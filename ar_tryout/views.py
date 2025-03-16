import json
import logging
import os
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from adminapp.models import BaseWatch
from django.conf import settings
from django.templatetags.static import static
from django.core.files.storage import default_storage
from django.urls import reverse

logger = logging.getLogger(__name__)

def ar_viewer(request, slug):
    """
    View to render the AR viewer for a specific watch
    """
    try:
        watch = get_object_or_404(BaseWatch, slug=slug, is_active=True)
        logger.info(f"Loading AR viewer for watch: {watch.model_name} (slug: {slug})")
        
        # If it's a customizable watch, we need to get materials
        watch_materials = {}
        try:
            if hasattr(watch, 'customizable_watch') and watch.customizable_watch:
                material_data = watch.customizable_watch.get_material_options()
                for part, materials in material_data.items():
                    watch_materials[part] = {
                        'options': materials,
                        'default': materials[0] if materials else None
                    }
        except Exception as e:
            logger.error(f"Error getting watch materials: {e}")
            # Continue with empty materials
        
        # Build absolute URL for model file
        model_url = None
        if watch.model_file:
            file_name = watch.model_file.name
            logger.info(f"Model file name: {file_name}")
            
            # Try to determine if this is a custom model or static model
            if file_name.startswith('custom_watch_models/'):
                # Custom model - use storage URL
                try:
                    model_url = default_storage.url(file_name)
                except Exception as e:
                    logger.error(f"Error getting custom model URL: {e}")
            else:
                # Static model - use static URL
                try:
                    model_url = static(f'models/{file_name}')
                except Exception as e:
                    logger.error(f"Error getting static model URL: {e}")
        
        # If no model file is available, use fallback model
        if not model_url:
            model_url = static('models/apple_watch_ultra_2.glb')
            logger.info("Using default watch model")
        
        logger.info(f"Final model URL: {model_url}")
        
        # Check if the model file exists
        if model_url.startswith('/static/models/'):
            # For static files, check if the file exists
            model_path = os.path.join(settings.STATIC_ROOT, 'models', os.path.basename(model_url))
            if not os.path.exists(model_path):
                logger.warning(f"Model file not found at {model_path}, using fallback")
                model_url = static('models/apple_watch_ultra_2.glb')
        
        context = {
            'watch': watch,
            'model_url': model_url,
            'materials_json': json.dumps(watch_materials),
            'ar_viewer_url': request.build_absolute_uri(reverse('ar_tryout:ar_viewer', args=[slug])),
        }
        
        return render(request, 'ar_tryout/ar_viewer.html', context)
    except Exception as e:
        logger.error(f"Error in AR viewer: {e}")
        return render(request, 'ar_tryout/ar_error.html', {
            'error_message': 'An error occurred while loading the AR experience.',
            'error_details': str(e) if settings.DEBUG else None
        })

def ar_marker(request):
    """
    View to display the AR marker for printing or display on another device
    """
    return render(request, 'ar_tryout/ar_marker.html')

@login_required
def save_ar_image(request, watch_id):
    """
    API to save AR captured image to user's account
    """
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            # Get the image data from the request
            image_data = request.POST.get('image')
            if not image_data:
                return JsonResponse({'status': 'error', 'message': 'No image data provided'})
            
            # Get the watch
            watch = get_object_or_404(BaseWatch, id=watch_id, is_active=True)
            
            # Save the image to the user's profile or watch history
            # Implementation depends on your user model structure
            # For now, just return success
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Image saved successfully',
                'watch_name': watch.model_name
            })
        except Exception as e:
            logger.error(f"Error saving AR image: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def ar_debug(request):
    """Debug view for AR capabilities"""
    return render(request, 'ar_tryout/ar_debug.html')

def ar_error(request):
    """Error view for AR issues"""
    return render(request, 'ar_tryout/ar_error.html', {
        'error_message': 'There was a problem loading the AR experience.',
        'error_details': None
    })