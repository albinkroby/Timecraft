from django import forms
from django.contrib.auth import get_user_model
from .models import DeliveryProfile, DeliveryHistory, DeliveryRating

User = get_user_model()

class DeliveryProfileForm(forms.ModelForm):
    class Meta:
        model = DeliveryProfile
        fields = ['phone', 'vehicle_type', 'vehicle_number', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'})
        }

class DeliveryUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['fullname', 'email', 'username']
        widgets = {
            'fullname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'})
        }

class OrderAssignmentForm(forms.Form):
    delivery_person = forms.ModelChoiceField(
        queryset=User.objects.filter(role='delivery'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class DeliveryUpdateForm(forms.ModelForm):
    class Meta:
        model = DeliveryHistory
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}, 
                                   choices=[
                                       ('assigned', 'Assigned'),
                                       ('picked_up', 'Picked Up'),
                                       ('in_transit', 'In Transit'),
                                       ('out_for_delivery', 'Out for Delivery'),
                                       ('delivered', 'Delivered'),
                                       ('failed_delivery', 'Failed Delivery'),
                                   ]),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6, 
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center', 
            'placeholder': 'Enter OTP',
            'pattern': '[0-9]*',  # Only allow digits
            'inputmode': 'numeric'  # Show numeric keyboard on mobile
        })
    )

class DeliveryLocationUpdateForm(forms.Form):
    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput()
    )

class DeliveryRatingForm(forms.ModelForm):
    class Meta:
        model = DeliveryRating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        } 