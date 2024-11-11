# userapp/decorators.py
from django.shortcuts import redirect
from functools import wraps

def user_type_required(user_type):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role == user_type:
                return view_func(request, *args, **kwargs)
            else:
                if request.user.role == 'admin':
                    return redirect('adminapp:index')
                elif request.user.role == 'vendor':
                    return redirect('vendorapp:index')
                else:
                    return redirect('mainapp:index')
        return _wrapped_view
    return decorator
