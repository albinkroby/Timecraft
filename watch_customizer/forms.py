from django import forms
from django.core.exceptions import ValidationError
import zipfile
import os
import logging
from .models import CustomizableWatch, WatchPart, WatchPartOption, WatchPartName

logger = logging.getLogger(__name__)

class ModelUploadForm(forms.Form):
    model_file = forms.FileField(
        label='Upload 3D Model',
        required=True,
        widget=forms.ClearableFileInput(attrs={'accept': '.zip,.gltf,.glb'})
    )

    def clean_model_file(self):
        model_file = self.cleaned_data.get('model_file')
        logger.debug(f"Cleaning model_file: {model_file}")
        logger.debug(f"Model file name: {getattr(model_file, 'name', 'No name')}")
        logger.debug(f"Model file size: {getattr(model_file, 'size', 'No size')}")
        
        if not model_file:
            logger.error("No file uploaded")
            raise forms.ValidationError("This field is required.")
        
        if not getattr(model_file, 'name', None):
            logger.error("Uploaded file has no name")
            raise forms.ValidationError("The uploaded file has no name.")
        
        file_extension = os.path.splitext(model_file.name)[1].lower()
        logger.debug(f"File extension: {file_extension}")
        
        if file_extension not in ['.zip', '.gltf', '.glb']:
            logger.error(f"Invalid file extension: {file_extension}")
            raise forms.ValidationError("Please upload a valid ZIP, GLTF, or GLB file.")
        
        if file_extension == '.zip':
            try:
                with zipfile.ZipFile(model_file) as zf:
                    file_list = zf.namelist()
                    logger.debug(f"ZIP contents: {file_list}")
                    if not any(f.endswith(('.gltf', '.glb')) for f in file_list):
                        raise forms.ValidationError("ZIP file does not contain a GLTF or GLB file.")
                logger.debug("ZIP file is valid")
            except zipfile.BadZipFile:
                logger.error("Invalid ZIP file")
                raise forms.ValidationError("The uploaded ZIP file is not valid.")
            except Exception as e:
                logger.error(f"Error testing ZIP file: {str(e)}")
                raise forms.ValidationError(f"Error processing ZIP file: {str(e)}")
        
        return model_file

class CustomizableWatchForm(forms.ModelForm):
    class Meta:
        model = CustomizableWatch
        fields = ['name', 'description', 'base_price', 'thumbnail']

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
        fields = ['name', 'texture', 'thumbnail', 'price', 'stock']

class WatchPartSelectionForm(forms.Form):
    parts = forms.ModelMultipleChoiceField(
        queryset=WatchPart.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )
