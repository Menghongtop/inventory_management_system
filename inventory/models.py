from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'System Administrator'),
        ('manager', 'Inventory Manager'),
        ('staff', 'Staff Member'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True, default='Inventory')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser

    @property
    def is_manager(self):
        return self.role in ['admin', 'manager'] or self.user.is_superuser


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'admin' if instance.is_superuser else 'staff'
        UserProfile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            if instance.is_superuser and instance.profile.role != 'admin':
                instance.profile.role = 'admin'
                instance.profile.save()
        else:
            role = 'admin' if instance.is_superuser else 'staff'
            UserProfile.objects.create(user=instance, role=role)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_perishable = models.BooleanField(
        default=False,
        verbose_name="Easy / Fast to Expire",
        help_text="Designate if this category has items that easily or fast expire (e.g. food, dairy, medicine, perishables)"
    )
    shelf_life_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Default Shelf Life (Days)",
        help_text="Typical shelf life in days"
    )
    alert_priority = models.PositiveIntegerField(
        default=1,
        verbose_name="Alert Priority",
        help_text="Priority rank: 10 for urgent perishable categories, 1 for standard"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['-alert_priority', 'name']

    def __str__(self):
        return self.name

    @property
    def product_count(self):
        return self.products.count()


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Pieces (pcs)'),
        ('box', 'Box'),
        ('kg', 'Kilograms (kg)'),
        ('g', 'Grams (g)'),
        ('ltr', 'Liters (ltr)'),
        ('pack', 'Pack'),
        ('set', 'Set'),
    ]

    sku = models.CharField(max_length=50, unique=True, help_text="Unique Stock Keeping Unit")
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10, help_text="Trigger alert when quantity is at or below this level")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs')
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Expiry Date",
        help_text="Expiration date for perishable goods"
    )
    batch_no = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Batch / Lot Number",
        help_text="Batch or Lot code for inventory tracking"
    )
    location = models.CharField(max_length=100, blank=True, help_text="e.g. Warehouse A, Shelf 3B")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    @property
    def is_perishable(self):
        return bool(self.category and self.category.is_perishable)

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            return (self.expiry_date - timezone.now().date()).days
        return None

    @property
    def days_expired(self):
        if self.days_until_expiry is not None and self.days_until_expiry < 0:
            return abs(self.days_until_expiry)
        return 0

    @property
    def is_expired(self):
        if self.expiry_date and self.quantity > 0:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def is_expiring_soon(self):
        if self.expiry_date and self.quantity > 0:
            today = timezone.now().date()
            return today <= self.expiry_date <= (today + timedelta(days=30))
        return False

    @property
    def expiry_status(self):
        if not self.expiry_date or self.quantity <= 0:
            return 'none'
        days = self.days_until_expiry
        if days < 0:
            return 'expired'
        elif days <= 30:
            return 'expiring_soon'
        return 'fresh'

    @property
    def expiry_status_label(self):
        if not self.expiry_date:
            return 'No Expiry'
        if self.quantity <= 0:
            return 'Depleted'
        days = self.days_until_expiry
        if days < 0:
            return f"Expired ({abs(days)}d ago)"
        elif days == 0:
            return "Expires Today!"
        elif days <= 30:
            return f"Expires in {days}d"
        return f"Good ({days}d left)"

    @property
    def status(self):
        if self.quantity <= 0:
            return 'out_of_stock'
        elif self.quantity <= self.reorder_level:
            return 'low_stock'
        return 'in_stock'

    @property
    def status_label(self):
        if self.quantity <= 0:
            return 'Out of Stock'
        elif self.quantity <= self.reorder_level:
            return 'Low Stock'
        return 'In Stock'

    @property
    def total_cost_value(self):
        return Decimal(self.quantity) * self.cost_price

    @property
    def total_retail_value(self):
        return Decimal(self.quantity) * self.selling_price

    @property
    def potential_profit(self):
        return self.total_retail_value - self.total_cost_value


class StockTransaction(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Stock In (Purchase/Restock)'),
        ('OUT', 'Stock Out (Sale/Dispatch)'),
        ('ADJUST', 'Inventory Adjustment (Audit/Damage/Return)'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Units added, removed, or net delta")
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reference_no = models.CharField(max_length=100, blank=True, help_text="PO#, Invoice#, or Audit ID")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity})"

    @property
    def total_revenue(self):
        if self.transaction_type == 'OUT':
            return Decimal(self.quantity) * self.product.selling_price
        return Decimal('0.00')

    @property
    def total_cost(self):
        if self.transaction_type == 'OUT':
            return Decimal(self.quantity) * self.product.cost_price
        return Decimal('0.00')

    @property
    def total_profit(self):
        if self.transaction_type == 'OUT':
            return self.total_revenue - self.total_cost
        return Decimal('0.00')


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name}{f' ({self.phone})' if self.phone else ''}"

    @property
    def total_orders(self):
        return self.sales_orders.count()

    @property
    def total_spent(self):
        orders = self.sales_orders.filter(status='COMPLETED')
        return sum(o.grand_total for o in orders) or Decimal('0.00')


class SaleOrder(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer (ABA / KHQR / Wire)'),
        ('CARD', 'Credit / Debit Card'),
        ('OTHER', 'Other / Credit'),
    ]

    STATUS_CHOICES = [
        ('COMPLETED', 'Completed / Paid'),
        ('PENDING', 'Pending / Unpaid'),
        ('CANCELLED', 'Cancelled'),
    ]

    invoice_no = models.CharField(max_length=50, unique=True, help_text="e.g. INV-2026-0001")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    customer_name = models.CharField(max_length=150, blank=True, help_text="Walk-in customer name if not registered")
    customer_phone = models.CharField(max_length=50, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_no} - {self.display_customer_name} (${self.grand_total})"

    @property
    def display_customer_name(self):
        if self.customer:
            return self.customer.name
        return self.customer_name or "Walk-in Customer"

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_cost(self):
        return sum(item.line_cost for item in self.items.all())

    @property
    def total_profit(self):
        return self.grand_total - self.total_cost


class SaleOrderItem(models.Model):
    order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    unit_cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def line_cost(self):
        return Decimal(self.quantity) * self.unit_cost_price

    @property
    def line_profit(self):
        return self.line_total - self.line_cost
