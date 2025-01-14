from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test


@login_required
@user_passes_test(lambda u: u.is_staff)
def staff_dashboard(request):
    return render(request, 'supportapp/staff_dashboard.html')

