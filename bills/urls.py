from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('add-bill/', views.add_bill, name='add_bill'),
    path('edit-bill/<int:bill_id>/', views.edit_bill, name='edit_bill'),
    path('delete-bill/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    path('customers/', views.all_customers, name='all_customers'),
    path('customer/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('admin/add-customer/', views.admin_add_customer, name='admin_add_customer'),
    path('all-bills/', views.all_bills_view, name='all_bills'),

    # Customer URLs
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('profile/', views.update_profile, name='update_profile'),

    # Print
    path('print-bill/<int:bill_id>/', views.print_bill, name='print_bill'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)