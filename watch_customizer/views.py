from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def customize_watch(request):
    return render(request, 'watch_customizer/custom_watch.html')