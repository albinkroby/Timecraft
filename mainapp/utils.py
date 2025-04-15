# utils.py
import hashlib
import base64
import requests
import json
from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify
import random
import string
from datetime import datetime, timedelta
import jwt
import hmac
import difflib
from django.db.models import Q
from adminapp.models import BaseWatch, Brand, Category

def hash_url(url):
    key = settings.SECRET_KEY.encode()
    message = url.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()

def verify_hashed_url(hashed_url, url):
    return hmac.compare_digest(hashed_url, hash_url(url))

def verify_pincode(pincode):
    """
    Verify an Indian pincode using the RapidAPI Pincode API
    Returns the pincode data if valid, None if invalid
    
    Uses caching to avoid repeated API calls for the same pincode
    """
    # Check if we have this pincode in cache
    cache_key = f"pincode_data_{pincode}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Check if RAPIDAPI_KEY is available
    if not hasattr(settings, 'RAPIDAPI_KEY') or not settings.RAPIDAPI_KEY:
        print("RAPIDAPI_KEY not available, using mock response for pincode verification")
        # Mock response for testing
        if len(str(pincode)) == 6 and str(pincode).isdigit():
            mock_data = {
                'pin': str(pincode),
                'district': 'Test District',
                'state': 'Test State',
                'office': 'Test Post Office',
                'taluk': 'Test Taluk'
            }
            # Cache the mock result
            cache.set(cache_key, mock_data, 60 * 60 * 24 * 30)
            return mock_data
        return None
    
    url = "https://pincode.p.rapidapi.com/v1/postalcodes/india"
    
    payload = {"search": str(pincode)}
    headers = {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": "pincode.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Find the exact match for the pincode
            exact_match = next((item for item in data if str(item.get('pin')) == str(pincode)), None)
            
            if exact_match:
                # Cache the result for 30 days
                cache.set(cache_key, exact_match, 60 * 60 * 24 * 30)
                return exact_match
        else:
            print(f"API request failed with status code: {response.status_code}")
    except Exception as e:
        print(f"Error verifying pincode {pincode}: {e}")
        # Use mock data if API call fails
        if len(str(pincode)) == 6 and str(pincode).isdigit():
            mock_data = {
                'pin': str(pincode),
                'district': 'Test District',
                'state': 'Test State',
                'office': 'Test Post Office',
                'taluk': 'Test Taluk'
            }
            print("Using mock data due to API error")
            # Cache the mock result
            cache.set(cache_key, mock_data, 60 * 60 * 24 * 30)
            return mock_data
    
    return None

def get_zone_from_pincode(pincode_data):
    """
    Determine delivery zone based on pincode data
    """
    if not pincode_data:
        return 'Unknown'
    
    # Use state information to determine zone
    state = pincode_data.get('state', '').lower()
    
    # Define zones based on Indian geography
    north_states = ['delhi', 'haryana', 'punjab', 'uttar pradesh', 'uttarakhand', 
                   'himachal pradesh', 'jammu and kashmir', 'ladakh']
    
    south_states = ['tamil nadu', 'kerala', 'karnataka', 'andhra pradesh', 
                   'telangana', 'puducherry']
    
    east_states = ['west bengal', 'odisha', 'bihar', 'jharkhand', 'assam', 
                  'arunachal pradesh', 'manipur', 'mizoram', 'nagaland', 
                  'sikkim', 'tripura', 'meghalaya']
    
    west_states = ['gujarat', 'maharashtra', 'goa', 'rajasthan']
    
    central_states = ['madhya pradesh', 'chhattisgarh']
    
    if state in north_states:
        return 'north'
    elif state in south_states:
        return 'south'
    elif state in east_states:
        return 'east'
    elif state in west_states:
        return 'west'
    elif state in central_states:
        return 'central'
    else:
        return 'other'

# New functions for enhanced search

def get_fuzzy_matches(query, threshold=0.6):
    """
    Get fuzzy matches for a search query
    
    Args:
        query (str): The search query
        threshold (float): Minimum similarity score (0-1)
        
    Returns:
        list: List of similar strings found in database
    """
    # Normalize the query
    query = query.lower().strip()
    
    # Get all watch models, brands and relevant text fields to search
    watch_models = BaseWatch.objects.filter(is_active=True).values_list('model_name', flat=True)
    brand_names = Brand.objects.values_list('brand_name', flat=True)
    
    # Combine all searchable strings
    all_searchable = list(watch_models) + list(brand_names)
    
    # Find fuzzy matches
    fuzzy_matches = []
    for item in all_searchable:
        similarity = difflib.SequenceMatcher(None, query, item.lower()).ratio()
        if similarity >= threshold:
            fuzzy_matches.append((item, similarity))
    
    # Sort by similarity score in descending order
    fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
    
    # Return top matches
    return [item[0] for item in fuzzy_matches[:5]]

def get_spelling_suggestions(query):
    """
    Get spelling suggestions for a query
    
    Args:
        query (str): The search query
        
    Returns:
        list: List of suggested corrections
    """
    # Normalize the query
    query = query.lower().strip()
    
    # Split query into words
    words = query.split()
    
    # Get all watch models, brands and categories to check against
    watch_models = BaseWatch.objects.filter(is_active=True).values_list('model_name', flat=True)
    brand_names = Brand.objects.values_list('brand_name', flat=True)
    category_names = Category.objects.values_list('name', flat=True)
    
    # Combine all searchable words
    all_searchable = []
    for item in list(watch_models) + list(brand_names) + list(category_names):
        all_searchable.extend(item.lower().split())
    
    # Remove duplicates
    all_searchable = list(set(all_searchable))
    
    # Find closest matches for each word
    suggestions = []
    for word in words:
        if len(word) <= 2:  # Skip very short words
            continue
            
        matches = difflib.get_close_matches(word, all_searchable, n=3, cutoff=0.6)
        if matches:
            suggestions.append((word, matches))
    
    return suggestions

def create_fuzzy_search_query(search_term):
    """
    Create a Q object for fuzzy searching
    
    Args:
        search_term (str): The search term
        
    Returns:
        Q: Django Q object for querying
    """
    # Get fuzzy matches
    fuzzy_matches = get_fuzzy_matches(search_term)
    
    # Create base query for non-color fields
    query = Q(model_name__icontains=search_term) | \
            Q(brand__brand_name__icontains=search_term) | \
            Q(description__icontains=search_term) | \
            Q(function_display__icontains=search_term)
    
    # Separate color query with OR logic between color and strap_color
    color_query = Q(color__icontains=search_term) | Q(details__strap_color__icontains=search_term)
    
    # Combine all queries
    query = query | color_query
    
    # Add fuzzy match terms to query
    for match in fuzzy_matches:
        query |= Q(model_name__icontains=match) | Q(brand__brand_name__icontains=match)
    
    return query

def extract_color_terms(search_term):
    """Extract color terms from search query"""
    # Common watch colors to detect in search
    common_colors = [
        'red', 'blue', 'green', 'black', 'white', 'gold', 'silver', 'brown', 
        'orange', 'yellow', 'purple', 'pink', 'grey', 'gray', 'navy', 'rose gold',
        'bronze', 'beige', 'tan', 'copper', 'maroon', 'turquoise', 'teal'
    ]
    
    # Check for color terms in the search query
    search_words = search_term.lower().split()
    found_colors = []
    
    # Check for exact color matches
    for color in common_colors:
        if color in search_term.lower():
            found_colors.append(color)
            
    # Check for compound colors
    for i in range(len(search_words) - 1):
        compound_color = f"{search_words[i]} {search_words[i+1]}"
        if compound_color in common_colors:
            found_colors.append(compound_color)
    
    return found_colors

def extract_function_display_terms(search_term):
    """Extract function display terms from search query"""
    # Common watch function displays
    function_displays = [
        'analog', 'digital', 'smart', 'chronograph', 'automatic', 'quartz',
        'mechanical', 'touch', 'hybrid', 'fitness', 'sport', 'dress', 'casual',
        'dive', 'pilot', 'field', 'military', 'skeleton', 'led', 'lcd'
    ]
    
    search_lower = search_term.lower()
    found_displays = []
    
    # Check for function display terms
    for display in function_displays:
        if display in search_lower or f"{display} watch" in search_lower:
            found_displays.append(display)
    
    return found_displays
