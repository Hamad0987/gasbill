from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile, Bill, MONTH_CHOICES  # Added MONTH_CHOICES import

class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'First Name'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Last Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Email Address'}))
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Phone Number'}))
    meter_no = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Meter Number'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class':'form-control','rows':3,'placeholder':'Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Confirm Password'}))
    profile_pic = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class':'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Passwords match nahi karte!")
        if User.objects.filter(username=cleaned_data.get('email')).exists():
            raise forms.ValidationError("Ye email already registered hai!")
        return cleaned_data

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['customer', 'month', 'year', 'previous_reading', 'current_reading', 'amount', 'due_date', 'is_paid', 'bill_image']
        widgets = {
            'customer': forms.Select(attrs={'class':'form-select'}),
            'month': forms.Select(attrs={'class':'form-select'}),
            'year': forms.NumberInput(attrs={'class':'form-control'}),
            'previous_reading': forms.NumberInput(attrs={'class':'form-control', 'step':'0.01'}),
            'current_reading': forms.NumberInput(attrs={'class':'form-control', 'step':'0.01'}),
            'amount': forms.NumberInput(attrs={'class':'form-control'}),
            'due_date': forms.DateInput(attrs={'class':'form-control', 'type':'date'}),
            'is_paid': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'bill_image': forms.FileInput(attrs={'class':'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['phone', 'address', 'profile_pic']
        widgets = {
            'phone': forms.TextInput(attrs={'class':'form-control'}),
            'address': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'profile_pic': forms.FileInput(attrs={'class':'form-control'}),
        }

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'6-digit OTP'}))

# Admin add customer form (without OTP, direct creation)
class AdminAddCustomerForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class':'form-control'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class':'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control'}))

    class Meta:
        model = CustomerProfile
        fields = ['meter_no', 'phone', 'address', 'profile_pic']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("User with this email already exists!")
        return email

# Filter form
class BillFilterForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=CustomerProfile.objects.all(), required=False, widget=forms.Select(attrs={'class':'form-select'}))
    month = forms.ChoiceField(choices=[('','All Months')] + MONTH_CHOICES, required=False, widget=forms.Select(attrs={'class':'form-select'}))
    year = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class':'form-control', 'placeholder':'Year'}))
    is_paid = forms.ChoiceField(choices=[('','All'), ('paid','Paid'), ('unpaid','Unpaid')], required=False, widget=forms.Select(attrs={'class':'form-select'}))