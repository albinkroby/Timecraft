from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse,HttpResponse
from django.contrib.auth import login, get_user_model,authenticate,logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db import transaction
from .models import Address,UserProfile, Cart, CartItem, Order, OrderItem
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
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

User = get_user_model()
# Create your views here.

@never_cache
def index(request):
    basewatch = BaseWatch.objects.filter(is_active=True)
    featured_watch = BaseWatch.objects.filter(is_featured=True, is_active=True).first()
    if not featured_watch:
        featured_watch = basewatch.first()
    return render(request, 'index.html', {'basewatch': basewatch, 'featured_watch': featured_watch})

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

@require_POST
@login_required
@never_cache
def update_cart(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')
        
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        if action == 'increase':
            item.quantity += 1
        elif action == 'decrease' and item.quantity > 1:
            item.quantity -= 1
        item.save()
        cart, created = Cart.objects.get_or_create(user=request.user)
        items = cart.items.all()
        total = sum(item.watch.base_price * item.quantity for item in items)
        # discount = sum((item.watch.original_price - item.watch.base_price) * item.quantity for item in items)
        # final_total = total - discount
        final_total = total

        return JsonResponse({'message': 'Cart updated successfully', 'new_quantity': item.quantity ,'total' : total ,'final_total' : final_total}, status=200)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@never_cache
def search_results(request):
    query = request.GET.get('search', '')
    brands = request.GET.getlist('brand')
    categories = request.GET.getlist('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    colors = request.GET.getlist('color')
    strap_materials = request.GET.getlist('strap_material')
    movement_types = request.GET.getlist('function_display')
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
        'movement_types': BaseWatch.get_unique_values('function_display'),
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

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
@never_cache
def order_review(request):
    addresses = Address.objects.filter(user=request.user)
    primary_address = addresses.filter(is_primary=True).first()
    
    product_id = request.GET.get('product_id')
    if product_id:
        # Single product checkout
        product = get_object_or_404(BaseWatch, id=product_id)
        items = [{'watch': product, 'quantity': 1}]
        total = product.base_price
        single_product = product
    else:
        # Cart checkout
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or cart.items.count() == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect('mainapp:cart')
        items = cart.items.all()
        total = sum(item.watch.base_price * item.quantity for item in items)
        single_product = None

    context = {
        'items': items,
        'total': total,
        'addresses': addresses,
        'primary_address': primary_address,
        'stripe_publishable_key': settings.STRIPE_PUBLIC_KEY,
        'single_product': single_product,
    }
    return render(request, 'order_review.html', context)

@csrf_exempt
@require_POST
@login_required
def create_checkout_session(request):
    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        product_id = data.get('product_id')

        if not address_id:
            return JsonResponse({'error': 'Please select a delivery address'}, status=400)

        address = get_object_or_404(Address, id=address_id, user=request.user)

        if product_id:
            # Single product checkout
            product = get_object_or_404(BaseWatch, id=product_id)
            line_items = [{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(product.base_price * 100),
                    'product_data': {
                        'name': product.model_name,
                    },
                },
                'quantity': 1,
            }]
            total_amount = product.base_price
        else:
            # Cart checkout
            cart = Cart.objects.filter(user=request.user).first()
            if not cart or cart.items.count() == 0:
                return JsonResponse({'error': 'Your cart is empty'}, status=400)
            
            line_items = [{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(item.watch.base_price * 100),
                    'product_data': {
                        'name': item.watch.model_name,
                    },
                },
                'quantity': item.quantity,
            } for item in cart.items.all()]
            total_amount = sum(item.watch.base_price * item.quantity for item in cart.items.all())

        # Create or update Stripe Customer with shipping address
        # Check if the customer already exists in Stripe
        existing_customers = stripe.Customer.list(email=request.user.email)
        if existing_customers.data:
            stripe_customer = existing_customers.data[0]
            # Update the existing customer's shipping information
            stripe_customer = stripe.Customer.modify(
                stripe_customer.id,
                shipping={
                    'name': request.user.fullname,
                    'address': {
                        'line1': address.flat_house_no,
                        'line2': address.area_street,
                        'city': address.town_city,
                        'state': address.state,
                        'postal_code': address.pincode,
                        'country': 'IN',
                    }
                }
            )
        else:
            # Create a new customer if one doesn't exist
            stripe_customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.fullname,
                shipping={
                    'name': request.user.fullname,
                    'address': {
                        'line1': address.flat_house_no,
                        'line2': address.area_street,
                        'city': address.town_city,
                        'state': address.state,
                        'postal_code': address.pincode,
                        'country': 'IN',
                    }
                }
            )

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer=stripe_customer.id,
            client_reference_id=str(request.user.id),
            shipping_address_collection={
                'allowed_countries': ['IN'],
            },
            shipping_options=[
                {
                    'shipping_rate_data': {
                        'type': 'fixed_amount',
                        'fixed_amount': {'amount': 0, 'currency': 'inr'},
                        'display_name': 'Free shipping',
                        'delivery_estimate': {
                            'minimum': {'unit': 'business_day', 'value': 5},
                            'maximum': {'unit': 'business_day', 'value': 7},
                        }
                    }
                },
            ],
            custom_text={
                'shipping_address': {
                    'message': 'Please confirm your shipping address for delivery within India.',
                },
                'submit': {
                    'message': 'Your order will be delivered within 5-7 business days.',
                },
            },
            metadata={
                'address_id': str(address_id),
                'product_id': str(product_id) if product_id else '',
                'total_amount': str(total_amount),
            },
            success_url=request.build_absolute_uri(reverse('mainapp:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('mainapp:payment_cancel')),
        )
        return JsonResponse({'id': checkout_session.id})
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'An unexpected error occurred.'}, status=400)

@never_cache
@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                existing_order = Order.objects.filter(stripe_session_id=session_id).first()
                if existing_order:
                    return render(request, 'registration/payment_success.html', {'paid': True, 'order': existing_order})
                try:
                    order = create_order(request.user, session)
                
                    cart = Cart.objects.filter(user=request.user).first()
                    if cart:
                        cart.items.all().delete()
                        cart.delete()
                    
                        return render(request, 'registration/payment_success.html', {'paid': True, 'order': order})
                except ValueError as e:
                    return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'There was an issue with the product stock. Please contact support.'})
            else:
                return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'Payment not successful.'})
        except (stripe.error.StripeError, Exception):
            return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'Error processing payment. Please contact support.'})
    return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'Invalid session ID.'})

def create_order(user, session):
    address_id = session.metadata.get('address_id')
    product_id = session.metadata.get('product_id')
    total_amount = Decimal(session.metadata.get('total_amount'))

    address = Address.objects.get(id=address_id)

    with transaction.atomic():
        # Check if an order with this session ID already exists
        existing_order = Order.objects.filter(stripe_session_id=session.id).first()
        if existing_order:
            return existing_order

        order = Order.objects.create(
            user=user,
            address=address,
            total_amount=total_amount,
            stripe_session_id=session.id
        )

        if product_id:
            # Single product order
            product = BaseWatch.objects.get(id=product_id)
            OrderItem.objects.create(
                order=order,
                watch=product,
                quantity=1,
                price=product.base_price
            )
            product.update_stock_after_order(1)
        else:
            # Cart order
            line_items = stripe.checkout.Session.list_line_items(session.id, limit=100)
            for item in line_items.data:
                product = BaseWatch.objects.get(model_name=item.description)
                OrderItem.objects.create(
                    order=order,
                    watch=product,
                    quantity=item.quantity,
                    price=item.price.unit_amount / 100  # Convert from cents to dollars
                )
                product.update_stock_after_order(item.quantity)

    return order


@never_cache
@login_required
def payment_cancel(request):
    return render(request, 'registration/payment_cancel.html')