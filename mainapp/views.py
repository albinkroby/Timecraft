from decimal import Decimal
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse,HttpResponse
from django.contrib.auth import login, get_user_model,authenticate,logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from django.urls import reverse
from django.db import transaction
from django.utils import timezone

from watch_customizer.models import CustomWatchOrder
from .models import Address,UserProfile, Cart, CartItem, Order, OrderItem, WatchNotification, ChatMessage, SupportTicket, SupportMessage, ChatSession
from .forms import SignUpForm
from userapp.forms import AddressForm
from social_django.models import UserSocialAuth
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from .utils import hash_url, verify_hashed_url
from django.db.models import Q,Count, F ,Min, Max
from adminapp.models import BaseWatch, WatchImage, Brand, Category, ImageFeature, Material
from django.contrib import messages
from django.core.paginator import Paginator
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image
import numpy as np
from scipy.spatial.distance import cosine
from rembg import remove
import io, cv2
from django.core.files.uploadedfile import InMemoryUploadedFile
from sklearn.cluster import KMeans
from django.utils.html import strip_tags
from adminapp.models import BaseWatch, ImageFeature
from adminapp.utils import remove_background, extract_features, find_similar_watches
from openai import OpenAI   
from .services.chatbot import ChatbotService
import logging
import uuid

logger = logging.getLogger(__name__)

User = get_user_model()
# Create your views here.

chatbot_service = ChatbotService()

@never_cache
def index(request):
    basewatch = BaseWatch.objects.filter(is_active=True, available_stock__gt=0).order_by('-id')[:15]
    featured_watch = BaseWatch.objects.filter(is_featured=True, is_active=True).first()
    new_arrivals = BaseWatch.objects.filter(
        is_active=True, 
        available_stock__gt=0
    ).order_by('-id')[:5]  # Fetch latest 5 watches
    
    if not featured_watch:
        featured_watch = basewatch.first()
        
    context = {
        'basewatch': basewatch, 
        'featured_watch': featured_watch,
        'new_arrivals': new_arrivals
    }
    return render(request, 'index.html', context)

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
                    elif user.role == 'staff':
                        return redirect('supportapp:staff_dashboard')
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
    if user.role == 'admin':
        return redirect('adminapp:index')
    elif user.role == 'staff':
        return redirect('mainapp:index')
    elif user.role == 'vendor':
        return redirect('vendorapp:index')
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

from adminapp.utils import find_similar_watches
import numpy as np

@never_cache
def product_detail(request, slug):
    watch = get_object_or_404(BaseWatch, slug=slug, is_active=True)
    
    # Get similar watches based on visual features
    try:
        # Get the feature vector for this watch
        from adminapp.models import ImageFeature
        watch_feature = ImageFeature.objects.get(base_watch=watch)
        feature_vector = np.frombuffer(watch_feature.feature_vector, dtype=np.float32)
        
        # Get features for other watches
        all_features = []
        for feature in ImageFeature.objects.exclude(base_watch=watch):
            try:
                other_vector = np.frombuffer(feature.feature_vector, dtype=np.float32)
                # Check that vectors have the same shape
                if other_vector.shape == feature_vector.shape:
                    all_features.append((feature.base_watch, other_vector))
            except Exception as e:
                print(f"Error processing feature for watch {feature.base_watch.id}: {str(e)}")
        
        # Find similar watches with lower threshold to ensure we get results
        similar_watches = find_similar_watches(
            feature_vector, 
            all_features,
            similarity_threshold=0.5,  # Lower threshold to get more matches
            min_results=4
        )
    except (ImageFeature.DoesNotExist, Exception) as e:
        print(f"Error finding similar watches: {str(e)}")
        similar_watches = []
    
    # Rest of your existing view code...
    
    context = {
        'watch': watch,
        'similar_watches': similar_watches,
        # Other context variables...
    }
    return render(request, 'product_detail.html', context)

@never_cache
@login_required
@user_type_required('user')
def add_to_cart(request, watch_id):
    if request.user.is_authenticated:
        if request.method == 'POST':
            try:
                watch = get_object_or_404(BaseWatch, id=watch_id)
                cart, _ = Cart.objects.get_or_create(user=request.user)
                
                # Check if the item already exists in the cart
                cart_item = CartItem.objects.filter(cart=cart, watch=watch).first()
                
                if cart_item:
                    if cart_item.quantity < min(6, watch.available_stock):
                        cart_item.quantity += 1
                        cart_item.save()
                    else:
                        return JsonResponse({'success': False, 'message': 'Maximum quantity reached or insufficient stock'}, status=400)
                else:
                    if watch.available_stock > 0:
                        CartItem.objects.create(cart=cart, watch=watch, quantity=1)
                    else:
                        return JsonResponse({'success': False, 'message': 'This product is out of stock'}, status=400)
                
                return JsonResponse({'success': True, 'message': f"{watch.model_name} added to your cart."})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    else:
        return redirect('mainapp:login')

@login_required
@never_cache
@user_type_required('user')
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
        try:
            item_id = request.POST.get('item_id')
            action = request.POST.get('action')
            
            if not item_id or not action:
                return JsonResponse({'error': 'Missing item_id or action'}, status=400)
            
            item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            watch = item.watch
            
            if action == 'increase':
                if item.quantity < min(6, watch.available_stock):
                    item.quantity += 1
                else:
                    return JsonResponse({'error': 'Maximum quantity reached or insufficient stock'}, status=400)
            elif action == 'decrease':
                if item.quantity > 1:
                    item.quantity -= 1
                else:
                    return JsonResponse({'error': 'Quantity cannot be less than 1'}, status=400)
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
            
            item.save()
            cart = Cart.objects.get(user=request.user)
            items = cart.items.all()
            total = sum(item.watch.base_price * item.quantity for item in items)
            final_total = total

            return JsonResponse({
                'message': 'Cart updated successfully', 
                'new_quantity': item.quantity,
                'total': total,
                'final_total': final_total
            })
        except CartItem.DoesNotExist:
            return JsonResponse({'error': 'Cart item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def get_dominant_color(image, k=4):
    try:
        # Convert InMemoryUploadedFile to PIL Image
        pil_image = Image.open(image)
        
        # Convert PIL Image to numpy array
        img_array = np.array(pil_image)
        
        # Check if the image is grayscale and convert to RGB if necessary
        if len(img_array.shape) == 2:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        elif img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
        # Reshape the array for K-means
        pixels = img_array.reshape((-1, 3))
        
        # Perform K-means clustering
        kmeans = KMeans(n_clusters=k)
        kmeans.fit(pixels)
        
        # Find the most dominant color
        colors = kmeans.cluster_centers_
        labels = kmeans.labels_
        label_counts = np.bincount(labels)
        dominant_color = colors[label_counts.argmax()]
        
        # Convert to hexadecimal color code
        hex_color = '#{:02x}{:02x}{:02x}'.format(int(dominant_color[0]), int(dominant_color[1]), int(dominant_color[2]))
        
        return hex_color
    except Exception as e:
        print(f"Error in get_dominant_color: {str(e)}")
        return "#000000"  # Return a default color in case of error



@never_cache
@require_http_methods(["GET", "POST"])
def search_results(request):
    query = request.GET.get('search', '')
    image_search = request.GET.get('image_search', '')
    similar_watches = []  # Initialize the variable here
    
    brands = request.GET.getlist('brand')
    categories = request.GET.getlist('category')
    min_price = request.GET.get('min_price', 0)
    max_price = request.GET.get('max_price')
    colors = request.GET.getlist('color')
    strap_colors = request.GET.getlist('strap_color')
    function_displays = request.GET.getlist('function_display')
    sort_by = request.GET.get('sort_by', 'relevance')

    watches = BaseWatch.objects.filter(is_active=True).order_by('id')  # Add default ordering

    if query:
        watches = watches.filter(
            Q(model_name__icontains=query) | 
            Q(brand__brand_name__icontains=query) |
            Q(description__icontains=query)
        )

    if brands:
        watches = watches.filter(brand__id__in=brands)
    if categories:
        watches = watches.filter(category__id__in=categories)
    if min_price:
        watches = watches.filter(base_price__gte=min_price)
    if max_price:
        watches = watches.filter(base_price__lte=max_price)
    if colors:
        watches = watches.filter(color__in=colors)
    if strap_colors:
        watches = watches.filter(details__strap_color__in=strap_colors)
    if function_displays:
        watches = watches.filter(function_display__in=function_displays)

    if sort_by == 'price_low_to_high':
        watches = watches.order_by('base_price')
    elif sort_by == 'price_high_to_low':
        watches = watches.order_by('-base_price')
    elif sort_by == 'newest':
        watches = watches.order_by('-id')

    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_image = request.FILES['image']
        uploaded_image_nobg = remove_background(uploaded_image)
        
        temp_image_path = default_storage.save('temp_images/search_image.jpg', uploaded_image_nobg)
        temp_image_path = default_storage.path(temp_image_path)
        
        search_features = extract_features(temp_image_path)
        
        # Get all image features from the database
        image_features = [(feature.base_watch, np.frombuffer(feature.feature_vector, dtype=np.float32)) 
                          for feature in ImageFeature.objects.all()]
        
        # Try different thresholds until we find matches
        thresholds = [0.7, 0.6, 0.5]
        similar_watches = []
        
        for threshold in thresholds:
            similar_watches = find_similar_watches(search_features, image_features, similarity_threshold=threshold)
            if similar_watches:
                print(f"Found matches at threshold {threshold}")
                break
        
        if similar_watches:
            watch_ids = [watch.id for watch, similarity in similar_watches]
            watches = watches.filter(id__in=watch_ids)
            image_search = True
            
            # Debug information
            print("Search features shape:", search_features.shape)
            print("Number of similar watches found:", len(similar_watches))
            print(f"Using threshold: {threshold}")
            for watch, similarity in similar_watches[:5]:  # Print top 5 matches
                print(f"Watch: {watch.model_name}, Similarity: {similarity}")
        else:
            print("No similar watches found at any threshold")
            messages.warning(request, "No similar watches found. Try a different image or search criteria.")
        
        # Clean up the temporary file
        default_storage.delete(temp_image_path)
        
        request.session['image_search'] = True
        request.session['search_features'] = search_features.tolist()
        request.session['similar_watches'] = [(watch.id, float(similarity)) for watch, similarity in similar_watches]
        
    elif image_search:
        saved_similar_watches = request.session.get('similar_watches', [])
        if saved_similar_watches:
            # Try different thresholds for saved watches too
            thresholds = [0.7, 0.6, 0.5]
            similar_watches = []
            
            for threshold in thresholds:
                watch_ids = [watch_id for watch_id, similarity in saved_similar_watches if similarity > threshold]
                if watch_ids:
                    watches = watches.filter(id__in=watch_ids)
                    similar_watches = [(BaseWatch.objects.get(id=watch_id), similarity) 
                                     for watch_id, similarity in saved_similar_watches
                                     if similarity > threshold]
                    print(f"Found saved matches at threshold {threshold}")
                    break

    paginator = Paginator(watches, 12)  # Show 12 watches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'watches': page_obj,
        'query': query,
        'image_search': image_search,
        'similar_watches': similar_watches,  # Now it's always defined
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
        'price_range': BaseWatch.get_price_range(),
        'colors': BaseWatch.get_unique_values('color'),
        'strap_colors': BaseWatch.objects.values_list('details__strap_color', flat=True).distinct(),
        'function_displays': BaseWatch.get_unique_values('function_display'),
        'selected_brands': brands,
        'selected_categories': categories,
        'selected_min_price': min_price,
        'selected_max_price': max_price,
        'selected_colors': colors,
        'selected_strap_colors': strap_colors,
        'selected_function_displays': function_displays,
        'sort_by': sort_by,
    }
    return render(request, 'search_results.html', context)

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
@never_cache
@user_type_required('user')
def order_review(request):
    addresses = Address.objects.filter(user=request.user)
    primary_address = addresses.filter(is_primary=True).first()
    form = AddressForm()
    
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
        'form': form,
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
        custom_watch_order_id = data.get('custom_watch_order_id')

        if not address_id:
            return JsonResponse({'error': 'Please select a delivery address'}, status=400)

        address = get_object_or_404(Address, id=address_id, user=request.user)

        if custom_watch_order_id:
            # Custom watch order checkout
            custom_order = get_object_or_404(CustomWatchOrder, id=custom_watch_order_id, user=request.user)
            line_items = [{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(custom_order.total_price * 100),
                    'product_data': {
                        'name': f"Custom Watch: {custom_order.customizable_watch.name}",
                    },
                },
                'quantity': 1,
            }]
            total_amount = custom_order.total_price
            success_url = request.build_absolute_uri(reverse('watch_customizer:custom_payment_success')) + '?session_id={CHECKOUT_SESSION_ID}'
            cancel_url = request.build_absolute_uri(reverse('watch_customizer:custom_payment_cancel'))
        elif product_id:
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
            success_url = request.build_absolute_uri(reverse('mainapp:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}'
            cancel_url = request.build_absolute_uri(reverse('mainapp:payment_cancel'))
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
            success_url = request.build_absolute_uri(reverse('mainapp:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}'
            cancel_url = request.build_absolute_uri(reverse('mainapp:payment_cancel'))

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
                'custom_watch_order_id': str(custom_watch_order_id) if custom_watch_order_id else '',
                'total_amount': str(total_amount),
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )

        # Update CustomWatchOrder with stripe_session_id
        if custom_watch_order_id:
            custom_order.stripe_session_id = checkout_session.id
            custom_order.save()

        return JsonResponse({'id': checkout_session.id})
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def send_order_confirmation_email(order, request):
    subject = f'Order Confirmation - Order #{order.id}'
    html_message = render_to_string('emails/order_confirmation.html', {
        'order': order,
        'user': order.user,
        'view_order_history_url': request.build_absolute_uri(reverse('userapp:my_orders')),
        'refund_policy_url': '#',
        # 'refund_policy_url': request.build_absolute_uri(reverse('mainapp:refund_policy')),
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = order.user.email

    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)

@never_cache
@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'No session ID provided.'})

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
                
                # Send order confirmation email
                send_order_confirmation_email(order, request)
                
                return render(request, 'registration/payment_success.html', {'paid': True, 'order': order})
            except ValueError as e:
                return render(request, 'registration/payment_success.html', {'paid': False, 'error': str(e)})
        else:
            return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'Payment not successful. Please try again or contact support.'})
    except stripe.error.InvalidRequestError:
        return render(request, 'registration/payment_success.html', {'paid': False, 'error': 'Invalid session ID. Please contact support if this persists.'})
    except stripe.error.StripeError as e:
        return render(request, 'registration/payment_success.html', {'paid': False, 'error': f'An error occurred: {str(e)}. Please contact support.'})
    except Exception as e:
        return render(request, 'registration/payment_success.html', {'paid': False, 'error': f'An unexpected error occurred: {str(e)}. Please contact support.'})

def create_order(user, session):
    address_id = session.metadata.get('address_id')
    product_id = session.metadata.get('product_id')
    custom_watch_order_id = session.metadata.get('custom_watch_order_id')
    total_amount = Decimal(session.metadata.get('total_amount'))

    address = Address.objects.get(id=address_id)

    with transaction.atomic():
        # Check if an order with this session ID already exists
        existing_order = Order.objects.filter(stripe_session_id=session.id).first()
        if existing_order:
            return existing_order

        if custom_watch_order_id:
            # Custom watch order
            custom_order = CustomWatchOrder.objects.get(id=custom_watch_order_id)
            custom_order.status = 'on_the_way'
            custom_order.stripe_session_id = session.id
            custom_order.address = address
            custom_order.save()
            return custom_order
        else:
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

@require_POST
@login_required
def notify_me(request):
    watch_id = request.POST.get('watch_id')
    watch = get_object_or_404(BaseWatch, id=watch_id)
    
    notification, created = WatchNotification.objects.get_or_create(
        user=request.user,
        watch=watch
    )
    
    if created:
        return JsonResponse({'success': True, 'message': 'You will be notified when this product is back in stock.'})
    else:
        return JsonResponse({'success': False, 'message': 'You are already subscribed to notifications for this product.'})

@require_http_methods(["POST"])
def chat_view(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': 'No session ID provided'}, status=400)
            
        try:
            # Get session
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Invalid session'}, status=404)
        
        # Save user message
        ChatMessage.objects.create(
            session=session,
            is_user=True,
            message=user_message
        )
        
        # Get bot response
        try:
            bot_response = chatbot_service.get_response(user_message)
        except Exception as e:
            print(f"Chatbot error: {str(e)}")
            return JsonResponse({
                'error': 'Error generating response',
                'response': "I'm sorry, I encountered an error. Please try again."
            })
        
        # Save bot message
        ChatMessage.objects.create(
            session=session,
            is_user=False,
            message=bot_response if isinstance(bot_response, str) else json.dumps(bot_response)
        )
        
        # Update session last activity
        session.save()  # This will update last_activity due to auto_now=True
        
        return JsonResponse({'response': bot_response})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def check_auth(request):
    return JsonResponse({
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None
    })

@require_http_methods(["POST"])
def create_session(request):
    try:
        data = json.loads(request.body)
        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            guest_name=data.get('guest_name'),
            session_id=str(uuid.uuid4())
        )
        return JsonResponse({'session': {
            'id': session.session_id,
            'guest_name': session.guest_name
        }})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_session(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id)
        # Get page number from query params, default to 1
        page = int(request.GET.get('page', 1))
        messages_per_page = 20  # Number of messages to load at once
        
        # Get total message count
        total_messages = session.messages.count()
        
        # Get paginated messages, ordered by newest first then reversed
        messages = session.messages.order_by('-timestamp')[
            (page-1)*messages_per_page : page*messages_per_page
        ]
        
        # Reverse the messages to show oldest first
        messages = list(reversed(messages))
        
        return JsonResponse({
            'session': {
                'id': session.session_id,
                'guest_name': session.guest_name
            },
            'messages': [{
                'message': msg.message,
                'is_user': msg.is_user,
                'timestamp': msg.timestamp.isoformat()
            } for msg in messages],
            'has_more': total_messages > page * messages_per_page,
            'total_pages': (total_messages + messages_per_page - 1) // messages_per_page
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({'session': None})

@never_cache
def get_recommended_products(request):
    """Generate personalized product recommendations based on browsing history"""
    from mainapp.models import ProductView
    
    user = request.user
    # Track products viewed in session if user is not logged in
    viewed_products = request.session.get('viewed_products', [])
    
    if user.is_authenticated:
        # Get user's view history from database
        user_views = ProductView.objects.filter(user=user).order_by('-timestamp')[:10]
        viewed_product_ids = [view.product.id for view in user_views]
    else:
        viewed_product_ids = viewed_products
    
    if viewed_product_ids:
        # Get viewed products' attributes to find similar ones
        viewed_products = BaseWatch.objects.filter(id__in=viewed_product_ids)
        brands = viewed_products.values_list('brand', flat=True).distinct()
        price_range = (viewed_products.aggregate(Min('base_price'))['base_price__min'],
                      viewed_products.aggregate(Max('base_price'))['base_price__max'])
                      
        # Find similar products
        recommendations = BaseWatch.objects.filter(
            Q(brand__in=brands) |
            Q(base_price__range=price_range)
        ).exclude(id__in=viewed_product_ids).distinct()[:8]
        
        return recommendations
    else:
        # Fall back to popular products
        return BaseWatch.objects.filter(is_active=True).order_by('-view_count')[:8]
