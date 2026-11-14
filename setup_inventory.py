import os
import sys
import django
from decimal import Decimal
from datetime import timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def check_mysql_and_create_db():
    from dotenv import load_dotenv
    load_dotenv()

    db_engine = os.getenv('DB_ENGINE', 'mysql').lower()
    if db_engine != 'mysql':
        print(f"[*] Configured DB_ENGINE is '{db_engine}', skipping MySQL database creation.")
        return True

    db_name = os.getenv('DB_NAME', 'inventory_db')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = int(os.getenv('DB_PORT', '3306'))

    print(f"[*] Checking MySQL connection at {db_host}:{db_port} as user '{db_user}'...")
    try:
        import pymysql
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            port=db_port,
            connect_timeout=3
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"[OK] MySQL Database `{db_name}` is ready!")
        conn.close()
        return True
    except Exception as e:
        print(f"[!] Warning: Could not connect to MySQL server: {e}")
        print(f"[!] Please check your DB_PASSWORD in .env or MySQL service status.")
        return False

def seed_data():
    django.setup()
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from django.utils import timezone
    from inventory.models import Category, Supplier, Product, StockTransaction, UserProfile, Customer, SaleOrder, SaleOrderItem

    print("[*] Running migrations...")
    call_command('makemigrations', 'inventory', interactive=False)
    call_command('migrate', interactive=False)

    print("[*] Creating demo users...")
    # Admin User
    admin_user, _ = User.objects.get_or_create(username='admin', defaults={
        'email': 'admin@stockpro.local',
        'first_name': 'Admin',
        'last_name': 'System',
        'is_staff': True,
        'is_superuser': True,
    })
    admin_user.set_password('admin123')
    admin_user.save()
    if hasattr(admin_user, 'profile'):
        admin_user.profile.role = 'admin'
        admin_user.profile.department = 'Executive Management'
        admin_user.profile.save()

    # Manager User
    mgr_user, _ = User.objects.get_or_create(username='manager', defaults={
        'email': 'manager@stockpro.local',
        'first_name': 'Sarah',
        'last_name': 'Connor',
        'is_staff': True,
    })
    mgr_user.set_password('manager123')
    mgr_user.save()
    if hasattr(mgr_user, 'profile'):
        mgr_user.profile.role = 'manager'
        mgr_user.profile.department = 'Warehouse Operations'
        mgr_user.profile.save()

    # Staff User
    staff_user, _ = User.objects.get_or_create(username='staff', defaults={
        'email': 'staff@stockpro.local',
        'first_name': 'Alex',
        'last_name': 'Rivera',
    })
    staff_user.set_password('staff123')
    staff_user.save()
    if hasattr(staff_user, 'profile'):
        staff_user.profile.role = 'staff'
        staff_user.profile.department = 'Floor Logistics'
        staff_user.profile.save()

    print("[*] Creating categories & suppliers...")
    cat_perishable, _ = Category.objects.get_or_create(name='Perishable Goods & Dairy', defaults={
        'description': 'Fresh dairy, refrigerated goods, and fast-perishing foodstuffs',
        'is_perishable': True,
        'shelf_life_days': 14,
        'alert_priority': 10
    })
    cat_pharma, _ = Category.objects.get_or_create(name='Pharmaceuticals & Health', defaults={
        'description': 'Medical supplies, supplements, and sterile laboratory reagents',
        'is_perishable': True,
        'shelf_life_days': 60,
        'alert_priority': 9
    })
    cat_electronics, _ = Category.objects.get_or_create(name='Electronics', defaults={
        'description': 'Barcode scanners, thermal printers, and electronic accessories',
        'is_perishable': False,
        'alert_priority': 2
    })
    cat_packaging, _ = Category.objects.get_or_create(name='Packaging & Shipping', defaults={
        'description': 'Corrugated boxes, tape, labels, and packing materials',
        'is_perishable': False,
        'alert_priority': 1
    })
    cat_tools, _ = Category.objects.get_or_create(name='Industrial Tools', defaults={
        'description': 'Scales, storage racks, bins, and handheld equipment',
        'is_perishable': False,
        'alert_priority': 1
    })
    cat_office, _ = Category.objects.get_or_create(name='Office Supplies', defaults={
        'description': 'Stationery, paper, toner, and administrative materials',
        'is_perishable': False,
        'alert_priority': 1
    })

    sup_apex, _ = Supplier.objects.get_or_create(name='Apex Tech Supply Co.', defaults={
        'contact_person': 'David Zhang',
        'email': 'orders@apextech.com',
        'phone': '+1 (555) 234-8890',
        'address': '742 Evergreen Terrace, Sector 4, CA'
    })
    sup_pack, _ = Supplier.objects.get_or_create(name='Global Packaging Solutions', defaults={
        'contact_person': 'Elena Rostova',
        'email': 'sales@globalpack.com',
        'phone': '+1 (555) 871-3342',
        'address': '1200 Logistics Blvd, Suite 200, TX'
    })
    sup_tools, _ = Supplier.objects.get_or_create(name='Titan Industrial Equipment', defaults={
        'contact_person': 'Marcus Vance',
        'email': 'marcus@titantools.com',
        'phone': '+1 (555) 902-1144',
        'address': '88 Foundry St, Detroit, MI'
    })

    print("[*] Seeding sample products...")
    products_data = [
        {
            'sku': 'PRD-1001',
            'name': 'Wireless Handheld Barcode Scanner 2D',
            'category': cat_electronics,
            'supplier': sup_apex,
            'cost_price': Decimal('42.50'),
            'selling_price': Decimal('89.99'),
            'quantity': 35,
            'reorder_level': 10,
            'unit': 'pcs',
            'location': 'Warehouse A - Bin 12A',
            'description': 'High-performance 2.4G wireless barcode scanner with cradle, compatible with 1D/2D QR codes.'
        },
        {
            'sku': 'PRD-1002',
            'name': 'Industrial Thermal Shipping Label Printer',
            'category': cat_electronics,
            'supplier': sup_apex,
            'cost_price': Decimal('165.00'),
            'selling_price': Decimal('279.00'),
            'quantity': 4,
            'reorder_level': 10,
            'unit': 'pcs',
            'location': 'Warehouse A - Shelf 3B',
            'description': 'Heavy-duty 4x6 direct thermal printer, 203 DPI, USB and Ethernet connectivity.'
        },
        {
            'sku': 'PRD-1003',
            'name': 'Heavy Duty Pistol Grip Tape Dispenser',
            'category': cat_packaging,
            'supplier': sup_pack,
            'cost_price': Decimal('5.20'),
            'selling_price': Decimal('14.50'),
            'quantity': 65,
            'reorder_level': 20,
            'unit': 'pcs',
            'location': 'Packing Station 1 & 2',
            'description': 'Comfortable ergonomic hand dispenser for standard 2-inch packaging tape.'
        },
        {
            'sku': 'PRD-1004',
            'name': 'Stackable Storage Bins (Pack of 6)',
            'category': cat_tools,
            'supplier': sup_tools,
            'cost_price': Decimal('18.00'),
            'selling_price': Decimal('36.00'),
            'quantity': 0,
            'reorder_level': 12,
            'unit': 'set',
            'location': 'Warehouse B - Rack 4',
            'description': 'High-density polypropylene stackable open-front bins for parts storage.'
        },
        {
            'sku': 'PRD-1005',
            'name': '4x6 Direct Thermal Labels (500 Labels/Roll)',
            'category': cat_packaging,
            'supplier': sup_pack,
            'cost_price': Decimal('3.10'),
            'selling_price': Decimal('7.99'),
            'quantity': 8,
            'reorder_level': 25,
            'unit': 'box',
            'location': 'Warehouse A - Bin 8C',
            'description': 'Perforated waterproof thermal shipping labels for standard courier printers.'
        },
        {
            'sku': 'PRD-1006',
            'name': 'Digital Bench Scale 100kg Capacity',
            'category': cat_tools,
            'supplier': sup_tools,
            'cost_price': Decimal('38.00'),
            'selling_price': Decimal('79.50'),
            'quantity': 18,
            'reorder_level': 5,
            'unit': 'pcs',
            'location': 'Dispatch Dock Bay 1',
            'description': 'Stainless steel platform scale with separate wall-mountable LCD backlit indicator.'
        },
        {
            'sku': 'PRD-1007',
            'name': 'Corrugated Box 12x9x6 (Bundle of 25)',
            'category': cat_packaging,
            'supplier': sup_pack,
            'cost_price': Decimal('9.50'),
            'selling_price': Decimal('22.00'),
            'quantity': 140,
            'reorder_level': 30,
            'unit': 'pack',
            'location': 'Pallet Row 3',
            'description': 'ECT-32 single-wall kraft corrugated shipping boxes.'
        },
        {
            'sku': 'PRD-2001',
            'name': 'Pasteurized Organic Whole Milk 1L',
            'category': cat_perishable,
            'supplier': sup_pack,
            'cost_price': Decimal('1.80'),
            'selling_price': Decimal('3.50'),
            'quantity': 15,
            'reorder_level': 20,
            'unit': 'ltr',
            'batch_no': 'LOT-MILK-092',
            'expiry_date': timezone.now().date() + timedelta(days=4),
            'location': 'Cold Storage - Chiller 1',
            'description': 'Fresh whole milk, requires continuous refrigeration between 2-4°C.'
        },
        {
            'sku': 'PRD-2002',
            'name': 'Greek Natural Yogurt Cups (Pack of 4)',
            'category': cat_perishable,
            'supplier': sup_pack,
            'cost_price': Decimal('2.40'),
            'selling_price': Decimal('4.99'),
            'quantity': 12,
            'reorder_level': 15,
            'unit': 'pack',
            'batch_no': 'LOT-YOG-018',
            'expiry_date': timezone.now().date() - timedelta(days=2),
            'location': 'Cold Storage - Chiller 2',
            'description': 'High-protein Greek yogurt, expired lot flagged for quarantine.'
        },
        {
            'sku': 'PRD-2003',
            'name': 'Sterile Saline Antiseptic Solution 500ml',
            'category': cat_pharma,
            'supplier': sup_tools,
            'cost_price': Decimal('4.50'),
            'selling_price': Decimal('9.99'),
            'quantity': 5,
            'reorder_level': 10,
            'unit': 'pcs',
            'batch_no': 'LOT-MED-102',
            'expiry_date': timezone.now().date() + timedelta(days=14),
            'location': 'Pharma Vault - Shelf 1A',
            'description': 'Sterile first aid saline flush, expiring within 2 weeks and low in stock.'
        },
        {
            'sku': 'PRD-2004',
            'name': 'Effervescent Multivitamin C + Zinc (30 Tabs)',
            'category': cat_pharma,
            'supplier': sup_tools,
            'cost_price': Decimal('6.00'),
            'selling_price': Decimal('13.50'),
            'quantity': 40,
            'reorder_level': 12,
            'unit': 'box',
            'batch_no': 'LOT-VIT-440',
            'expiry_date': timezone.now().date() + timedelta(days=240),
            'location': 'Pharma Vault - Shelf 2B',
            'description': 'Immune boost vitamins, stable long shelf life.'
        },
    ]

    for p_info in products_data:
        p, created = Product.objects.get_or_create(sku=p_info['sku'], defaults=p_info)
        if created and p.quantity > 0:
            StockTransaction.objects.create(
                product=p,
                transaction_type='IN',
                quantity=p.quantity,
                quantity_before=0,
                quantity_after=p.quantity,
                reference_no='PO-INITIAL-STOCK',
                notes='Initial inventory intake batch',
                created_by=admin_user
            )

    print("[*] Generating 7-day movement trend transactions...")
    p1 = Product.objects.filter(sku='PRD-1001').first()
    p3 = Product.objects.filter(sku='PRD-1003').first()
    p5 = Product.objects.filter(sku='PRD-1005').first()

    now = timezone.now()
    if p1 and StockTransaction.objects.count() <= len(products_data):
        # Add realistic spread of transactions over past 6 days
        sample_moves = [
            (p1, 'OUT', 5, 40, 35, now - timedelta(days=1), 'DISPATCH-8812', staff_user),
            (p3, 'IN', 25, 40, 65, now - timedelta(days=2), 'PO-7729', mgr_user),
            (p5, 'OUT', 12, 20, 8, now - timedelta(days=3), 'DISPATCH-8801', staff_user),
            (p1, 'IN', 15, 25, 40, now - timedelta(days=4), 'PO-7681', mgr_user),
            (p3, 'OUT', 10, 50, 40, now - timedelta(days=5), 'DISPATCH-8760', staff_user),
        ]
        for prod, t_type, qty, q_before, q_after, t_time, ref, usr in sample_moves:
            tx = StockTransaction.objects.create(
                product=prod,
                transaction_type=t_type,
                quantity=qty,
                quantity_before=q_before,
                quantity_after=q_after,
                reference_no=ref,
                notes='Historical inventory flow demonstration',
                created_by=usr
            )
            # Update created_at timestamp
            StockTransaction.objects.filter(pk=tx.pk).update(created_at=t_time)

        print("[*] Creating demo customers and initial sale order...")
        cust1, _ = Customer.objects.get_or_create(
            phone='012888999',
            defaults={
                'name': 'Angkor Mega Supermarket',
                'email': 'procurement@angkormarket.com',
                'address': '#45 Monivong Blvd, Phnom Penh',
                'notes': 'Key retail partner - high-volume perishable buyer'
            }
        )
        cust2, _ = Customer.objects.get_or_create(
            phone='098765432',
            defaults={
                'name': 'Golden Bakery & Cafe',
                'email': 'order@goldenbakery.kh',
                'address': '#12 Sothearos Blvd, Phnom Penh',
                'notes': 'Regular weekly dairy and bakery supply customer'
            }
        )

        # Seed an initial completed sale order if none exist
        if SaleOrder.objects.count() == 0:
            so = SaleOrder.objects.create(
                invoice_no='INV-20261114-1001',
                customer=cust2,
                customer_name=cust2.name,
                customer_phone=cust2.phone,
                subtotal=Decimal('62.50'),
                discount_amount=Decimal('2.50'),
                tax_amount=Decimal('0.00'),
                grand_total=Decimal('60.00'),
                payment_method='QR_CODE',
                status='COMPLETED',
                notes='Direct store pickup - Paid via KHQR',
                created_by=staff_user
            )
            # Add line items
            SaleOrderItem.objects.create(
                order=so,
                product=p1,
                product_name=p1.name,
                product_sku=p1.sku,
                unit_cost_price=p1.cost_price,
                unit_selling_price=p1.selling_price,
                quantity=10,
                line_total=Decimal('35.00')
            )
            SaleOrderItem.objects.create(
                order=so,
                product=p3,
                product_name=p3.name,
                product_sku=p3.sku,
                unit_cost_price=p3.cost_price,
                unit_selling_price=p3.selling_price,
                quantity=5,
                line_total=Decimal('27.50')
            )

    print("[OK] Seed completed successfully!")

if __name__ == '__main__':
    mysql_ready = check_mysql_and_create_db()
    if not mysql_ready:
        print("\n--------------------------------------------------------------")
        print("ATTENTION: MySQL connection was not established.")
        print("1. Please check if your MySQL server is running.")
        print("2. Enter your MySQL password in the .env file (e.g. DB_PASSWORD=your_password).")
        print("3. Re-run: python setup_inventory.py")
        print("--------------------------------------------------------------\n")
        # Ask if user wants to run with SQLite for immediate preview
        use_fallback = os.getenv('FALLBACK_TO_SQLITE', 'False') == 'True'
        if not use_fallback:
            print("[*] To preview the app right away while you check MySQL password, you can set:")
            print("    DB_ENGINE=sqlite in .env")
            sys.exit(1)

    seed_data()
