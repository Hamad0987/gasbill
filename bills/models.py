from django.db import models
from django.contrib.auth.models import User
import random
from django.utils import timezone
from datetime import timedelta

MONTH_CHOICES = [
    ('January','January'),('February','February'),('March','March'),
    ('April','April'),('May','May'),('June','June'),
    ('July','July'),('August','August'),('September','September'),
    ('October','October'),('November','November'),('December','December'),
]

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    meter_no = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.save()
        return self.otp

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.meter_no})"

class Bill(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='bills')
    bill_no = models.CharField(max_length=20, unique=True, blank=True)
    month = models.CharField(max_length=20, choices=MONTH_CHOICES)
    year = models.IntegerField(default=2025)
    previous_reading = models.FloatField(default=0)
    current_reading = models.FloatField()
    units = models.FloatField(blank=True, null=True)
    amount = models.FloatField()
    due_date = models.DateField(null=True, blank=True)  # Changed: allow null, set in save()
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    bill_image = models.ImageField(upload_to='bill_images/', blank=True, null=True)
    barcode = models.CharField(max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Auto-calculate units
        if self.previous_reading is not None and self.current_reading is not None:
            self.units = self.current_reading - self.previous_reading
        # Auto-generate bill number if not set
        if not self.bill_no:
            self.bill_no = f"GB-{self.year}-{self.customer.id}-{random.randint(1000,9999)}"
        # Set due date 14 days from creation if not set
        if not self.due_date:
            self.due_date = timezone.now().date() + timedelta(days=14)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - {self.month} {self.year}"

    @property
    def reading(self):
        return self.current_reading

    @reading.setter
    def reading(self, value):
        self.current_reading = value