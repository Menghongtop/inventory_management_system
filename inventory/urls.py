from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Language
    path('', views.dashboard, name='dashboard'),
    path('switch-language/<str:lang_code>/', views.switch_language, name='switch_language'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/adjust/', views.product_adjust_stock, name='product_adjust_stock'),

    # Stock movements
    path('movements/new/', views.stock_movement, name='stock_movement'),
    path('transactions/', views.transaction_list, name='transaction_list'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Customers Directory
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/quick-create/', views.customer_quick_create, name='customer_quick_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # Sales Orders & POS Checkout
    path('sales/', views.sales_order_list, name='sales_order_list'),
    path('sales/checkout/', views.sales_order_create, name='sales_order_create'),
    path('sales/<int:pk>/', views.sales_order_detail, name='sales_order_detail'),

    # User Management (Admin Only)
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/toggle/', views.user_toggle_status, name='user_toggle_status'),

    # Exports
    path('export/products/', views.export_products_csv, name='export_products_csv'),
    path('export/transactions/', views.export_transactions_csv, name='export_transactions_csv'),
]
