# SASTRA E-Canteen 🍽

A full-stack web application for SASTRA University students to pre-order canteen food online.

## Features

### Student Portal
- Login/Register with SASTRA college email (@sastra.ac.in)
- Browse today's menu with categories & search
- Add to cart and select pickup time slot
- Pay via Google Pay (UPI QR)
- Enter transaction ID to get Token Number
- View order history with bill details

### Admin Dashboard
- Login with admin credentials
- Dashboard: Total orders, revenue, monthly revenue, top selling items
- Order History with search & filter
- Inventory Management with ON/OFF toggles
- Transaction History
- Add Food (name, price, description, image, category)
- View & Edit all food items (toggle availability, today's menu, update details)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install flask
```
Or:
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### 3. Open in Browser
```
http://localhost:5000
```

## Default Admin Credentials
- **Email:** admin@sastra.ac.in
- **Password:** admin123

## Student Registration
- Use any @sastra.ac.in email address
- Passwords are hashed using SHA-256

## Project Structure
```
sastra_ecanteen/
├── app.py                  # Flask backend
├── requirements.txt
├── README.md
├── data/                   # JSON data files (auto-created)
│   ├── users.json
│   ├── admins.json
│   ├── foods.json
│   ├── orders.json
│   └── transactions.json
├── templates/
│   ├── index.html          # Landing page with menu
│   ├── student_login.html  # Student login/register
│   ├── student_dashboard.html  # Ordering interface
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/
    └── css/
        └── style.css
```

## Tech Stack
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Backend:** Python + Flask
- **Database:** JSON files (no external DB required)
- **Payment:** GPay/UPI QR Code integration (manual verification)
