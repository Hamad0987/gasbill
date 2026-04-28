from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Avg, Q, Sum
from django.http import HttpResponse
from django.conf import settings
from django.core.cache import cache
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import CustomerProfile, Bill
from .forms import RegisterForm, BillForm, ProfileUpdateForm
import io
import random

def is_admin(user):
    return user.is_staff

# ─── HOME PAGE ────────────────────────────────────────────

def home_page(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('customer_dashboard')
    return render(request, 'bills/home.html')

# ─── AUTH VIEWS ───────────────────────────────────────────

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                old_user = User.objects.get(username=email)
                if hasattr(old_user, 'customerprofile') and not old_user.customerprofile.is_verified:
                    old_user.delete()
            except User.DoesNotExist:
                pass
            user = User.objects.create_user(
                username=email,
                email=email,
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            profile = CustomerProfile.objects.create(
                user=user,
                meter_no=form.cleaned_data['meter_no'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                profile_pic=request.FILES.get('profile_pic'),
            )
            otp = profile.generate_otp()
            send_mail(
                'Gas Bill System - Email Verification OTP',
                f'Your OTP is: {otp}\nValid for 10 minutes.',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
            request.session['verify_user_id'] = user.id
            return redirect('verify_otp')
    else:
        form = RegisterForm()
    return render(request, 'bills/register.html', {'form': form})


def verify_otp_view(request):
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return redirect('register')
    user = get_object_or_404(User, id=user_id)
    profile = user.customerprofile
    error = None
    if request.method == 'POST':
        entered = request.POST.get('otp')
        if entered == profile.otp:
            profile.is_verified = True
            profile.otp = ''
            profile.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('customer_dashboard')
        else:
            error = 'Galat OTP! Dobara try karo.'
    return render(request, 'bills/verify_otp.html', {'error': error, 'email': user.email})


def login_view(request):
    error = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'customer')
        user = authenticate(request, username=email, password=password)
        if user:
            if role == 'admin':
                if user.is_staff:
                    login(request, user)
                    return redirect('admin_dashboard')
                else:
                    error = 'Aap admin nahi hain!'
            else:
                if user.is_staff:
                    error = 'Admin portal use karo!'
                else:
                    try:
                        if user.customerprofile.is_verified:
                            login(request, user)
                            return redirect('customer_dashboard')
                        else:
                            error = 'Email verify nahi hai!'
                    except:
                        error = 'Profile nahi mili!'
        else:
            error = 'Email ya password galat hai!'
    return render(request, 'bills/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('home')


def forgot_password_view(request):
    error = None
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            cache.set(f'reset_otp_{email}', otp, 600)
            send_mail(
                'Gas Bill System - Password Reset OTP',
                f'Your password reset OTP is: {otp}\nValid for 10 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            request.session['reset_email'] = email
            return redirect('reset_password')
        except User.DoesNotExist:
            error = 'Ye email registered nahi hai!'
    return render(request, 'bills/forgot_password.html', {'error': error})


def reset_password_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
    error = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify_otp':
            entered_otp = request.POST.get('otp')
            saved_otp = cache.get(f'reset_otp_{email}')
            if entered_otp == saved_otp:
                request.session['otp_verified'] = True
            else:
                error = 'Galat OTP! Dobara try karo.'
        elif action == 'set_password':
            if request.session.get('otp_verified'):
                password = request.POST.get('password')
                confirm = request.POST.get('confirm_password')
                if password != confirm:
                    error = 'Passwords match nahi karte!'
                else:
                    user = User.objects.get(email=email)
                    user.set_password(password)
                    user.save()
                    cache.delete(f'reset_otp_{email}')
                    del request.session['reset_email']
                    del request.session['otp_verified']
                    return redirect('login')
            else:
                error = 'OTP verify nahi hua!'
    otp_verified = request.session.get('otp_verified', False)
    return render(request, 'bills/reset_password.html', {
        'email': email, 'error': error, 'otp_verified': otp_verified
    })

# ─── ADMIN VIEWS ──────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    customers = CustomerProfile.objects.all()
    bills = Bill.objects.all().order_by('-created_at')[:50]
    total_amount = Bill.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'bills/admin_dashboard.html', {
        'customers': customers,
        'bills': bills,
        'total_amount': total_amount,
        'total_customers': customers.count(),
        'total_bills': Bill.objects.count(),
    })


@login_required
@user_passes_test(is_admin)
def add_bill(request):
    form = BillForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('admin_dashboard')
    return render(request, 'bills/add_bill.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def edit_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    form = BillForm(request.POST or None, request.FILES or None, instance=bill)
    if form.is_valid():
        form.save()
        return redirect('admin_dashboard')
    return render(request, 'bills/edit_bill.html', {'form': form, 'bill': bill})


@login_required
@user_passes_test(is_admin)
def delete_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    if request.method == 'POST':
        bill.delete()
        return redirect('admin_dashboard')
    return render(request, 'bills/delete_bill.html', {'bill': bill})


@login_required
@user_passes_test(is_admin)
def all_customers(request):
    customers = CustomerProfile.objects.all()
    search_query = request.GET.get('q')
    if search_query:
        customers = customers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(meter_no__icontains=search_query)
        )
    return render(request, 'bills/all_customers.html', {'customers': customers})


@login_required
@user_passes_test(is_admin)
def customer_detail(request, customer_id):
    customer = get_object_or_404(CustomerProfile, id=customer_id)
    bills = customer.bills.all().order_by('-year', 'month')
    years = bills.values_list('year', flat=True).distinct()
    year_averages = {}
    for year in years:
        avg = customer.bills.filter(year=year).aggregate(Avg('amount'))['amount__avg']
        year_averages[year] = round(avg, 2) if avg else 0
    return render(request, 'bills/customer_detail.html', {
        'customer': customer, 'bills': bills, 'year_averages': year_averages
    })


@login_required
@user_passes_test(is_admin)
def admin_add_customer(request):
    error = None
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        meter_no = request.POST.get('meter_no')
        address = request.POST.get('address', '')
        password = request.POST.get('password')
        if User.objects.filter(username=email).exists():
            error = 'Ye email already registered hai!'
        else:
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            CustomerProfile.objects.create(
                user=user, meter_no=meter_no, phone=phone,
                address=address, is_verified=True,
                profile_pic=request.FILES.get('profile_pic')
            )
            return redirect('all_customers')
    return render(request, 'bills/admin_add_customer.html', {'error': error})


@login_required
@user_passes_test(is_admin)
def all_bills_view(request):
    bills = Bill.objects.all().order_by('-year', 'month')
    return render(request, 'bills/all_bills.html', {'bills': bills})

# ─── CUSTOMER VIEWS ───────────────────────────────────────

@login_required
def customer_dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    profile = request.user.customerprofile
    bills = profile.bills.all().order_by('-year', 'month')
    total_due = bills.filter(is_paid=False).aggregate(Sum('amount'))['amount__sum'] or 0
    overall_avg = bills.aggregate(Avg('amount'))['amount__avg'] or 0
    years = bills.values_list('year', flat=True).distinct()
    year_averages = {}
    for year in years:
        avg = profile.bills.filter(year=year).aggregate(Avg('amount'))['amount__avg']
        year_averages[year] = round(avg, 2) if avg else 0
    return render(request, 'bills/customer_dashboard.html', {
        'profile': profile,
        'bills': bills,
        'year_averages': year_averages,
        'total_due': total_due,
        'overall_avg': round(overall_avg, 2),
    })


@login_required
def update_profile(request):
    profile = request.user.customerprofile
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('customer_dashboard')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'bills/update_profile.html', {'form': form})

# ─── PRINT VIEWS ──────────────────────────────────────────

@login_required
def print_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    p.setFillColorRGB(0.0, 0.4, 0.2)
    p.rect(0, height-110, width, 110, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height-45, "GAS BILL MANAGEMENT SYSTEM")
    p.setFont("Helvetica", 11)
    p.drawString(50, height-65, "Sui Gas Distribution Network")
    p.setFont("Helvetica", 9)
    p.drawString(50, height-82, "Helpline: 1199  |  info@gasbill.pk")

    # Bill info box
    p.setFillColorRGB(0.95, 0.95, 0.95)
    p.rect(width-180, height-105, 160, 60, fill=1)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-170, height-55, f"Bill No: GBS-{bill.id:05d}")
    p.drawString(width-170, height-70, f"Month: {bill.month} {bill.year}")
    p.drawString(width-170, height-85, f"Due Date: 15 {bill.month} {bill.year}")

    # Customer Info
    p.setFillColorRGB(0.0, 0.4, 0.2)
    p.rect(30, height-145, width-60, 22, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, height-133, "CUSTOMER INFORMATION")

    p.setFillColorRGB(0, 0, 0)
    info = [
        (40, height-165, "Consumer Name:", bill.customer.user.get_full_name()),
        (40, height-180, "Meter Number:", bill.customer.meter_no),
        (40, height-195, "Address:", bill.customer.address[:60]),
        (320, height-165, "Phone:", bill.customer.phone),
    ]
    for x, y, label, value in info:
        p.setFont("Helvetica-Bold", 9)
        p.drawString(x, y, label)
        p.setFont("Helvetica", 9)
        p.drawString(x + 80, y, value)

    # Reading Table
    p.setFillColorRGB(0.0, 0.4, 0.2)
    p.rect(30, height-230, width-60, 22, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, height-218, "METER READING DETAILS")

    p.setFillColorRGB(0.85, 0.85, 0.85)
    p.rect(30, height-255, width-60, 20, fill=1)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    headers = ["Month", "Year", "Reading (CFT)", "Amount"]
    x_pos = [40, 150, 260, 400]
    for h, x in zip(headers, x_pos):
        p.drawString(x, height-245, h)

    p.setFillColorRGB(0.97, 0.97, 0.97)
    p.rect(30, height-275, width-60, 18, fill=1)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 9)
    values = [bill.month, str(bill.year), str(bill.reading), f"Rs. {bill.amount}"]
    for v, x in zip(values, x_pos):
        p.drawString(x, height-265, v)

    # Amount & Status
    p.setFillColorRGB(0.0, 0.4, 0.2)
    p.rect(width-200, height-330, 170, 45, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(width-190, height-305, "TOTAL PAYABLE")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(width-190, height-325, f"Rs. {bill.amount}")

    if bill.is_paid:
        p.setFillColorRGB(0.1, 0.6, 0.1)
    else:
        p.setFillColorRGB(0.8, 0.1, 0.1)
    p.rect(30, height-330, 120, 45, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height-312, "PAID" if bill.is_paid else "UNPAID")

    # Bill Image
    if bill.bill_image:
        try:
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Helvetica-Bold", 10)
            p.drawString(40, height-360, "Attached Bill Image:")
            p.drawImage(bill.bill_image.path, 30, height-560,
                       width=250, height=180, preserveAspectRatio=True)
        except:
            pass

    # Instructions
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, height-380, "Payment Instructions:")
    p.setFont("Helvetica", 8)
    instructions = [
        "• Bank mein bill ki due date se pehle payment karen",
        "• EasyPaisa / JazzCash se bhi payment mumkin hai",
        "• Late payment par surcharge lagay ga",
        "• Queries ke liye helpline 1199 par call karen",
    ]
    y = height - 395
    for inst in instructions:
        p.drawString(40, y, inst)
        y -= 13

    # Footer
    p.setFillColorRGB(0.0, 0.4, 0.2)
    p.rect(0, 0, width, 40, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica", 8)
    p.drawString(40, 25, "Gas Bill Management System | Computer Generated Bill")
    p.drawString(40, 12, f"Print Date: {bill.created_at.strftime('%d-%m-%Y')}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')