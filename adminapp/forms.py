from django import forms
from .models import Brand, Category, BaseWatch, Feature, Material

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
        fields = '__all__'
        exclude = ['vendor', 'slug', 'average_rating', 'total_reviews','total_stock','sold_stock']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class FeatureForm(forms.ModelForm):
    class Meta:
        model = Feature
        fields = ['name', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }