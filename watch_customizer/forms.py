from django import forms
from django.core.exceptions import ValidationError
from .models import CustomizableWatch, WatchPart, WatchPartOption, WatchPartName

class CustomizableWatchForm(forms.ModelForm):
    class Meta:
        model = CustomizableWatch
        fields = ['name', 'description', 'base_price', 'model_file', 'thumbnail']

class WatchPartForm(forms.ModelForm):
    part_name = forms.ModelChoiceField(
        queryset=WatchPartName.objects.all(),
        empty_label="Select a part",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = WatchPart
        fields = ['part_name', 'description', 'model_path']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'model_path': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_part_name(self):
        part_name = self.cleaned_data.get('part_name')
        if not part_name:
            raise ValidationError("This field is required.")
        return part_name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description:
            raise ValidationError("This field is required.")
        return description

    def clean_model_path(self):
        model_path = self.cleaned_data.get('model_path')
        if not model_path:
            raise ValidationError("This field is required.")
        return model_path

class WatchPartOptionForm(forms.ModelForm):
    class Meta:
        model = WatchPartOption
        fields = ['name', 'texture', 'thumbnail', 'price', 'stock', 'roughness', 'metalness']

class WatchPartSelectionForm(forms.Form):
    parts = forms.ModelMultipleChoiceField(
        queryset=WatchPart.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )