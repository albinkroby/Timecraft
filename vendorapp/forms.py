from django import forms
from .models import VendorProfile
from adminapp.models import BaseWatch

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
        
class BaseWatchForm(forms.ModelForm):
    class Meta:
        model = BaseWatch
        fields = '__all__'
        exclude = ['vendor', 'slug', 'average_rating', 'total_reviews','total_stock','sold_stock']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})