from django import forms
from .models import Brand, Category, BaseWatch

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['brand_name', 'brand_image', 'description']
        widgets={
            'brand_name':forms.TextInput(attrs={'class':'form-control'}),
            'brand_image':forms.FileInput(attrs={'class':'form-control'}),
            'description':forms.Textarea(attrs={'class':'form-control'}),
        }
        
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent_category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_category': forms.Select(attrs={'class': 'form-control'}),
        }

class BaseWatchForm(forms.ModelForm):
    class Meta:
        model = BaseWatch
        fields = ['category', 'brand', 'model_name', 'base_price', 'description', 
                  'available_stock', 'color', 'strap_material', 'case_size', 'movement_type', 
                  'water_resistance']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'model_name': forms.TextInput(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'available_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'strap_material': forms.TextInput(attrs={'class': 'form-control'}),
            'case_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'movement_type': forms.TextInput(attrs={'class': 'form-control'}),
            'water_resistance': forms.TextInput(attrs={'class': 'form-control'}),
        }