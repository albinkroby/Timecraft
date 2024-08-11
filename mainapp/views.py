from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse,HttpResponse
from django.contrib.auth import login, get_user_model,authenticate,logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.db import transaction
from .models import Address,UserProfile, Cart, CartItem
from .forms import SignUpForm
from social_django.models import UserSocialAuth
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from .utils import hash_url, verify_hashed_url
from django.db.models import Q
from adminapp.models import BaseWatch, WatchImage, Brand, Category
from django.contrib import messages
from django.core.paginator import Paginator

User = get_user_model()
# Create your views here.

@never_cache
def index(request):
    basewatch = BaseWatch.objects.all()
    featured_watch = get_object_or_404(BaseWatch, model_name="Chronograph Analog Watch")
    return render(request,'index.html',{'basewatch':basewatch, 'featured_watch': featured_watch})

@never_cache
def signin(request):
    if request.user.is_authenticated:
        return redirect(reverse('mainapp:index'))
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_verified and user.is_active:
                hashed_next = request.POST.get('redirect')
                login(request, user)
                if hashed_next:
                    default_redirect_url = 'vendorapp:register'
                    if verify_hashed_url(hashed_next, default_redirect_url):
                        return redirect(default_redirect_url)
                    else:
                        return redirect('mainapp:index')
                else:
                    if user.role == 'vendor':
                        return redirect('vendorapp:index')
                    elif user.role == 'admin':
                        return redirect('adminapp:index')
                    else:  # user.role == 'user'
                        return redirect('mainapp:index')
            else:
                sendmail(request, user)
                return render(request, 'registration/account_verification_sent.html')
        else:
            return render(request, 'login.html', {'error': 'Invalid email or password'})
    
    return render(request, 'login.html')

@never_cache
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
@never_cache
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
                    is_verified=False  # User is inactive until email verification
                )
                
                # Send email verification
                sendmail(request,user)
                return render(request, 'registration/account_verification_sent.html')
        else:
            form = SignUpForm()
        return render(request, 'signup.html', {'form': form})

@never_cache
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
        
@never_cache
def signout(request):
    logout(request)
    return redirect(reverse('mainapp:login'), {'message': 'You have been logged out'})

@login_required
@never_cache
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

@never_cache
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save()
        return redirect('mainapp:login')
    else:
        return render(request, 'registration/activation_invalid.html')

@never_cache
def check_username(request):
    username = request.GET.get('username', '')
    if request.user.is_authenticated and request.user.username == username:
        return JsonResponse({'available': True})
    is_available = not User.objects.filter(username=username).exists()
    return JsonResponse({'available': is_available})

@never_cache
def check_email(request):
    email = request.GET.get('email', '')
    if request.user.is_authenticated and request.user.email == email:
        return JsonResponse({'available': True})
    is_available = not User.objects.filter(email=email).exists()
    return JsonResponse({'available': is_available})

@never_cache
def product_detail(request, slug):
    watch = get_object_or_404(BaseWatch, slug=slug)
    context = {
        'watch': watch,
        'other_images': watch.additional_images.all(),
    }
    return render(request, 'product_detail.html', context)

@never_cache
@login_required
def add_to_cart(request, watch_id):
    if request.user.is_authenticated:
        if request.method == 'POST':
            try:
                watch = get_object_or_404(BaseWatch, id=watch_id)
                cart, _ = Cart.objects.get_or_create(user=request.user)
                
                # Check if the item already exists in the cart
                cart_items = CartItem.objects.filter(cart=cart, watch=watch)
                
                if cart_items.exists():
                    # If the item exists, update the quantity of the first item
                    cart_item = cart_items.first()
                    cart_item.quantity += 1
                    cart_item.save()
                    
                    # Delete any duplicate items if they exist
                    cart_items.exclude(id=cart_item.id).delete()
                else:
                    # If the item doesn't exist, create a new CartItem
                    cart_item = CartItem.objects.create(cart=cart, watch=watch, quantity=1)
                
                return JsonResponse({'success': True, 'message': f"{watch.model_name} added to your cart."})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    else:
        return redirect('mainapp:login')    

@login_required
@never_cache
def cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()
    total = sum(item.watch.base_price * item.quantity for item in items)
    # discount = sum((item.watch.original_price - item.watch.base_price) * item.quantity for item in items)
    # final_total = total - discount
    final_total = total
    
    context = {
        'items': items,
        'total': total,
        # 'discount': discount,
        'final_total': final_total,
    }
    return render(request, 'cart.html', context)

@login_required
@never_cache
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, f"{item.watch.model_name} removed from your cart.")
    return redirect('mainapp:cart')

@login_required
@never_cache
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > 0:
        item.quantity = quantity
        item.save()
        messages.success(request, f"Quantity updated for {item.watch.model_name}.")
    else:
        item.delete()
        messages.success(request, f"{item.watch.model_name} removed from your cart.")
    return redirect('mainapp:cart')

@never_cache
def search_results(request):
    query = request.GET.get('search', '')
    brands = request.GET.getlist('brand')
    categories = request.GET.getlist('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    colors = request.GET.getlist('color')
    strap_materials = request.GET.getlist('strap_material')
    movement_types = request.GET.getlist('movement_type')
    sort_by = request.GET.get('sort_by', 'relevance')

    watches = BaseWatch.objects.filter(
        Q(model_name__icontains=query) | 
        Q(brand__brand_name__icontains=query) |
        Q(description__icontains=query)
    )

    if brands:
        watches = watches.filter(brand__id__in=brands)
    if categories:
        watches = watches.filter(category__id__in=categories)
    if min_price and max_price:
        watches = watches.filter(base_price__gte=min_price, base_price__lte=max_price)
    if colors:
        watches = watches.filter(color__in=colors)
    if strap_materials:
        watches = watches.filter(strap_material__in=strap_materials)
    if movement_types:
        watches = watches.filter(movement_type__in=movement_types)

    if sort_by == 'price_low_to_high':
        watches = watches.order_by('base_price')
    elif sort_by == 'price_high_to_low':
        watches = watches.order_by('-base_price')
    elif sort_by == 'newest':
        watches = watches.order_by('-id')

    paginator = Paginator(watches, 12)  # Show 12 watches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'watches': page_obj,
        'query': query,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
        'price_range': BaseWatch.get_price_range(),
        'colors': BaseWatch.get_unique_values('color'),
        'strap_materials': BaseWatch.get_unique_values('strap_material'),
        'movement_types': BaseWatch.get_unique_values('movement_type'),
        'selected_brands': brands,
        'selected_categories': categories,
        'selected_min_price': min_price,
        'selected_max_price': max_price,
        'selected_colors': colors,
        'selected_strap_materials': strap_materials,
        'selected_movement_types': movement_types,
        'sort_by': sort_by,
    }
    return render(request, 'search_results.html', context)