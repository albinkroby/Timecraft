from django import forms
from .models import VendorProfile
from adminapp.models import BaseWatch, BrandApproval, Brand, WatchDetails, WatchMaterials, SmartWatchFeature, PremiumWatchFeature, WatchImage

class VendorRegistrationForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = ['contact_phone', 'company_name', 'gst_number', 'contact_email']
        widgets = {
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Mobile Number'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Company Name'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter GSTIN'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Email ID'}),
        }

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
            'features': forms.SelectMultiple(attrs={'class': 'form-control'}),
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

class SmartWatchFeatureForm(forms.ModelForm):
    class Meta:
        model = SmartWatchFeature
        fields = ['heart_rate_monitor', 'gps', 'step_counter', 'sleep_tracker']
        widgets = {field: forms.CheckboxInput(attrs={'class': 'form-check-input'}) for field in fields}

class PremiumWatchFeatureForm(forms.ModelForm):
    class Meta:
        model = PremiumWatchFeature
        fields = ['sapphire_glass', 'automatic_movement', 'chronograph']
        widgets = {field: forms.CheckboxInput(attrs={'class': 'form-check-input'}) for field in fields}

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
