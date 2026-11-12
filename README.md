# StockPro - Modern Inventory Management System

A full-stack, enterprise-grade **Inventory Management System** built with **Django**, **MySQL**, **Tailwind CSS**, and **Chart.js**. Featuring authentication, role-based authorization (Admin, Manager, Staff), real-time low-stock tracking, automated movements audit, and interactive analytics.

---

## 🚀 Key Features

- **🌐 Multi-Language Support (Khmer & English)**:
  - Instant toggle between **English (🇬🇧 EN)** and **ភាសាខ្មែរ (🇰🇭 KM)** via top navigation pill.
  - Native Google Font **Kantumruy Pro** integration for Khmer typography.
  - Full translations for dashboard metrics, menus, tables, badges, and stock control flows.
- **🔐 Authentication & Role-Based Authorization (RBAC)**:
  - **Administrator (`admin`)**: Complete system authority, user provisioning, access activation, and catalog deletions.
  - **Inventory Manager (`manager`)**: Product catalog management, category & supplier oversight, and stock audit reconciliations.
  - **Staff Member (`staff`)**: Day-to-day warehouse floor operations, stock-in receiving, stock-out dispatches, and alert monitoring.
- **📊 Real-time Dashboard**:
  - **KPI Performance Cards**:
    1. **Total Products / Volume**: Active catalog SKUs and physical units on hand.
    2. **Low Stock Alert**: Real-time warning for items at or below reorder threshold.
    3. **Out of Stock**: Urgent zero-stock notice requiring immediate purchase orders.
    4. **Expire Product Alert**: Immediate visibility of Expired and Expiring Soon items with countdown badges.
    5. **Total Inventory Valuation**: Live asset retail value with cost basis.
    6. **Products Sold & Realized Profit (New Card)**: Tracks total units sold/dispatched, total sales revenue, net realized money profit, and gross profit margin percentage.
  - **⚡ Category-Based Stock Alerts (Fast-to-Expire Prioritized First)**:
    - Automatically surfaces categories flagged as easy or fast to expire (e.g. Perishables, Dairy, Pharmaceuticals) at the top of alerts.
    - Category breakdown showing expired count, expiring soon count, out of stock, and low stock units.
  - **Chart.js Visualizations**: 7-day inbound vs. outbound movement flow and category breakdown doughnut.
  - Prioritized Reorder & Expiry Warnings list highlighting perishable items first.
- **📦 Comprehensive Product & Expiry Management**:
  - Unique SKU tracking, categories, suppliers, cost vs. selling price, and warehouse bin locations.
  - **Perishable & Batch Tracking**: Lot / Batch numbers, expiration dates, days-remaining countdowns, and automated expired stock warnings.
  - Dynamic stock & shelf-life status badges (*In Stock*, *Low Stock*, *Out of Stock*, *Expired*, *Expiring Soon*).
  - Live gross margin % calculator on product creation/editing.
- **🔄 Stock Movement & Audit Logging**:
  - **Stock In**: Record purchases and restocking batches with document reference numbers.
  - **Stock Out**: Record customer dispatches with automatic negative-stock prevention.
  - **Audit Adjustment**: Reconcile discrepancies after physical inventory counts.
  - **CSV Exports**: One-click download of both inventory product sheets and movement audit trails.
- **🗄️ MySQL Database Engine**:
  - Native MySQL backend using `pymysql` and `.env` configuration.
  - Automatic `inventory_db` database creation upon connection.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.14, Django 6.1, PyMySQL, Python-Dotenv |
| **Database** | MySQL (with automated fallback to SQLite for zero-config testing) |
| **Frontend** | HTML5, Tailwind CSS 3.4 (CDN), Font Awesome 6.5, Google Fonts |
| **Analytics** | Chart.js 4.x (Dynamic bar and doughnut charts) |

---

## 📋 Preconfigured Demo Accounts

| Role | Username | Password | Permissions |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Full access, user role management, deletions |
| **Manager** | `manager` | `manager123` | Add/Edit products, categories, suppliers, audit reconciliations |
| **Staff** | `staff` | `staff123` | View inventory, record stock in/out, view low-stock alerts |

---

## ⚙️ Quick Start Guide

### 1. Configure MySQL in `.env`
Edit the `.env` file in the project root with your MySQL database credentials:

```env
DB_ENGINE=mysql
DB_NAME=inventory_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 2. Initialize Database & Seed Demo Data
Run the all-in-one setup script:
```powershell
python setup_inventory.py
```
This script will:
1. Connect to MySQL and run `CREATE DATABASE IF NOT EXISTS inventory_db`.
2. Apply all Django migrations.
3. Seed default demo accounts (`admin`, `manager`, `staff`).
4. Populate categories, suppliers, realistic warehouse products, and 7-day movement transactions.

### 3. Start the Development Server
```powershell
python manage.py runserver 127.0.0.1:8000
```
Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📁 Project Structure

```
inventory_system/
├── config/                  # Django project configuration
│   ├── __init__.py          # PyMySQL initialization
│   ├── settings.py          # Database, auth, and template configuration
│   ├── urls.py              # Main URL routing (login, logout, admin)
│   └── wsgi.py
├── inventory/               # Inventory core application
│   ├── admin.py             # Django admin model registrations
│   ├── context_processors.py# Global alert counters & user role helpers
│   ├── forms.py             # Tailwind-styled forms for items, movements & users
│   ├── models.py            # UserProfile, Category, Supplier, Product, StockTransaction
│   ├── urls.py              # Application URL routes
│   └── views.py             # RBAC views, dashboard analytics, and CSV exports
├── templates/               # Responsive HTML templates
│   ├── base.html            # Sidebar navigation, topbar, alert toasts, dark mode
│   ├── registration/
│   │   └── login.html       # Sign-in page with 1-click demo credential autofill
│   └── inventory/
│       ├── dashboard.html   # KPI stat cards, Chart.js charts, reorder alerts
│       ├── product_list.html# Search, filter, pagination, status pills
│       ├── product_detail.html # SKU details, margins, quick audit adjust
│       ├── product_form.html# Add/Edit product with live profit calculator
│       ├── stock_movement.html # Stock In / Out transactional form
│       ├── transaction_list.html # Audit trail with filter by type & CSV export
│       ├── category_list.html # Categories management
│       ├── supplier_list.html # Suppliers directory & contact cards
│       ├── supplier_form.html # Supplier edit
│       ├── user_list.html   # Admin user role assignment & activation
│       └── confirm_delete.html # Deletion warning modal
├── static/css/style.css     # Custom animations and variables
├── setup_inventory.py       # Automated database migration and seed utility
├── .env                     # Environment variables configuration
└── manage.py
```
