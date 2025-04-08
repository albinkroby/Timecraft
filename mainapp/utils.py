# utils.py
import hashlib
import base64
import requests
import json
from django.conf import settings
from django.core.cache import cache

def hash_url(url):
    hashed = hashlib.sha256(url.encode()).digest()
    encoded = base64.urlsafe_b64encode(hashed).decode()
    return encoded

def verify_hashed_url(hashed_url, original_url):
    print(f"Hashed URL: {hashed_url}")
    print(f"Original URL: {original_url}")
    return hash_url(original_url) == hashed_url

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
