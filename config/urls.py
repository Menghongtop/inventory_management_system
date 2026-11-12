from django.contrib import admin
from django.urls import path, include
from inventory import views as inv_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', inv_views.login_view, name='login'),
    path('logout/', inv_views.logout_view, name='logout'),
    path('', include('inventory.urls')),
]
