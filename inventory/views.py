import csv
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db import transaction
from django.db.models import Sum, F, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator

from .models import (
    Product, Category, Supplier, StockTransaction, UserProfile,
    Customer, SaleOrder, SaleOrderItem
)
from .forms import (
    StyledLoginForm, ProductForm, CategoryForm,
    SupplierForm, CustomerForm, StockMovementForm, QuickAdjustmentForm, UserCreateForm
)

def role_required(allowed_roles):
    """Decorator to restrict access based on user role"""
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            profile = getattr(request.user, 'profile', None)
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Permission Denied: You do not have permission to access that resource.")
            return redirect('dashboard')
        return _wrapped_view
    return decorator


def switch_language(request, lang_code):
    """Switch active session language between 'en' and 'km'"""
    if lang_code in ['en', 'km']:
        request.session['django_language'] = lang_code
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = StyledLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = StyledLoginForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def dashboard(request):
    today = timezone.now().date()
    soon_threshold = today + timedelta(days=30)

    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')
    total_products = products.count()
    total_units_count = sum(p.quantity for p in products)

    # Stock quantity alerts
    low_stock_products = products.filter(quantity__gt=0, quantity__lte=F('reorder_level'))
    out_of_stock_products = products.filter(quantity__lte=0)

    # Expiration product alerts
    expired_products = products.filter(quantity__gt=0, expiry_date__lt=today)
    expiring_soon_products = products.filter(
        quantity__gt=0, expiry_date__gte=today, expiry_date__lte=soon_threshold
    )

    expired_count = expired_products.count()
    expiring_soon_count = expiring_soon_products.count()
    total_expiry_alert_count = expired_count + expiring_soon_count

    # Financial metrics
    total_inventory_cost = sum(p.total_cost_value for p in products)
    total_inventory_retail = sum(p.total_retail_value for p in products)

    # Sales Performance & Realized Profit from selling products
    sales_transactions = StockTransaction.objects.filter(transaction_type='OUT').select_related('product')
    total_products_sold = sum(t.quantity for t in sales_transactions)
    total_sales_revenue = sum(Decimal(t.quantity) * t.product.selling_price for t in sales_transactions)
    total_sales_cost = sum(Decimal(t.quantity) * t.product.cost_price for t in sales_transactions)
    total_sales_profit = total_sales_revenue - total_sales_cost
    sales_profit_margin = ((total_sales_profit / total_sales_revenue) * 100) if total_sales_revenue > 0 else Decimal('0.00')

    # Recent Transactions
    recent_transactions = StockTransaction.objects.select_related('product', 'created_by').order_by('-created_at')[:8]

    # Category Distribution for Chart
    category_data = (
        Category.objects.annotate(
            item_count=Count('products', filter=Q(products__is_active=True))
        )
        .filter(item_count__gt=0)
        .order_by('-item_count')[:6]
    )
    cat_labels = [c.name for c in category_data]
    cat_counts = [c.item_count for c in category_data]

    # 7-day movement trend
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    trend_labels = [d.strftime('%b %d') for d in days]
    trend_in = []
    trend_out = []

    for d in days:
        start_of_day = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time()))
        end_of_day = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.max.time()))

        in_qty = StockTransaction.objects.filter(
            transaction_type='IN',
            created_at__range=(start_of_day, end_of_day)
        ).aggregate(total=Sum('quantity'))['total'] or 0

        out_qty = StockTransaction.objects.filter(
            transaction_type='OUT',
            created_at__range=(start_of_day, end_of_day)
        ).aggregate(total=Sum('quantity'))['total'] or 0

        trend_in.append(in_qty)
        trend_out.append(out_qty)

    # Category-based stock alerts: Fast/easy to expire (perishable) categories alerted first
    categories_all = Category.objects.all()
    category_alerts = []
    for cat in categories_all:
        cat_prods = products.filter(category=cat)
        c_expired = cat_prods.filter(quantity__gt=0, expiry_date__lt=today).count()
        c_expiring = cat_prods.filter(quantity__gt=0, expiry_date__gte=today, expiry_date__lte=soon_threshold).count()
        c_low = cat_prods.filter(quantity__gt=0, quantity__lte=F('reorder_level')).count()
        c_out = cat_prods.filter(quantity__lte=0).count()
        c_total_alerts = c_expired + c_expiring + c_low + c_out

        category_alerts.append({
            'category': cat,
            'is_perishable': cat.is_perishable,
            'alert_priority': cat.alert_priority,
            'expired_count': c_expired,
            'expiring_soon_count': c_expiring,
            'low_stock_count': c_low,
            'out_of_stock_count': c_out,
            'total_alerts': c_total_alerts,
            'total_products': cat_prods.count(),
        })

    # Sort so that easy/fast to expire categories ALWAYS appear first!
    category_alerts.sort(key=lambda x: (not x['is_perishable'], -x['alert_priority'], -x['total_alerts'], x['category'].name))

    # Priority ranking for individual alert items (perishable & fast-to-expire items alerted first)
    def alert_item_priority(p):
        is_perish = p.is_perishable
        if p.is_expired:
            return (0 if is_perish else 2, 0, p.days_until_expiry or 0)
        elif p.is_expiring_soon:
            return (0 if is_perish else 2, 1, p.days_until_expiry or 0)
        elif p.quantity <= 0:
            return (1 if is_perish else 3, 0, 0)
        elif p.quantity <= p.reorder_level:
            return (1 if is_perish else 3, 1, p.quantity)
        return (4, 4, 0)

    alert_candidates = [
        p for p in products
        if p.is_expired or p.is_expiring_soon or p.quantity <= p.reorder_level or p.quantity <= 0
    ]
    alert_candidates.sort(key=alert_item_priority)
    urgent_alert_items = alert_candidates[:7]

    context = {
        'total_products': total_products,
        'total_units_count': total_units_count,
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock_products.count(),
        'expired_count': expired_count,
        'expiring_soon_count': expiring_soon_count,
        'total_expiry_alert_count': total_expiry_alert_count,
        'total_inventory_cost': total_inventory_cost,
        'total_inventory_retail': total_inventory_retail,
        'total_products_sold': total_products_sold,
        'total_sales_revenue': total_sales_revenue,
        'total_sales_cost': total_sales_cost,
        'total_sales_profit': total_sales_profit,
        'sales_profit_margin': sales_profit_margin,
        'recent_transactions': recent_transactions,
        'urgent_alert_items': urgent_alert_items,
        'category_alerts': category_alerts,
        'cat_labels': cat_labels,
        'cat_counts': cat_counts,
        'trend_labels': trend_labels,
        'trend_in': trend_in,
        'trend_out': trend_out,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def product_list(request):
    products = Product.objects.select_related('category', 'supplier').all()

    # Search query
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(location__icontains=query)
        )

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    today = timezone.now().date()
    soon_threshold = today + timedelta(days=30)

    # Status filter
    status = request.GET.get('status')
    if status == 'in_stock':
        products = products.filter(quantity__gt=F('reorder_level'))
    elif status == 'low_stock':
        products = products.filter(quantity__gt=0, quantity__lte=F('reorder_level'))
    elif status == 'out_of_stock':
        products = products.filter(quantity__lte=0)
    elif status == 'expired':
        products = products.filter(quantity__gt=0, expiry_date__lt=today)
    elif status == 'expiring_soon':
        products = products.filter(quantity__gt=0, expiry_date__gte=today, expiry_date__lte=soon_threshold)
    elif status == 'perishable':
        products = products.filter(category__is_perishable=True)

    # Sorting
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = [
        'name', '-name', 'quantity', '-quantity',
        'selling_price', '-selling_price', '-created_at',
        'expiry_date', '-expiry_date', 'category_priority'
    ]
    if sort == 'expiry_date':
        products = products.order_by(F('expiry_date').asc(nulls_last=True))
    elif sort == '-expiry_date':
        products = products.order_by(F('expiry_date').desc(nulls_last=True))
    elif sort == 'category_priority':
        products = products.order_by('-category__is_perishable', '-category__alert_priority', 'name')
    elif sort in valid_sorts:
        products = products.order_by(sort)

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'selected_status': status,
        'selected_sort': sort,
    }
    return render(request, 'inventory/product_list.html', context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'supplier'), pk=pk)
    transactions = product.transactions.select_related('created_by').order_by('-created_at')[:15]
    adj_form = QuickAdjustmentForm(initial={'quantity': product.quantity})
    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'transactions': transactions,
        'adj_form': adj_form,
    })


@login_required
@role_required(['admin', 'manager'])
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            # Initial stock transaction if initial quantity > 0
            if product.quantity > 0:
                StockTransaction.objects.create(
                    product=product,
                    transaction_type='IN',
                    quantity=product.quantity,
                    quantity_before=0,
                    quantity_after=product.quantity,
                    reference_no="INIT-STOCK",
                    notes="Initial stock quantity at creation",
                    created_by=request.user
                )
            messages.success(request, f"Product '{product.name}' was created successfully!")
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add New Product'})


@login_required
@role_required(['admin', 'manager'])
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' was updated successfully!")
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': f'Edit {product.name}', 'product': product})


@login_required
@role_required(['admin'])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f"Product '{name}' was permanently deleted.")
        return redirect('product_list')
    return render(request, 'inventory/confirm_delete.html', {
        'object': product,
        'type': 'Product',
        'cancel_url': 'product_detail',
        'cancel_pk': product.pk
    })


@login_required
def stock_movement(request):
    initial_product_id = request.GET.get('product')
    initial_product = None
    if initial_product_id:
        initial_product = Product.objects.filter(pk=initial_product_id).first()

    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            movement_type = form.cleaned_data['transaction_type']
            qty = form.cleaned_data['quantity']
            ref_no = form.cleaned_data.get('reference_no', '')
            notes = form.cleaned_data.get('notes', '')

            qty_before = product.quantity

            if movement_type == 'OUT':
                if product.quantity < qty:
                    messages.error(request, f"Cannot stock out {qty} units. Only {product.quantity} units available in stock.")
                    return render(request, 'inventory/stock_movement.html', {'form': form})
                product.quantity -= qty
            else: # IN
                product.quantity += qty

            product.save()

            StockTransaction.objects.create(
                product=product,
                transaction_type=movement_type,
                quantity=qty,
                quantity_before=qty_before,
                quantity_after=product.quantity,
                reference_no=ref_no,
                notes=notes,
                created_by=request.user
            )

            messages.success(request, f"Successfully recorded {movement_type} movement of {qty} {product.unit} for '{product.name}'.")
            return redirect('product_detail', pk=product.pk)
    else:
        form = StockMovementForm(initial={'product': initial_product} if initial_product else {})

    return render(request, 'inventory/stock_movement.html', {'form': form, 'selected_product': initial_product})


@login_required
@role_required(['admin', 'manager'])
def product_adjust_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = QuickAdjustmentForm(request.POST)
        if form.is_valid():
            new_qty = form.cleaned_data['quantity']
            reason = form.cleaned_data.get('reason', 'Stock count audit / adjustment')

            if new_qty < 0:
                messages.error(request, "Stock quantity cannot be negative.")
                return redirect('product_detail', pk=product.pk)

            qty_before = product.quantity
            delta = new_qty - qty_before
            product.quantity = new_qty
            product.save()

            StockTransaction.objects.create(
                product=product,
                transaction_type='ADJUST',
                quantity=delta,
                quantity_before=qty_before,
                quantity_after=new_qty,
                reference_no="AUDIT-ADJ",
                notes=reason,
                created_by=request.user
            )

            messages.success(request, f"Inventory for '{product.name}' was adjusted from {qty_before} to {new_qty}.")
            return redirect('product_detail', pk=product.pk)

    return redirect('product_detail', pk=product.pk)


@login_required
def transaction_list(request):
    transactions = StockTransaction.objects.select_related('product', 'created_by').all()

    tx_type = request.GET.get('type')
    if tx_type in ['IN', 'OUT', 'ADJUST']:
        transactions = transactions.filter(transaction_type=tx_type)

    query = request.GET.get('q', '').strip()
    if query:
        transactions = transactions.filter(
            Q(product__name__icontains=query) |
            Q(product__sku__icontains=query) |
            Q(reference_no__icontains=query)
        )

    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/transaction_list.html', {
        'page_obj': page_obj,
        'selected_type': tx_type,
        'query': query,
    })


@login_required
def category_list(request):
    categories = Category.objects.annotate(
        prod_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('name')

    if request.method == 'POST' and (request.user.is_superuser or request.user.profile.is_manager):
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' created!")
            return redirect('category_list')
    else:
        form = CategoryForm()

    return render(request, 'inventory/category_list.html', {
        'categories': categories,
        'form': form,
    })


@login_required
@role_required(['admin', 'manager'])
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted.")
        return redirect('category_list')
    return render(request, 'inventory/confirm_delete.html', {
        'object': category,
        'type': 'Category',
        'cancel_url': 'category_list'
    })


@login_required
def supplier_list(request):
    suppliers = Supplier.objects.annotate(prod_count=Count('products')).order_by('name')

    if request.method == 'POST' and (request.user.is_superuser or request.user.profile.is_manager):
        form = SupplierForm(request.POST)
        if form.is_valid():
            sup = form.save()
            messages.success(request, f"Supplier '{sup.name}' created!")
            return redirect('supplier_list')
    else:
        form = SupplierForm()

    return render(request, 'inventory/supplier_list.html', {
        'suppliers': suppliers,
        'form': form,
    })


@login_required
@role_required(['admin', 'manager'])
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated!")
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form, 'supplier': supplier})


@login_required
@role_required(['admin'])
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{name}' deleted.")
        return redirect('supplier_list')
    return render(request, 'inventory/confirm_delete.html', {
        'object': supplier,
        'type': 'Supplier',
        'cancel_url': 'supplier_list'
    })


@login_required
@role_required(['admin'])
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            u = form.save()
            messages.success(request, f"User account '{u.username}' was created with role {u.profile.get_role_display()}!")
            return redirect('user_list')
    else:
        form = UserCreateForm()

    return render(request, 'inventory/user_list.html', {
        'users': users,
        'form': form,
    })


@login_required
@role_required(['admin'])
def user_toggle_status(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('user_list')

    target_user.is_active = not target_user.is_active
    target_user.save()
    status_str = "activated" if target_user.is_active else "deactivated"
    messages.success(request, f"User '{target_user.username}' was {status_str}.")
    return redirect('user_list')


@login_required
def export_products_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_products.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'SKU', 'Name', 'Category', 'Perishable / Fast Expire', 'Batch / Lot #',
        'Quantity', 'Unit', 'Cost Price', 'Selling Price', 'Total Value',
        'Stock Status', 'Expiry Date', 'Expiry Status', 'Location'
    ])

    for p in Product.objects.select_related('category').all():
        cat_name = p.category.name if p.category else 'Uncategorized'
        is_perish = 'Yes (Fast to Expire)' if (p.category and p.category.is_perishable) else 'No'
        writer.writerow([
            p.sku,
            p.name,
            cat_name,
            is_perish,
            p.batch_no or 'N/A',
            p.quantity,
            p.unit,
            p.cost_price,
            p.selling_price,
            p.total_retail_value,
            p.status_label,
            p.expiry_date.strftime('%Y-%m-%d') if p.expiry_date else 'N/A',
            p.expiry_status_label,
            p.location or 'N/A',
        ])
    return response


@login_required
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date & Time', 'Product SKU', 'Product Name', 'Movement Type', 'Quantity', 'Before', 'After', 'Reference', 'Staff User', 'Notes'])

    for t in StockTransaction.objects.select_related('product', 'created_by').all():
        writer.writerow([
            t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            t.product.sku,
            t.product.name,
            t.get_transaction_type_display(),
            t.quantity,
            t.quantity_before,
            t.quantity_after,
            t.reference_no,
            t.created_by.username if t.created_by else 'System',
            t.notes,
        ])
    return response


# ==========================================
# CUSTOMER MANAGEMENT VIEWS
# ==========================================

@login_required
def customer_list(request):
    customers = Customer.objects.annotate(
        orders_count=Count('sales_orders')
    ).order_by('name')

    query = request.GET.get('q', '').strip()
    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(address__icontains=query)
        )

    if request.method == 'POST' and (request.user.is_superuser or request.user.profile.is_manager):
        form = CustomerForm(request.POST)
        if form.is_valid():
            cust = form.save()
            messages.success(request, f"Customer '{cust.name}' added successfully!")
            return redirect('customer_list')
    else:
        form = CustomerForm()

    paginator = Paginator(customers, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/customer_list.html', {
        'page_obj': page_obj,
        'form': form,
        'query': query,
    })


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales_orders = customer.sales_orders.select_related('created_by').order_by('-created_at')[:20]
    return render(request, 'inventory/customer_detail.html', {
        'customer': customer,
        'sales_orders': sales_orders,
    })


@login_required
@role_required(['admin', 'manager'])
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer '{customer.name}' updated successfully!")
            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'inventory/customer_form.html', {'form': form, 'customer': customer})


@login_required
@role_required(['admin'])
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = customer.name
        customer.delete()
        messages.success(request, f"Customer '{name}' was deleted.")
        return redirect('customer_list')
    return render(request, 'inventory/confirm_delete.html', {
        'object': customer,
        'type': 'Customer',
        'cancel_url': 'customer_list'
    })


# ==========================================
# MULTI-ITEM SALES CHECKOUT & INVOICING (POS)
# ==========================================

@login_required
def sales_order_list(request):
    orders = SaleOrder.objects.select_related('customer', 'created_by').all()

    query = request.GET.get('q', '').strip()
    if query:
        orders = orders.filter(
            Q(invoice_no__icontains=query) |
            Q(customer__name__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )

    payment_method = request.GET.get('payment_method')
    if payment_method:
        orders = orders.filter(payment_method=payment_method)

    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/sales_order_list.html', {
        'page_obj': page_obj,
        'query': query,
        'selected_payment': payment_method,
        'selected_status': status,
    })


@login_required
def sales_order_create(request):
    """Multi-item Sales Checkout (POS) with dynamic items and automatic stock deduction"""
    available_products = Product.objects.filter(is_active=True).order_by('name')
    customers = Customer.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        try:
            cart_data_raw = request.POST.get('cart_data', '[]')
            cart_items = json.loads(cart_data_raw)

            if not cart_items:
                messages.error(request, "Please add at least one product to the checkout cart.")
                return redirect('sales_order_create')

            customer_id = request.POST.get('customer')
            walk_in_name = request.POST.get('customer_name', '').strip()
            walk_in_phone = request.POST.get('customer_phone', '').strip()
            payment_method = request.POST.get('payment_method', 'CASH')
            order_notes = request.POST.get('notes', '').strip()
            discount_amount = Decimal(request.POST.get('discount_amount', '0.00') or '0.00')
            tax_amount = Decimal(request.POST.get('tax_amount', '0.00') or '0.00')

            customer = None
            if customer_id:
                customer = Customer.objects.filter(pk=customer_id).first()

            # Atomic transaction to guarantee stock consistency
            with transaction.atomic():
                # 1. Validate all stock availability before making any changes
                line_items_to_create = []
                subtotal = Decimal('0.00')

                for item in cart_items:
                    prod_id = item.get('product_id')
                    qty = int(item.get('quantity', 1))

                    if qty <= 0:
                        continue

                    prod = Product.objects.select_for_update().get(pk=prod_id)
                    if prod.quantity < qty:
                        messages.error(
                            request,
                            f"Insufficient stock for '{prod.name}'. Requested: {qty}, Available: {prod.quantity}."
                        )
                        return redirect('sales_order_create')

                    line_price = Decimal(str(item.get('unit_price', prod.selling_price)))
                    line_total = line_price * qty
                    subtotal += line_total

                    line_items_to_create.append({
                        'product': prod,
                        'qty': qty,
                        'unit_price': line_price,
                        'cost_price': prod.cost_price,
                        'line_total': line_total,
                    })

                grand_total = max(Decimal('0.00'), subtotal - discount_amount + tax_amount)

                # Generate unique invoice number: INV-YYYYMMDD-XXXX
                date_str = timezone.now().strftime('%Y%m%d')
                short_code = uuid.uuid4().hex[:4].upper()
                invoice_no = f"INV-{date_str}-{short_code}"

                # 2. Create SaleOrder
                order = SaleOrder.objects.create(
                    invoice_no=invoice_no,
                    customer=customer,
                    customer_name=walk_in_name if not customer else customer.name,
                    customer_phone=walk_in_phone if not customer else customer.phone,
                    subtotal=subtotal,
                    discount_amount=discount_amount,
                    tax_amount=tax_amount,
                    grand_total=grand_total,
                    payment_method=payment_method,
                    status='COMPLETED',
                    notes=order_notes,
                    created_by=request.user
                )

                # 3. Create SaleOrderItems, deduct stock, and create StockTransactions
                for line in line_items_to_create:
                    prod = line['product']
                    qty = line['qty']
                    qty_before = prod.quantity
                    qty_after = qty_before - qty

                    SaleOrderItem.objects.create(
                        order=order,
                        product=prod,
                        product_name=prod.name,
                        product_sku=prod.sku,
                        unit_cost_price=line['cost_price'],
                        unit_selling_price=line['unit_price'],
                        quantity=qty,
                        line_total=line['line_total'],
                    )

                    # Deduct physical stock
                    prod.quantity = qty_after
                    prod.save()

                    # Record transaction log
                    StockTransaction.objects.create(
                        product=prod,
                        transaction_type='OUT',
                        quantity=qty,
                        quantity_before=qty_before,
                        quantity_after=qty_after,
                        reference_no=invoice_no,
                        notes=f"Sale Invoice #{invoice_no} to {order.display_customer_name}",
                        created_by=request.user
                    )

            messages.success(request, f"Sale Order #{order.invoice_no} completed successfully!")
            return redirect('sales_order_detail', pk=order.pk)

        except Exception as e:
            messages.error(request, f"Error processing sales checkout: {e}")
            return redirect('sales_order_create')

    # Prepare JSON products data for live instant client-side cart search
    products_json = [
        {
            'id': p.pk,
            'name': p.name,
            'sku': p.sku,
            'category': p.category.name if p.category else 'Uncategorized',
            'selling_price': float(p.selling_price),
            'quantity': p.quantity,
            'unit': p.unit,
            'expiry_status': p.expiry_status_label,
            'is_perishable': p.is_perishable,
        }
        for p in available_products
    ]

    return render(request, 'inventory/sales_order_form.html', {
        'available_products': available_products,
        'customers': customers,
        'products_json': json.dumps(products_json),
    })


@login_required
def sales_order_detail(request, pk):
    """Printable invoice and receipt view"""
    order = get_object_or_404(
        SaleOrder.objects.select_related('customer', 'created_by').prefetch_related('items__product'),
        pk=pk
    )
    return render(request, 'inventory/sales_order_detail.html', {
        'order': order,
    })
