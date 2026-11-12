from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Product, Category, Supplier, StockTransaction, UserProfile, Customer, SaleOrder, SaleOrderItem

# Base style for Tailwind form inputs
INPUT_STYLE = "w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-sm text-sm"
SELECT_STYLE = "w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-sm text-sm"
TEXTAREA_STYLE = "w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-sm text-sm resize-none"

class StyledLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': INPUT_STYLE,
            'placeholder': 'Enter your username',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': INPUT_STYLE,
            'placeholder': '••••••••',
        })

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'category', 'supplier',
            'cost_price', 'selling_price', 'quantity',
            'reorder_level', 'unit', 'expiry_date', 'batch_no',
            'location', 'description', 'is_active'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'e.g. PRD-1001'}),
            'name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Product name'}),
            'category': forms.Select(attrs={'class': SELECT_STYLE}),
            'supplier': forms.Select(attrs={'class': SELECT_STYLE}),
            'cost_price': forms.NumberInput(attrs={'class': INPUT_STYLE, 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': INPUT_STYLE, 'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': '0'}),
            'reorder_level': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': '0'}),
            'unit': forms.Select(attrs={'class': SELECT_STYLE}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': INPUT_STYLE}),
            'batch_no': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'e.g. LOT-2026-A1'}),
            'location': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Warehouse A, Shelf 2'}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 3, 'placeholder': 'Product notes/specifications...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-slate-300'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_perishable', 'shelf_life_days', 'alert_priority']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 2, 'placeholder': 'Category description...'}),
            'is_perishable': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-slate-300'}),
            'shelf_life_days': forms.NumberInput(attrs={'class': INPUT_STYLE, 'placeholder': 'e.g. 7, 30, 90 days', 'min': '1'}),
            'alert_priority': forms.NumberInput(attrs={'class': INPUT_STYLE, 'placeholder': 'e.g. 10 for urgent perishable, 1 for normal', 'min': '1'}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Supplier Company Name'}),
            'contact_person': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Contact Person'}),
            'email': forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'supplier@example.com'}),
            'phone': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': '+1 234 567 890'}),
            'address': forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 2, 'placeholder': 'Address...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-slate-300'}),
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Customer / Company Name'}),
            'contact_person': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Contact Person'}),
            'phone': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': '+1 555-0123'}),
            'email': forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'customer@example.com'}),
            'address': forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 2, 'placeholder': 'Address / Delivery location...'}),
            'notes': forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 2, 'placeholder': 'Customer notes or credit terms...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-slate-300'}),
        }

class StockMovementForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': SELECT_STYLE})
    )
    transaction_type = forms.ChoiceField(
        choices=[
            ('IN', 'Stock In (Purchase / Restock)'),
            ('OUT', 'Stock Out (Sale / Dispatch)'),
        ],
        widget=forms.Select(attrs={'class': SELECT_STYLE})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Quantity'})
    )
    reference_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'PO-8821, INV-4402, etc.'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 2, 'placeholder': 'Notes about this movement...'})
    )

class QuickAdjustmentForm(forms.Form):
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': INPUT_STYLE, 'placeholder': 'New target quantity on hand'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA_STYLE, 'rows': 2, 'placeholder': 'Reason for adjustment (e.g. Audit discrepancy, Damaged items)'})
    )

class UserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_STYLE})
    )
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Warehouse, Sales, Purchasing, etc.'})
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': '+1 555-0192'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Temporary Password'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'username'}),
            'email': forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'user@example.com'}),
            'first_name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Last Name'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.department = self.cleaned_data.get('department', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save()
        return user
