# userapp/forms.py
from django import forms
from django.contrib.auth.forms import PasswordResetForm,SetPasswordForm
from django.contrib.auth import get_user_model
from mainapp.models import Address, UserProfile,User
from django.core.exceptions import ValidationError
import re

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


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['flat_house_no', 'area_street', 'landmark', 'pincode', 'town_city', 'state', 'country','address_type']
        widgets = {
            'flat_house_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat/House No:/Building/Company/Apartment'}),
            'area_street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area/Street/Sector/Village'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Landmark'}),
            'pincode': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'town_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Town/City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'address_type': forms.Select(attrs={'class': 'form-control'}),
        }
    

class UserProfileForm(forms.ModelForm):
    fullname = forms.CharField(
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'fullname'})
    )
    username = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'email'})
    )
    mobilephone = forms.CharField(
        max_length=10, 
        required=True, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'mobilephone'})
    )

    class Meta:
        model = UserProfile
        fields = ['mobilephone']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add readonly attribute to email field for Google login users
        if self.user and self.user.social_auth.filter(provider='google-oauth2').exists():
            self.fields['email'].widget.attrs['readonly'] = True

    def clean_username(self):
        username = self.cleaned_data['username']
        if self.user and self.user.username != username:
            if User.objects.filter(username=username).exists():
                raise ValidationError("This username is already taken.")
        elif len(username) < 4:
            raise ValidationError("Username must be at least 4 characters long.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if self.user and self.user.email != email:
            if User.objects.filter(email=email).exists():
                raise ValidationError("This email is already registered.")
        return email

    def clean_mobilephone(self):
        mobilephone = self.cleaned_data['mobilephone']
        if not re.match(r'^[0-9]{10}$', mobilephone):
            raise ValidationError('Number must be 10 digits.')
        elif not mobilephone[0] in '6789':
            raise ValidationError('Enter a valid mobile number.')
        return mobilephone

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = self.user
        userprofile=UserProfile.objects.get(user=user)
        user.fullname = self.cleaned_data['fullname']
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        userprofile.phone = self.cleaned_data['mobilephone']
        if commit:
            user.save()
            profile.save()
            userprofile.save()
        return profile