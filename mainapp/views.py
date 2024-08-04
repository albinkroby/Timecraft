from django.shortcuts import render, redirect
from django.http import JsonResponse,HttpResponse
from django.contrib.auth import login, get_user_model,authenticate,logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

from django.urls import reverse
from django.db import transaction
from .models import Address,UserProfile
from .forms import SignUpForm
from social_django.models import UserSocialAuth
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator


User = get_user_model()
# Create your views here.

@never_cache
def index(request):
    return render(request,'index.html')


def signin(request):
    if request.user.is_authenticated:
        return redirect(reverse('mainapp:index'))
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                if user.role == 'staff':
                    return redirect('mainapp:index')
                elif user.role == 'admin':
                    return redirect('adminapp:index')
                else:  # user.role == 'user'
                    return redirect('mainapp:index')
            else:
                sendmail(request, user)
                return render(request, 'login.html', {'error': 'Email not verified. Please check your email to verify your account.'})
        else:
            return render(request, 'login.html', {'error': 'Invalid email or password'})
    
    return render(request, 'login.html')

def google_login(request):
    if request.user.is_authenticated:
        return redirect(reverse('mainapp:index')) 
    else:
        user = request.user
        try:
            google_login = user.social_auth.get(provider='google-oauth2')
        except UserSocialAuth.DoesNotExist:
            google_login = None

        if google_login:
            return redirect('/')

    # If not, proceed with the login
    return redirect('social:begin', 'google-oauth2')

@transaction.atomic
def signup(request):
    if request.user.is_authenticated:
        return redirect(reverse('mainapp:index')) 
    else:
        if request.method == 'POST':
            form = SignUpForm(request.POST)
            if form.is_valid():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    fullname=form.cleaned_data['name'],
                    is_active=False  # User is inactive until email verification
                )
                
                # Send email verification
                sendmail(request,user)
        else:
            form = SignUpForm()
        return render(request, 'signup.html', {'form': form})

def sendmail(request,user):
    current_site = get_current_site(request)
    subject = 'Activate Your Account'
    message = render_to_string('registration/account_activation_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    send_mail(subject, message, 'webmaster@yourdomain.com', [user.email])
    
    return redirect(reverse('mainapp:index'))
        
def signout(request):
    logout(request)
    return redirect(reverse('mainapp:login'), {'message': 'You have been logged out'})

@login_required
def login_redirect(request):
    user = request.user
    user_role = request.session.pop('user_role', None)
    # if user_role:
    #     user.role = user_role
    #     user.save()
    if user.role == 'staff':
        return redirect('mainapp:index')
    elif user.role == 'user':
        return redirect('mainapp:index')
    return redirect('login')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('mainapp:login')
    else:
        return render(request, 'registration/activation_invalid.html')

def check_username(request):
    username = request.GET.get('username', '')
    if request.user.is_authenticated and request.user.username == username:
        return JsonResponse({'available': True})
    is_available = not User.objects.filter(username=username).exists()
    return JsonResponse({'available': is_available})

def check_email(request):
    email = request.GET.get('email', '')
    if request.user.is_authenticated and request.user.email == email:
        return JsonResponse({'available': True})
    is_available = not User.objects.filter(email=email).exists()
    return JsonResponse({'available': is_available})