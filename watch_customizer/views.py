from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CustomizableWatch, CustomizableWatchPart, CustomWatchSavedDesign
from django.db import IntegrityError
import json
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def customize_watch(request, watch_id=None):
    if watch_id is None:
        customizable_watch = CustomizableWatch.objects.first()
    else:
        customizable_watch = get_object_or_404(CustomizableWatch, id=watch_id)
    
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=customizable_watch).select_related('part__part_name').prefetch_related('options')
    
    saved_design = None
    if 'design_id' in request.GET:
        design_id = request.GET['design_id']
        logger.info(f"Attempting to load design with id: {design_id}")
        try:
            saved_design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
            logger.info(f"Loaded saved design: {saved_design.name}")
            logger.info(f"Design data: {saved_design.design_data}")
        except CustomWatchSavedDesign.DoesNotExist:
            logger.warning(f"Design with id {design_id} not found for user {request.user}")
    
    context = {
        'customizable_watch': customizable_watch,
        'customizable_parts': customizable_parts,
        'saved_design': saved_design,
    }
    return render(request, 'watch_customizer/custom_watch.html', context)

@login_required
@require_POST
def save_design(request, design_id=None):
    try:
        data = json.loads(request.body)

        design_name = data.get('name')
        design_data = data.get('design_data')
        watch_id = data.get('watch_id')

        if not design_name:
            return JsonResponse({'status': 'error', 'message': 'Design name is required'}, status=400)

        if not watch_id:
            return JsonResponse({'status': 'error', 'message': 'Watch ID is missing'}, status=400)

        if design_id:
            # Update existing design
            try:
                saved_design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
                saved_design.name = design_name
                saved_design.design_data = design_data
                saved_design.save()
                return JsonResponse({'status': 'success', 'design_id': saved_design.id, 'message': 'Design updated successfully'})
            except CustomWatchSavedDesign.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Design not found'}, status=404)
        else:
            # Create new design
            try:
                saved_design = CustomWatchSavedDesign.objects.create(
                    user=request.user,
                    customizable_watch_id=watch_id,
                    name=design_name,
                    design_data=design_data
                )
                return JsonResponse({'status': 'success', 'design_id': saved_design.id, 'message': 'Design saved successfully'})
            except IntegrityError:
                return JsonResponse({'status': 'error', 'message': 'Design name already exists'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def saved_designs(request):
    designs = CustomWatchSavedDesign.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'watch_customizer/saved_designs.html', {'designs': designs})

@login_required
@require_POST
def delete_design(request, design_id):
    try:
        design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
        design.delete()
        return JsonResponse({'status': 'success'})
    except CustomWatchSavedDesign.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Design not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)