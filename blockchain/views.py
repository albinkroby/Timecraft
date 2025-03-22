from django.shortcuts import render

# Create your views here.

def blockchain_home(request):
    """Home page for the blockchain module"""
    return render(request, 'base.html', {'title': 'Blockchain Module'})
