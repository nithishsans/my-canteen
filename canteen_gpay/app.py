"""
app.py  –  SASTRA E-Canteen  (SQLite edition)

Authentication rules:
  • Email  : exactly <9-digit-register-no>@sastra.ac.in
  • Reg no : must exist in authorized_students table (226171001–226171120)
  • Login  : name + email + password must all match the stored user record
  • Mobile : 10-digit number required at registration
"""

from flask import (Flask, render_template, request,
                   jsonify, session, redirect, url_for)
import sqlite3, json, os, re, random, string, hashlib
from datetime import datetime
from contextlib import contextmanager

# ── App setup ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'sastra_ecanteen_secret_2024'

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ecanteen.db')

# ── DB helper ─────────────────────────────────────────────────────────────
@contextmanager
def get_db():
    """Yield a (conn, cursor) pair; commit on success, rollback on error."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name
    conn.execute("PRAGMA journal_mode=WAL") # safer concurrent access
    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ── Helpers ────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def generate_token() -> str:
    return ''.join(random.choices(string.digits, k=6))

def generate_bill() -> str:
    return 'BILL' + ''.join(random.choices(string.digits, k=8))

def valid_sastra_email(email: str) -> bool:
    """9-digit register number @sastra.ac.in"""
    return bool(re.match(r'^\d{9}@sastra\.ac\.in$', email))

def reg_no_from_email(email: str) -> str:
    return email.split('@')[0]

def is_authorized_reg_no(reg_no: str) -> bool:
    """Check the SQLite authorized_students table."""
    with get_db() as (conn, cur):
        cur.execute(
            'SELECT 1 FROM authorized_students WHERE register_no=? AND is_active=1',
            (reg_no,)
        )
        return cur.fetchone() is not None

# ── Ensure DB exists (auto-bootstrap if needed) ───────────────────────────
def ensure_db():
    if not os.path.exists(DB_PATH):
        import init_db
        init_db.init()

ensure_db()

# ══════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


# ── Student auth ──────────────────────────────────────────────────────────

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        data     = request.get_json()
        email    = data.get('email', '').strip().lower()
        name     = data.get('name', '').strip()
        password = data.get('password', '')

        # 1) Email format
        if not valid_sastra_email(email):
            return jsonify({'success': False,
                'message': 'Email must be: 226171001@sastra.ac.in (9-digit register number)'})

        reg_no = reg_no_from_email(email)

        # 2) Register number in authorized DB
        if not is_authorized_reg_no(reg_no):
            return jsonify({'success': False,
                'message': f'Register number {reg_no} is not in the authorized student database.'})

        # 3) Account exists
        with get_db() as (conn, cur):
            cur.execute('SELECT name, password FROM users WHERE email=?', (email,))
            user = cur.fetchone()

        if user is None:
            return jsonify({'success': False,
                'message': 'No account found for this email. Please register first.'})

        # 4) Password check
        if user['password'] != hash_password(password):
            return jsonify({'success': False, 'message': 'Incorrect password.'})

        # 5) Name check
        if user['name'].strip().lower() != name.lower():
            return jsonify({'success': False,
                'message': 'Name does not match the registered account.'})

        session['student']      = email
        session['student_name'] = user['name']
        return jsonify({'success': True})

    return render_template('student_login.html')


@app.route('/student/register', methods=['POST'])
def student_register():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    name     = data.get('name', '').strip()
    mobile   = data.get('mobile', '').strip()
    password = data.get('password', '')

    # Validate email format
    if not valid_sastra_email(email):
        return jsonify({'success': False,
            'message': 'Email must be 9-digit register number @sastra.ac.in'})

    reg_no = reg_no_from_email(email)

    # Validate register number in authorized DB
    if not is_authorized_reg_no(reg_no):
        return jsonify({'success': False,
            'message': f'Register number {reg_no} is not in the authorized student database (226171001–226171120).'})

    # Validate mobile
    if not re.match(r'^\d{10}$', mobile):
        return jsonify({'success': False,
            'message': 'Mobile number must be exactly 10 digits.'})

    if not name:
        return jsonify({'success': False, 'message': 'Full name is required.'})

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'})

    with get_db() as (conn, cur):
        cur.execute('SELECT 1 FROM users WHERE email=?', (email,))
        if cur.fetchone():
            return jsonify({'success': False,
                'message': 'Email already registered. Please login.'})

        cur.execute(
            '''INSERT INTO users (email, name, register_no, mobile, password)
               VALUES (?,?,?,?,?)''',
            (email, name, reg_no, mobile, hash_password(password))
        )

    return jsonify({'success': True, 'message': 'Registered successfully!'})


@app.route('/student/dashboard')
def student_dashboard():
    if 'student' not in session:
        return redirect(url_for('student_login'))
    return render_template('student_dashboard.html', name=session['student_name'])


@app.route('/student/cart')
def student_cart():
    if 'student' not in session:
        return redirect(url_for('student_login'))
    return render_template('student_cart.html', name=session['student_name'])


@app.route('/student/logout')
def student_logout():
    session.pop('student', None)
    session.pop('student_name', None)
    return redirect(url_for('index'))


# ── Admin auth ────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '')

        with get_db() as (conn, cur):
            cur.execute('SELECT name, password FROM admins WHERE email=?', (email,))
            admin = cur.fetchone()

        if admin and admin['password'] == hash_password(data.get('password', '')):
            session['admin']      = email
            session['admin_name'] = admin['name']
            return jsonify({'success': True})

        return jsonify({'success': False, 'message': 'Invalid admin credentials.'})

    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', name=session['admin_name'])


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    session.pop('admin_name', None)
    return redirect(url_for('index'))


# ══════════════════════════════════════════════════════════════════════════
#  STUDENT API
# ══════════════════════════════════════════════════════════════════════════

@app.route('/api/menu')
def api_menu():
    with get_db() as (conn, cur):
        cur.execute(
            'SELECT * FROM foods WHERE in_today_menu=1 AND available=1'
        )
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route('/api/foods')
def api_foods():
    with get_db() as (conn, cur):
        cur.execute('SELECT * FROM foods')
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route('/api/place_order', methods=['POST'])
def place_order():
    if 'student' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    data      = request.get_json()
    items     = data.get('items', [])
    time_slot = data.get('time_slot', '')

    with get_db() as (conn, cur):
        # Calculate total from DB prices (don't trust client-side prices)
        total = 0.0
        for item in items:
            cur.execute('SELECT price FROM foods WHERE id=?', (item['food_id'],))
            row = cur.fetchone()
            if row:
                total += row['price'] * item['qty']

        bill_no = generate_bill()
        token   = generate_token()

        cur.execute(
            '''INSERT INTO orders
               (bill_no, token, student_email, student_name,
                items_json, total, time_slot, status)
               VALUES (?,?,?,?,?,?,?,?)''',
            (bill_no, token,
             session['student'], session['student_name'],
             json.dumps(items), total, time_slot, 'Pending Payment')
        )

    return jsonify({'success': True, 'bill_no': bill_no, 'token': token, 'total': total})


@app.route('/api/verify_payment', methods=['POST'])
def verify_payment():
    """
    Student submits GPay UTR / transaction ID after paying.
    Order is marked 'Payment Submitted' — admin must confirm.
    """
    if 'student' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    data    = request.get_json()
    bill_no = data.get('bill_no', '')
    txn_id  = data.get('transaction_id', '').strip()

    if not txn_id:
        return jsonify({'success': False, 'message': 'Enter transaction ID'})

    with get_db() as (conn, cur):
        cur.execute('SELECT * FROM orders WHERE bill_no=?', (bill_no,))
        order = cur.fetchone()
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})

        if order['payment_verified']:
            return jsonify({'success': False, 'message': 'Payment already confirmed'})

        # Save txn ID; mark as submitted but NOT yet admin-confirmed
        cur.execute(
            '''UPDATE orders
               SET transaction_id=?, status='Payment Submitted'
               WHERE bill_no=?''',
            (txn_id, bill_no)
        )

    return jsonify({'success': True, 'bill_no': bill_no,
                    'message': 'Transaction ID submitted. Awaiting admin confirmation.'})



@app.route('/api/upi_info')
def api_upi_info():
    """Public: returns canteen UPI ID for student payment screen."""
    with get_db() as (conn, cur):
        cur.execute("SELECT key, value FROM settings WHERE key IN ('upi_id','upi_name')")
        data = {row['key']: row['value'] for row in cur.fetchall()}
    return jsonify({'upi_id': data.get('upi_id','canteen@sastra'), 'upi_name': data.get('upi_name','SASTRA Canteen')})


@app.route('/api/admin/get_settings')
def admin_get_settings():
    if 'admin' not in session:
        return jsonify({})
    with get_db() as (conn, cur):
        cur.execute("SELECT key, value FROM settings")
        data = {row['key']: row['value'] for row in cur.fetchall()}
    return jsonify(data)


@app.route('/api/admin/save_settings', methods=['POST'])
def admin_save_settings():
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Not admin'})
    data = request.get_json()
    upi_id   = data.get('upi_id',   '').strip()
    upi_name = data.get('upi_name', '').strip()
    if not upi_id:
        return jsonify({'success': False, 'message': 'UPI ID cannot be empty'})
    if '@' not in upi_id:
        return jsonify({'success': False, 'message': 'Invalid UPI ID format (e.g. name@bankname)'})
    with get_db() as (conn, cur):
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_id', ?)",   (upi_id,))
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_name', ?)", (upi_name or 'SASTRA Canteen',))
    return jsonify({'success': True, 'upi_id': upi_id, 'upi_name': upi_name})


@app.route('/api/admin/pending_payments')
def admin_pending_payments():
    """All orders with a txn ID submitted but not yet admin-confirmed."""
    if 'admin' not in session:
        return jsonify([])
    with get_db() as (conn, cur):
        cur.execute(
            """SELECT * FROM orders
               WHERE status='Payment Submitted' AND payment_verified=0
               ORDER BY timestamp DESC"""
        )
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d['items'] = json.loads(d.get('items_json') or '[]')
            rows.append(d)
    return jsonify(rows)


@app.route('/api/admin/confirm_payment', methods=['POST'])
def admin_confirm_payment():
    """Admin confirms a submitted payment → order becomes Confirmed."""
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Not admin'})

    data    = request.get_json()
    bill_no = data.get('bill_no', '')
    action  = data.get('action', 'confirm')   # 'confirm' or 'reject'

    with get_db() as (conn, cur):
        cur.execute('SELECT * FROM orders WHERE bill_no=?', (bill_no,))
        order = cur.fetchone()
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})

        if action == 'confirm':
            cur.execute(
                '''UPDATE orders
                   SET payment_verified=1, status='Confirmed'
                   WHERE bill_no=?''',
                (bill_no,)
            )
            # Insert into transactions table
            cur.execute(
                '''INSERT OR IGNORE INTO transactions
                   (transaction_id, bill_no, amount, student_email)
                   VALUES (?,?,?,?)''',
                (order['transaction_id'], bill_no,
                 order['total'], order['student_email'])
            )
            return jsonify({'success': True, 'action': 'confirmed',
                            'token': order['token']})

        elif action == 'reject':
            cur.execute(
                '''UPDATE orders
                   SET transaction_id=NULL, status='Pending Payment'
                   WHERE bill_no=?''',
                (bill_no,)
            )
            return jsonify({'success': True, 'action': 'rejected'})

    return jsonify({'success': False, 'message': 'Unknown action'})


@app.route('/api/order_status')
def order_status():
    """Student polls this to check if admin has confirmed their payment."""
    if 'student' not in session:
        return jsonify({'payment_verified': False})
    bill_no = request.args.get('bill_no', '')
    with get_db() as (conn, cur):
        cur.execute(
            'SELECT payment_verified, token, status FROM orders WHERE bill_no=? AND student_email=?',
            (bill_no, session['student'])
        )
        row = cur.fetchone()
    if not row:
        return jsonify({'payment_verified': False})
    return jsonify({'payment_verified': bool(row['payment_verified']),
                    'token': row['token'], 'status': row['status']})


@app.route('/api/my_orders')
def my_orders():
    if 'student' not in session:
        return jsonify([])
    with get_db() as (conn, cur):
        cur.execute(
            'SELECT * FROM orders WHERE student_email=? ORDER BY timestamp DESC',
            (session['student'],)
        )
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d['items'] = json.loads(d.get('items_json') or '[]')
            rows.append(d)
    return jsonify(rows)


# ══════════════════════════════════════════════════════════════════════════
#  ADMIN API
# ══════════════════════════════════════════════════════════════════════════

@app.route('/api/admin/stats')
def admin_stats():
    if 'admin' not in session:
        return jsonify({})
    with get_db() as (conn, cur):
        cur.execute('SELECT COUNT(*) AS n FROM orders')
        total_orders = cur.fetchone()['n']

        cur.execute('SELECT COUNT(*), SUM(total) FROM orders WHERE payment_verified=1')
        row = cur.fetchone()
        confirmed_orders = row[0] or 0
        total_revenue    = row[1] or 0.0

        now = datetime.now().strftime('%Y-%m')
        cur.execute(
            "SELECT SUM(total) FROM orders WHERE payment_verified=1 AND strftime('%Y-%m',timestamp)=?",
            (now,)
        )
        monthly_revenue = cur.fetchone()[0] or 0.0

        # Top foods from items_json
        cur.execute('SELECT items_json FROM orders WHERE payment_verified=1')
        food_count = {}
        for (items_json,) in cur.fetchall():
            for item in json.loads(items_json or '[]'):
                fid = item['food_id']
                food_count[fid] = food_count.get(fid, 0) + item.get('qty', 1)

        top5 = sorted(food_count.items(), key=lambda x: x[1], reverse=True)[:5]

        top_foods = []
        for fid, cnt in top5:
            cur.execute('SELECT name FROM foods WHERE id=?', (fid,))
            row = cur.fetchone()
            top_foods.append({'name': row['name'] if row else fid, 'count': cnt})

    return jsonify({
        'total_orders':     total_orders,
        'confirmed_orders': confirmed_orders,
        'total_revenue':    total_revenue,
        'monthly_revenue':  monthly_revenue,
        'top_foods':        top_foods,
    })


@app.route('/api/admin/orders')
def admin_orders():
    if 'admin' not in session:
        return jsonify([])
    with get_db() as (conn, cur):
        cur.execute('SELECT * FROM orders ORDER BY timestamp DESC')
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d['items'] = json.loads(d.get('items_json') or '[]')
            rows.append(d)
    return jsonify(rows)


@app.route('/api/admin/transactions')
def admin_transactions():
    if 'admin' not in session:
        return jsonify([])
    with get_db() as (conn, cur):
        cur.execute('SELECT * FROM transactions ORDER BY timestamp DESC')
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route('/api/admin/students')
def admin_students():
    """List all registered students."""
    if 'admin' not in session:
        return jsonify([])
    with get_db() as (conn, cur):
        cur.execute(
            'SELECT email, name, register_no, mobile, created_at FROM users ORDER BY register_no'
        )
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route('/api/admin/authorized_students')
def admin_authorized_students():
    """List all authorized register numbers and their registration status."""
    if 'admin' not in session:
        return jsonify([])
    with get_db() as (conn, cur):
        cur.execute('''
            SELECT a.register_no, a.is_active,
                   u.name, u.email, u.mobile
            FROM authorized_students a
            LEFT JOIN users u ON u.register_no = a.register_no
            ORDER BY a.register_no
        ''')
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route('/api/admin/update_food', methods=['POST'])
def update_food():
    if 'admin' not in session:
        return jsonify({'success': False})
    data = request.get_json()
    fid  = data.get('id')
    allowed = ['name', 'price', 'description', 'image', 'available', 'in_today_menu']
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return jsonify({'success': False, 'message': 'Nothing to update'})

    with get_db() as (conn, cur):
        cur.execute('SELECT 1 FROM foods WHERE id=?', (fid,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Food not found'})
        set_clause = ', '.join(f'{k}=?' for k in updates)
        cur.execute(f'UPDATE foods SET {set_clause} WHERE id=?',
                    list(updates.values()) + [fid])

    return jsonify({'success': True})


@app.route('/api/admin/add_food', methods=['POST'])
def add_food():
    if 'admin' not in session:
        return jsonify({'success': False})
    data = request.get_json()
    with get_db() as (conn, cur):
        # Generate unique ID
        while True:
            fid = 'F' + ''.join(random.choices(string.digits, k=3))
            cur.execute('SELECT 1 FROM foods WHERE id=?', (fid,))
            if not cur.fetchone():
                break
        cur.execute(
            '''INSERT INTO foods (id,name,price,description,category,image,available,in_today_menu,rating)
               VALUES (?,?,?,?,?,?,1,?,4.0)''',
            (fid,
             data.get('name'),
             float(data.get('price', 0)),
             data.get('description', ''),
             data.get('category', 'Other'),
             data.get('image', 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400'),
             int(data.get('in_today_menu', 0)))
        )
    return jsonify({'success': True, 'id': fid})


# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
