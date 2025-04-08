from django import forms
from django.contrib.auth import get_user_model
from .models import DeliveryProfile, DeliveryHistory, DeliveryRating

User = get_user_model()

class DeliveryProfileForm(forms.ModelForm):
    class Meta:
        model = DeliveryProfile
        fields = [
            'phone', 
            'vehicle_type', 
            'vehicle_number', 
            'profile_image',
            'preferred_zones_text',
            'max_distance',
            'max_workload',
            'availability_start',
            'availability_end',
            'weekday_availability_text'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'preferred_zones_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'north,south,east,west'}),
            'max_distance': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
            'max_workload': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'availability_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'availability_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'weekday_availability_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,1,2,3,4,5,6'}),
        }
        labels = {
            'preferred_zones_text': 'Preferred Zones (comma-separated)',
            'weekday_availability_text': 'Available Days (0=Monday, 6=Sunday)',
        }

    # Alternative UI using checkboxes (can be enabled if needed)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['preferred_zones_text'].help_text = "Enter zones separated by commas (north,south,east,west)"
        self.fields['weekday_availability_text'].help_text = "Enter days as numbers separated by commas (0=Monday, 6=Sunday)"
        
        # Set initial values if editing an existing instance
        instance = kwargs.get('instance', None)
        if instance:
            # No need to set initial values as the model will handle the conversion
            pass

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