"""
init_db.py  –  Run once to create and seed the SQLite database.
Creates:
  - authorized_students   : preloaded register numbers 226171001–226171120
  - users                 : registered student accounts
  - admins                : admin accounts
  - foods                 : menu items
  - orders                : placed orders
  - transactions          : payment records
"""

import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ecanteen.db')

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── authorized_students ──────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS authorized_students (
            register_no TEXT PRIMARY KEY,
            is_active   INTEGER DEFAULT 1
        )
    ''')

    # ── users (registered accounts) ─────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email        TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            register_no  TEXT NOT NULL,
            mobile       TEXT NOT NULL,
            password     TEXT NOT NULL,
            created_at   TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (register_no) REFERENCES authorized_students(register_no)
        )
    ''')

    # ── admins ───────────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            email    TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # ── foods ────────────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            price         REAL NOT NULL,
            description   TEXT,
            category      TEXT,
            image         TEXT,
            available     INTEGER DEFAULT 1,
            in_today_menu INTEGER DEFAULT 0,
            rating        REAL DEFAULT 4.0
        )
    ''')

    # ── orders ───────────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            bill_no          TEXT PRIMARY KEY,
            token            TEXT,
            student_email    TEXT,
            student_name     TEXT,
            items_json       TEXT,
            total            REAL,
            time_slot        TEXT,
            status           TEXT DEFAULT 'Pending Payment',
            timestamp        TEXT DEFAULT (datetime('now','localtime')),
            transaction_id   TEXT,
            payment_verified INTEGER DEFAULT 0
        )
    ''')

    # ── transactions ─────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            bill_no        TEXT,
            amount         REAL,
            student_email  TEXT,
            timestamp      TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # ── settings (key-value config) ──────────────────────────────────────
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('upi_id', 'canteen@sastra')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('upi_name', 'SASTRA Canteen')")

    conn.commit()

    # ── Seed authorized_students (226171001 – 226171120) ─────────────────
    print("Seeding authorized students 226171001 → 226171120 ...")
    rows = [(str(n),) for n in range(226171001, 226171121)]
    c.executemany(
        'INSERT OR IGNORE INTO authorized_students (register_no) VALUES (?)',
        rows
    )
    print(f"  Inserted {len(rows)} register numbers.")

    # ── Seed default admin ───────────────────────────────────────────────
    c.execute(
        'INSERT OR IGNORE INTO admins (email, name, password) VALUES (?,?,?)',
        ('admin@sastra.ac.in', 'Admin', hash_password('admin123'))
    )
    print("  Default admin: admin@sastra.ac.in / admin123")

    # ── Seed food items ──────────────────────────────────────────────────
    foods = [
        ('F001','Veg Thali',60,'Rice, Dal, 2 Sabzi, Roti, Papad, Pickle','Meals',
         'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400',1,1,4.5),
        ('F002','Chicken Biryani',90,'Aromatic basmati rice with tender chicken pieces','Biryani',
         'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400',1,1,4.8),
        ('F003','Masala Dosa',40,'Crispy dosa with spiced potato filling, chutney & sambar','South Indian',
         'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=400',1,1,4.6),
        ('F004','Paneer Butter Masala',75,'Creamy tomato gravy with soft paneer cubes','Curries',
         'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=400',1,1,4.4),
        ('F005','Veg Fried Rice',55,'Wok-tossed rice with fresh vegetables and soy sauce','Rice',
         'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=400',1,1,4.2),
        ('F006','Egg Fried Rice',65,'Fluffy rice wok-fried with eggs and vegetables','Rice',
         'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=400',1,1,4.3),
        ('F007','Chapati + Dal',35,'3 chapatis with yellow dal tadka','Meals',
         'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400',1,1,4.1),
        ('F008','Cold Coffee',30,'Chilled blended coffee with milk and ice cream','Beverages',
         'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400',1,1,4.7),
        ('F009','Samosa (2 pcs)',20,'Crispy golden samosas with mint chutney','Snacks',
         'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400',1,0,4.5),
        ('F010','Veg Noodles',50,'Hakka noodles stir-fried with fresh vegetables','Noodles',
         'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400',0,0,4.0),
    ]
    c.executemany(
        '''INSERT OR IGNORE INTO foods
           (id,name,price,description,category,image,available,in_today_menu,rating)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        foods
    )
    print(f"  Seeded {len(foods)} food items.")

    conn.commit()
    conn.close()
    print(f"\n✅  Database created at: {DB_PATH}")
    print("   Tables: authorized_students, users, admins, foods, orders, transactions")

if __name__ == '__main__':
    init()
