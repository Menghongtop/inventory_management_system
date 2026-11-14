from datetime import timedelta
from decimal import Decimal
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from .models import Category, Product, Supplier, StockTransaction, Customer, SaleOrder, SaleOrderItem

class InventoryUpgradeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='testadmin', password='password123', email='admin@test.com')
        self.client.login(username='testadmin', password='password123')

        # Fast to expire perishable category
        self.cat_perishable = Category.objects.create(
            name='Dairy & Bakery',
            is_perishable=True,
            shelf_life_days=7,
            alert_priority=10
        )
        # Non-perishable category
        self.cat_hardware = Category.objects.create(
            name='Hardware & Tools',
            is_perishable=False,
            alert_priority=1
        )

        today = timezone.now().date()

        # Product 1: Perishable, Expired
        self.p_expired = Product.objects.create(
            sku='PER-001',
            name='Fresh Milk',
            category=self.cat_perishable,
            quantity=10,
            reorder_level=5,
            cost_price=Decimal('1.50'),
            selling_price=Decimal('3.00'),
            expiry_date=today - timedelta(days=2),
            batch_no='LOT-MILK-1'
        )

        # Product 2: Perishable, Expiring Soon
        self.p_expiring_soon = Product.objects.create(
            sku='PER-002',
            name='Yogurt Pack',
            category=self.cat_perishable,
            quantity=15,
            reorder_level=20, # Also low stock
            cost_price=Decimal('2.00'),
            selling_price=Decimal('4.00'),
            expiry_date=today + timedelta(days=5),
            batch_no='LOT-YOG-2'
        )

        # Product 3: Non-perishable, Out of Stock
        self.p_out_of_stock = Product.objects.create(
            sku='HDW-001',
            name='Steel Hammer',
            category=self.cat_hardware,
            quantity=0,
            reorder_level=5,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('25.00')
        )

        # Product 4: Non-perishable, In Stock & Healthy
        self.p_healthy = Product.objects.create(
            sku='HDW-002',
            name='Drill Bit Set',
            category=self.cat_hardware,
            quantity=50,
            reorder_level=10,
            cost_price=Decimal('5.00'),
            selling_price=Decimal('12.00')
        )

    def test_category_ordering_and_perishable_priority(self):
        """Categories must prioritize perishable and high alert priority first."""
        categories = list(Category.objects.all())
        self.assertEqual(categories[0].name, 'Dairy & Bakery')
        self.assertTrue(categories[0].is_perishable)
        self.assertEqual(categories[1].name, 'Hardware & Tools')

    def test_product_expiry_properties(self):
        """Test is_expired, is_expiring_soon, days_until_expiry and labels."""
        self.assertTrue(self.p_expired.is_expired)
        self.assertFalse(self.p_expired.is_expiring_soon)
        self.assertEqual(self.p_expired.expiry_status, 'expired')
        self.assertIn('Expired', self.p_expired.expiry_status_label)

        self.assertFalse(self.p_expiring_soon.is_expired)
        self.assertTrue(self.p_expiring_soon.is_expiring_soon)
        self.assertEqual(self.p_expiring_soon.expiry_status, 'expiring_soon')
        self.assertIn('Expires in', self.p_expiring_soon.expiry_status_label)

        self.assertFalse(self.p_healthy.is_expired)
        self.assertFalse(self.p_healthy.is_expiring_soon)
        self.assertEqual(self.p_healthy.expiry_status, 'none')

    def test_dashboard_kpis_and_category_alert_ordering(self):
        """Dashboard must calculate the 4 critical stock numbers and rank perishable categories first."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

        # 4 Important Stock Numbers
        self.assertEqual(response.context['total_products'], 4)
        self.assertEqual(response.context['low_stock_count'], 1) # p_expiring_soon
        self.assertEqual(response.context['out_of_stock_count'], 1) # p_out_of_stock
        self.assertEqual(response.context['expired_count'], 1) # p_expired
        self.assertEqual(response.context['expiring_soon_count'], 1) # p_expiring_soon
        self.assertEqual(response.context['total_expiry_alert_count'], 2)

        # Category alerts: perishable category MUST be first
        category_alerts = response.context['category_alerts']
        self.assertTrue(category_alerts[0]['is_perishable'])
        self.assertEqual(category_alerts[0]['category'].name, 'Dairy & Bakery')

    def test_product_list_filters(self):
        """Verify filter by expired, expiring_soon, and perishable."""
        # Expired filter
        res = self.client.get(reverse('product_list') + '?status=expired')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['page_obj']), 1)
        self.assertEqual(res.context['page_obj'][0].sku, 'PER-001')

        # Expiring soon filter
        res = self.client.get(reverse('product_list') + '?status=expiring_soon')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['page_obj']), 1)
        self.assertEqual(res.context['page_obj'][0].sku, 'PER-002')

        # Perishable category filter
        res = self.client.get(reverse('product_list') + '?status=perishable')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['page_obj']), 2)

    def test_csv_export_includes_expiry_and_lot(self):
        """CSV export must include Lot number, Expiry date, and Perishable indicator."""
        response = self.client.get(reverse('export_products_csv'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Batch / Lot #', content)
        self.assertIn('Expiry Date', content)
        self.assertIn('Perishable / Fast Expire', content)
        self.assertIn('LOT-MILK-1', content)
        self.assertIn('Yes (Fast to Expire)', content)

    def test_products_sold_and_profit_card(self):
        """Test sales tracking: units sold and realized money profit from selling products."""
        # Sale 1: 5 units of p_healthy (selling=12.00, cost=5.00 -> revenue=60.00, profit=35.00)
        t1 = StockTransaction.objects.create(
            product=self.p_healthy,
            transaction_type='OUT',
            quantity=5,
            quantity_before=50,
            quantity_after=45,
            created_by=self.admin
        )
        # Sale 2: 2 units of p_expired (selling=3.00, cost=1.50 -> revenue=6.00, profit=3.00)
        t2 = StockTransaction.objects.create(
            product=self.p_expired,
            transaction_type='OUT',
            quantity=2,
            quantity_before=10,
            quantity_after=8,
            created_by=self.admin
        )

        self.assertEqual(t1.total_profit, Decimal('35.00'))
        self.assertEqual(t2.total_profit, Decimal('3.00'))

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_products_sold'], 7)
        self.assertEqual(response.context['total_sales_revenue'], Decimal('66.00'))
        self.assertEqual(response.context['total_sales_profit'], Decimal('38.00'))

    def test_product_detail_view_expired_product(self):
        """Verify product detail renders without TemplateSyntaxError on expired products."""
        response = self.client.get(reverse('product_detail', kwargs={'pk': self.p_expired.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product Expired!')
        self.assertContains(response, '2 days ago')

    def test_customer_crud_and_directory(self):
        """Verify customer creation, directory view, and customer profile."""
        customer = Customer.objects.create(
            name='Acme Corp',
            phone='012999888',
            email='acme@example.com',
            address='123 Commercial Blvd'
        )
        res_list = self.client.get(reverse('customer_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, 'Acme Corp')

        res_detail = self.client.get(reverse('customer_detail', kwargs={'pk': customer.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Acme Corp')
        self.assertContains(res_detail, '012999888')

    def test_sales_order_checkout_and_stock_deduction(self):
        """Verify POS multi-item checkout, atomic stock deduction, and printable invoice detail."""
        customer = Customer.objects.create(
            name='John Doe',
            phone='098765432'
        )

        initial_qty = self.p_healthy.quantity # 50
        cart = [
            {
                'product_id': self.p_healthy.pk,
                'quantity': 5,
                'unit_price': 12.00
            }
        ]

        post_data = {
            'customer': customer.pk,
            'customer_name': '',
            'customer_phone': '',
            'payment_method': 'CASH',
            'discount_amount': '2.00',
            'tax_amount': '0.00',
            'notes': 'Test POS order',
            'cart_data': json.dumps(cart)
        }

        response = self.client.post(reverse('sales_order_create'), data=post_data)
        self.assertEqual(response.status_code, 302) # Redirect to invoice detail

        # Verify order created
        order = SaleOrder.objects.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.customer, customer)
        self.assertEqual(order.customer_name, 'John Doe')
        self.assertEqual(order.subtotal, Decimal('60.00')) # 5 * 12.00
        self.assertEqual(order.discount_amount, Decimal('2.00'))
        self.assertEqual(order.grand_total, Decimal('58.00'))
        self.assertEqual(order.total_items_count, 5)

        # Verify stock deducted
        self.p_healthy.refresh_from_db()
        self.assertEqual(self.p_healthy.quantity, initial_qty - 5) # 45

        # Verify transaction logged
        tx = StockTransaction.objects.filter(product=self.p_healthy, transaction_type='OUT').latest('id')
        self.assertEqual(tx.quantity, 5)
        self.assertEqual(tx.quantity_after, 45)
        self.assertIn(order.invoice_no, tx.notes)

        # Verify printable invoice view renders successfully
        res_invoice = self.client.get(reverse('sales_order_detail', kwargs={'pk': order.pk}))
        self.assertEqual(res_invoice.status_code, 200)
        self.assertContains(res_invoice, order.invoice_no)
        self.assertContains(res_invoice, 'John Doe')
        self.assertContains(res_invoice, 'Drill Bit Set')
        self.assertContains(res_invoice, '58.00')
        self.assertContains(res_invoice, 'Print Receipt')


