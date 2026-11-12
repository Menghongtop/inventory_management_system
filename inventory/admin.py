from django.contrib import admin
from .models import UserProfile, Category, Supplier, Product, StockTransaction, Customer, SaleOrder, SaleOrderItem

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'phone', 'created_at')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'user__email', 'phone')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_perishable', 'alert_priority', 'shelf_life_days', 'product_count', 'created_at')
    list_filter = ('is_perishable',)
    search_fields = ('name', 'description')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'batch_no', 'expiry_date', 'expiry_status_label', 'quantity', 'reorder_level', 'cost_price', 'selling_price', 'status_label', 'is_active')
    list_filter = ('category', 'category__is_perishable', 'supplier', 'is_active')
    search_fields = ('sku', 'name', 'batch_no', 'location')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity', 'quantity_before', 'quantity_after', 'reference_no', 'created_by', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('product__name', 'product__sku', 'reference_no', 'notes')
    readonly_fields = ('created_at',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'total_orders', 'total_spent', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone', 'email', 'address')

class SaleOrderItemInline(admin.TabularInline):
    model = SaleOrderItem
    extra = 0
    readonly_fields = ('product_name', 'product_sku', 'unit_cost_price', 'unit_selling_price', 'quantity', 'line_total')

@admin.register(SaleOrder)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'display_customer_name', 'grand_total', 'payment_method', 'status', 'created_by', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('invoice_no', 'customer__name', 'customer_name', 'customer_phone')
    inlines = [SaleOrderItemInline]
