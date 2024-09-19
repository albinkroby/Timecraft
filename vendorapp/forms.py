from django import forms
from .models import VendorProfile
from django.contrib.auth import get_user_model
from adminapp.models import BaseWatch, BrandApproval, Brand, WatchDetails, WatchMaterials, WatchImage
from django.core.exceptions import ValidationError
import re
from django.core.validators import RegexValidator

User = get_user_model()

def validate_fullname(value):
    if not re.match(r'^[a-zA-Z\s]+$', value):
        raise ValidationError('Full name must contain only alphabets and spaces.')

def validate_gst_number(value):
    if not re.match(r'^[A-Z0-9]{14}$', value):
        raise ValidationError('GST number must be 14 characters long and contain only uppercase alphabets and numbers.')

def validate_contact_phone(value):
    if not re.match(r'^[6-9]\d{9}$', value):
        raise ValidationError('Contact phone must be a 10-digit number starting with 6, 7, 8, or 9.')

class VendorProfileForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = ['company_name']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Company Name'}),
        }
    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        if VendorProfile.objects.filter(company_name=company_name).exists():
            raise ValidationError('This company name is already in use.')
        return company_name

class VendorRegistrationFormStep1(forms.ModelForm):
    contact_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Contact Email ID'}))
    gst_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter GSTIN'}), validators=[validate_gst_number])
    contact_phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Mobile Number'}), validators=[validate_contact_phone])
    use_same_email = forms.BooleanField(required=False, label="Use same email as registration email")

    class Meta:
        model = User
        fields = ['fullname', 'email']
        widgets = {
            'fullname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Email'}),
        }
        validators = {
            'fullname': [validate_fullname],
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email is already in use.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        use_same_email = cleaned_data.get("use_same_email")
        if use_same_email:
            cleaned_data['contact_email'] = cleaned_data.get('email')
        return cleaned_data

class VendorRegistrationFormStep2(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = []

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class VendorOnboardingForm(forms.ModelForm):
    postal_code = forms.CharField(
        max_length=6, 
        validators=[
            RegexValidator(
                regex='^[0-9]{6}$',
                message='Postal code must be 6 digits',
                code='invalid_postal_code'
            )
        ]
    )
    address_line1 = forms.CharField(max_length=255, required=True)
    address_line2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100, required=True)
    state = forms.CharField(max_length=100, required=True)

    class Meta:
        model = VendorProfile
        fields = ['postal_code', 'address_line1', 'address_line2', 'city', 'state']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

# ... rest of the existing code ...
class BrandSelectionForm(forms.Form):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        empty_label="Select a brand",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class BrandApprovalRequestForm(forms.ModelForm):
    class Meta:
        model = BrandApproval
        fields = ['brand']
        widgets = {
            'brand': forms.Select(attrs={'class': 'form-control'}),
        }

class BaseWatchForm(forms.ModelForm):
    class Meta:
        model = BaseWatch
        fields = '__all__'
        exclude = ['vendor', 'slug', 'total_stock', 'sold_stock', 'is_in_stock', 'image_hash','is_featured']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'collection': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'watch_type': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'model_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'gender': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'available_stock': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'style_code': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'net_quantity': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
            'function_display': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'primary_image': forms.FileInput(attrs={
                'class': 'form-control-file',
                'style': 'display: none;',
                'id': 'primaryImageInput',
                'required': True,
            }),
            'features': forms.CheckboxSelectMultiple(),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].error_messages = {'required': f'{field.replace("_", " ").title()} is required'}
        
        # Add custom error message for primary_image and model_name
        self.fields['primary_image'].error_messages['required'] = 'Primary image is required'
        self.fields['model_name'].error_messages['unique'] = 'This model name is already in use'

    def clean_model_name(self):
        model_name = self.cleaned_data.get('model_name')
        if BaseWatch.objects.filter(model_name=model_name).exists():
            raise forms.ValidationError("This model name is already in use")
        return model_name

class WatchDetailsForm(forms.ModelForm):
    class Meta:
        model = WatchDetails
        fields = ['case_size', 'water_resistance', 'water_resistance_depth', 'series', 'occasion', 'strap_color', 'strap_type', 'dial_color', 'warranty_period']
        widgets = {
            'case_size': forms.TextInput(attrs={'class': 'form-control'}),
            'water_resistance': forms.Select(attrs={'class': 'form-control'}),
            'water_resistance_depth': forms.NumberInput(attrs={'class': 'form-control'}),
            'series': forms.TextInput(attrs={'class': 'form-control'}),
            'occasion': forms.TextInput(attrs={'class': 'form-control'}),
            'strap_color': forms.TextInput(attrs={'class': 'form-control'}),
            'strap_type': forms.TextInput(attrs={'class': 'form-control'}),
            'dial_color': forms.TextInput(attrs={'class': 'form-control'}),
            'warranty_period': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class WatchMaterialsForm(forms.ModelForm):
    class Meta:
        model = WatchMaterials
        fields = ['strap_material', 'glass_material', 'case_material']
        widgets = {field: forms.Select(attrs={'class': 'form-control'}) for field in fields}

class WatchImageForm(forms.ModelForm):
    class Meta:
        model = WatchImage
        fields = ['image']

from django.forms import inlineformset_factory

WatchImageFormSet = inlineformset_factory(
    BaseWatch, WatchImage,
    form=WatchImageForm,
    extra=1,
    can_delete=True
)


class BaseWatchUpdateForm(BaseWatchForm):
    class Meta(BaseWatchForm.Meta):
        exclude = ['vendor', 'slug', 'total_stock', 'sold_stock', 'is_in_stock', 'image_hash', 'is_featured']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_model_name = self.instance.model_name

    def clean_model_name(self):
        model_name = self.cleaned_data.get('model_name')
        if model_name != self.initial_model_name:
            if BaseWatch.objects.filter(model_name=model_name).exists():
                raise forms.ValidationError("This model name is already in use. Please choose a different name.")
        return model_name

class WatchDetailsUpdateForm(WatchDetailsForm):
    class Meta(WatchDetailsForm.Meta):
        pass

class WatchMaterialsUpdateForm(WatchMaterialsForm):
    class Meta(WatchMaterialsForm.Meta):
        pass

WatchImageUpdateFormSet = inlineformset_factory(
    BaseWatch, WatchImage,
    form=WatchImageForm,
    extra=1,
    can_delete=True
)
