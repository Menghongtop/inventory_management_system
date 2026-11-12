from datetime import timedelta
from django.db.models import F
from django.utils import timezone
from .models import Product
from .translations import TRANSLATIONS

def inventory_context(request):
    current_lang = request.session.get('django_language', 'en') if hasattr(request, 'session') else 'en'
    t = TRANSLATIONS.get(current_lang, TRANSLATIONS['en'])

    if not request.user.is_authenticated:
        return {
            'current_lang': current_lang,
            't': t,
        }

    today = timezone.now().date()
    soon_threshold = today + timedelta(days=30)

    try:
        low_stock_count = Product.objects.filter(is_active=True, quantity__gt=0, quantity__lte=F('reorder_level')).count()
    except Exception:
        low_stock_count = 0

    try:
        out_of_stock_count = Product.objects.filter(is_active=True, quantity__lte=0).count()
    except Exception:
        out_of_stock_count = 0

    try:
        expired_count = Product.objects.filter(is_active=True, quantity__gt=0, expiry_date__lt=today).count()
    except Exception:
        expired_count = 0

    try:
        expiring_soon_count = Product.objects.filter(
            is_active=True, quantity__gt=0, expiry_date__gte=today, expiry_date__lte=soon_threshold
        ).count()
    except Exception:
        expiring_soon_count = 0

    total_expiry_alert_count = expired_count + expiring_soon_count

    user_role = 'staff'
    if hasattr(request.user, 'profile'):
        user_role = request.user.profile.role
    elif request.user.is_superuser:
        user_role = 'admin'

    return {
        'current_lang': current_lang,
        't': t,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'expired_count': expired_count,
        'expiring_soon_count': expiring_soon_count,
        'total_expiry_alert_count': total_expiry_alert_count,
        'total_alert_count': low_stock_count + out_of_stock_count + total_expiry_alert_count,
        'user_role': user_role,
        'is_admin': user_role == 'admin' or request.user.is_superuser,
        'is_manager': user_role in ['admin', 'manager'] or request.user.is_superuser,
    }
