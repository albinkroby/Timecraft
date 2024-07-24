# userapp/forms.py
from django import forms
from django.contrib.auth.forms import PasswordResetForm,SetPasswordForm
from django.contrib.auth import get_user_model
from mainapp.models import Profile

class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        active_users = get_user_model()._default_manager.filter(email__iexact=email, is_active=True)
        return (user for user in active_users)

class CustomSetPasswordForm(SetPasswordForm):
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        
        # Additional validation can be added here if needed
        
        return password2


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['flat_house_no', 'area_street', 'landmark', 'pincode', 'town_city', 'state', 'country']
        widgets = {
            'flat_house_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat/House No:/Building/Company/Apartment'}),
            'area_street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area/Street/Sector/Village'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Landmark'}),
            'pincode': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'town_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Town/City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
        }

class NewAddressForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['flat_house_no', 'area_street', 'landmark', 'pincode', 'town_city', 'state', 'country']
        widgets = {
            'flat_house_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat/House No:/Building/Company/Apartment'}),
            'area_street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area/Street/Sector/Village'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Landmark'}),
            'pincode': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'town_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Town/City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
        }
