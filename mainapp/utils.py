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
    Verify an Indian pincode using the free India Post API
    Returns the pincode data if valid, None if invalid
    
    Uses caching to avoid repeated API calls for the same pincode
    """    # Check if we have this pincode in cache
    cache_key = f"pincode_data_{pincode}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Validate pincode format first
    if not (isinstance(pincode, str) and len(pincode) == 6 and pincode.isdigit()):
        print(f"Invalid pincode format: {pincode}")
        return None

    # Use India Post API (free, no authentication needed)
    url = f"https://api.postalpincode.in/pincode/{pincode}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and data[0]['Status'] == 'Success' and data[0]['PostOffice']:
                postoffice = data[0]['PostOffice'][0]  # Get first post office data
                
                # Format the data to match our expected structure
                result = {
                    'pin': str(pincode),
                    'district': postoffice['District'],
                    'state': postoffice['State'],
                    'office': postoffice['Name'],
                    'region': postoffice.get('Region', ''),
                    'circle': postoffice.get('Circle', ''),
                    'division': postoffice.get('Division', ''),
                    'branch_type': postoffice.get('BranchType', ''),
                    'delivery_status': postoffice.get('DeliveryStatus', '')
                }
                
                # Cache the result for 30 days
                cache.set(cache_key, result, 60 * 60 * 24 * 30)
                return result            
            else:
                error_msg = data[0]['Message'] if data else "No data received"
                print(f"Invalid pincode or no data found: {pincode}. Error: {error_msg}")
                return None
                
        else:
            print(f"API request failed with status code: {response.status_code}")
            # Fall back to mock data for API errors
            return _get_mock_pincode_data(pincode, cache_key)
            
    except Exception as e:
        print(f"Error verifying pincode {pincode}: {e}")
        # Fall back to mock data if request fails
        return _get_mock_pincode_data(pincode, cache_key)
    
    return None

def _get_mock_pincode_data(pincode, cache_key=None):
    """Helper function to get mock pincode data"""
    mock_data = {
        'pin': str(pincode),
        'district': 'Test District',
        'state': 'Test State',
        'office': 'Test Post Office',
        'taluk': 'Test Taluk'
    }
    if cache_key:
        # Cache the mock result for 30 days
        cache.set(cache_key, mock_data, 60 * 60 * 24 * 30)
    return mock_data

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
    
    # Split the query into words to handle multi-word queries
    query_words = query.split()
    
    # Check for common watch type words like "watch", "watches", "timepiece"
    watch_terms = ["watch", "watches", "timepiece", "timepieces", "wristwatch", "wristwatches"]
    content_words = [word for word in query_words if word not in watch_terms and len(word) > 2]
    
    # Create a cleaned query without watch terms for better matching
    cleaned_query = " ".join(content_words) if content_words else query
    
    # Get all watch models, brands and relevant text fields to search
    watch_models = BaseWatch.objects.filter(is_active=True).values_list('model_name', flat=True)
    brand_names = Brand.objects.values_list('brand_name', flat=True)
    colors = BaseWatch.objects.values_list('color', flat=True).distinct()
    strap_colors = BaseWatch.objects.values_list('details__strap_color', flat=True).distinct()
    function_displays = BaseWatch.objects.values_list('function_display', flat=True).distinct()
    
    # Combine all searchable strings and remove None/empty values
    all_searchable = []
    for items in [watch_models, brand_names, colors, strap_colors, function_displays]:
        all_searchable.extend([item for item in items if item])
    
    # Find fuzzy matches
    fuzzy_matches = []
    
    # First, check for matches with the whole query
    for item in all_searchable:
        item_lower = item.lower()
        # Check if the full query is a direct substring of the item (case-insensitive)
        if query in item_lower:
            # Direct full query matches get highest similarity score
            fuzzy_matches.append((item, 1.0))
        else:
            # Use sequence matcher for fuzzy matching with full query
            similarity = difflib.SequenceMatcher(None, query, item_lower).ratio()
            if similarity >= threshold:
                fuzzy_matches.append((item, similarity))
    
    # For queries like "red watches", also check with just the content words (e.g., "red")
    if cleaned_query != query:
        for item in all_searchable:
            item_lower = item.lower()
            if cleaned_query in item_lower:
                # Direct content word matches get high score
                fuzzy_matches.append((item, 0.95))
            else:
                # Use sequence matcher for fuzzy matching with cleaned query
                similarity = difflib.SequenceMatcher(None, cleaned_query, item_lower).ratio()
                if similarity >= threshold:
                    fuzzy_matches.append((item, similarity * 0.9))  # Slightly lower than full query matches
    
    # Then check for individual word matches for multi-word queries
    if len(query_words) > 1:
        # Skip common filler words
        skip_words = ['watch', 'watches', 'the', 'and', 'for', 'with', 'a', 'an', 'in', 'on', 'at']
        for word in query_words:
            if len(word) <= 2 or word in skip_words:
                continue
                
            for item in all_searchable:
                item_lower = item.lower()
                # Check if this word is a direct substring
                if word in item_lower:
                    # Word match gets good but not perfect score
                    # Adjust score based on word length compared to full query
                    word_importance = len(word) / len(query)
                    fuzzy_matches.append((item, 0.7 * word_importance))
      # Sort by similarity score in descending order
    fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
    
    # Return only unique matches (by lowercase comparison) to avoid duplicates
    seen = set()
    unique_matches = []
    for item, score in fuzzy_matches:
        item_lower = item.lower()
        if item_lower not in seen:
            unique_matches.append((item, score))
            seen.add(item_lower)
    
    # Return only the item names, not the scores
    return [item for item, score in unique_matches[:5]]

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
    colors = BaseWatch.objects.values_list('color', flat=True).distinct()
    strap_colors = BaseWatch.objects.values_list('details__strap_color', flat=True).distinct()
    function_displays = BaseWatch.objects.values_list('function_display', flat=True).distinct()
    
    # Combine all searchable words and normalize to lowercase
    all_searchable = []
    for items in [watch_models, brand_names, colors, strap_colors, function_displays]:
        for item in items:
            if item:  # Check for None/empty values
                # Split multi-word items and add both the full item and individual words
                all_searchable.append(item.lower())  # Add the complete term
                all_searchable.extend([word.lower() for word in item.split() if len(word) > 2])  # Add individual words
    
    # Remove duplicates while preserving order of more important terms
    all_searchable_unique = []
    seen = set()
    for item in all_searchable:
        if item not in seen and len(item) > 1:  # Skip very short words and duplicates
            all_searchable_unique.append(item)
            seen.add(item)
    
    # Find closest matches for each word
    suggestions = []
    for word in words:
        if len(word) <= 2:  # Skip very short words
            continue
        
        # Try to find exact matches first (case insensitive)
        exact_matches = [s for s in all_searchable_unique if word == s]
        if exact_matches:
            continue  # Skip words that have exact matches
            
        # Then find close matches for potential misspellings
        matches = difflib.get_close_matches(word, all_searchable_unique, n=3, cutoff=0.6)
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
    # Normalize the search term to lowercase for consistent searching
    normalized_term = search_term.lower().strip()
    
    # Split the search term into individual words for better matching
    search_words = normalized_term.split()
    
    # Check for common watch type words like "watch", "watches", "timepiece"
    watch_terms = ["watch", "watches", "timepiece", "timepieces", "wristwatch", "wristwatches"]
    content_words = [word for word in search_words if word not in watch_terms]
    
    # Create a cleaned term without watch terms for better color matching
    cleaned_term = " ".join(content_words) if content_words else normalized_term
    
    # Prioritize different search strategies based on content
    # 1. When searching for a color term like "red watches", prioritize color search
    # 2. When searching for specific terms, prioritize exact matches over fuzzy matches
    colors = extract_color_terms(normalized_term)
    
    # Get fuzzy matches for both the full term and the cleaned term
    fuzzy_matches_full = get_fuzzy_matches(normalized_term)
    fuzzy_matches_cleaned = get_fuzzy_matches(cleaned_term) if cleaned_term != normalized_term else []
    
    # Combine unique fuzzy matches
    fuzzy_matches = list(set(fuzzy_matches_full + fuzzy_matches_cleaned))
    
    # Start with an empty query - we'll build it up based on the search content
    query = Q()
    
    # When searching for a specific term + "watches" (e.g. "red watches"), prioritize the specific term
    if content_words and any(term in normalized_term for term in watch_terms):
        # First add the content words with higher priority
        for word in content_words:
            if len(word) > 2:  # Skip very short words
                query |= Q(model_name__icontains=word) | \
                        Q(brand__brand_name__icontains=word) | \
                        Q(description__icontains=word) | \
                        Q(color__icontains=word) | \
                        Q(function_display__icontains=word) | \
                        Q(details__strap_color__icontains=word)
        
        # Then add the cleaned term for good measure
        if len(content_words) > 0:
            cleaned_term = " ".join(content_words)
            query |= Q(model_name__icontains=cleaned_term) | \
                    Q(brand__brand_name__icontains=cleaned_term) | \
                    Q(description__icontains=cleaned_term)
    
    # If we have color terms and watch terms, prioritize color matching
    elif colors and any(term in normalized_term for term in watch_terms):
        for color in colors:
            query |= Q(color__iexact=color) | Q(details__strap_color__iexact=color)
    
    # Otherwise, search with the full term and individual words
    else:
        # Add the full term search
        query |= Q(model_name__icontains=normalized_term) | \
                Q(brand__brand_name__icontains=normalized_term) | \
                Q(description__icontains=normalized_term) | \
                Q(function_display__icontains=normalized_term)
        
        # Add individual word matches to improve search relevance
        for word in search_words:
            if len(word) > 2:  # Skip very short words
                query |= Q(model_name__icontains=word) | \
                        Q(brand__brand_name__icontains=word) | \
                        Q(description__icontains=word) | \
                        Q(function_display__icontains=word)    # Enhanced color matching
    color_query = Q()
    
    # Check for colors in both the full term and the cleaned term (without watch terms)
    colors_full = extract_color_terms(normalized_term)
    colors_cleaned = extract_color_terms(cleaned_term) if cleaned_term != normalized_term else []
    all_colors = list(set(colors_full + colors_cleaned))
    
    if all_colors:
        # We found specific colors - use exact matching for better results
        for color in all_colors:
            color_query |= Q(color__iexact=color) | Q(details__strap_color__iexact=color)
            # Also add contains to catch partial matches like "dark red", "light blue"
            color_query |= Q(color__icontains=color) | Q(details__strap_color__icontains=color)
    else:
        # No specific colors found, try with content words
        for word in content_words:
            if len(word) > 2:
                color_query |= Q(color__icontains=word) | Q(details__strap_color__icontains=word)
    
    # Always add color queries to improve matching
    query = query | color_query
      # Add fuzzy match terms to query with more weight given to important matches
    for match in fuzzy_matches:
        # Check if this is a color or function display term for more focused matching
        is_color = match.lower() in [color.lower() for color in extract_color_terms(match)]
        is_function = match.lower() in [func.lower() for func in extract_function_display_terms(match)]
        
        # Basic search in all fields
        match_query = Q(model_name__icontains=match) | \
                     Q(brand__brand_name__icontains=match) | \
                     Q(description__icontains=match)
                     
        # Add specialized field searches based on the type of term
        if is_color:
            match_query |= Q(color__iexact=match) | Q(details__strap_color__iexact=match) | \
                          Q(color__icontains=match) | Q(details__strap_color__icontains=match)
        elif is_function:
            match_query |= Q(function_display__iexact=match) | Q(function_display__icontains=match)
        else:
            # For general terms, search in all fields
            match_query |= Q(color__icontains=match) | \
                          Q(details__strap_color__icontains=match) | \
                          Q(function_display__icontains=match)
        
        # Add this match's query to the main query
        query |= match_query
    
    return query

def extract_color_terms(search_term):
    """Extract color terms from search query"""
    # Common watch colors to detect in search
    common_colors = [
        'red', 'blue', 'green', 'black', 'white', 'gold', 'silver', 'brown', 
        'orange', 'yellow', 'purple', 'pink', 'grey', 'gray', 'navy', 'rose gold',
        'bronze', 'beige', 'tan', 'copper', 'maroon', 'turquoise', 'teal',
        # Add more nuanced color descriptions that might appear in watches
        'dark blue', 'light blue', 'dark green', 'light green', 'dark brown',
        'light brown', 'dark gray', 'light gray', 'dark grey', 'light grey',
        'midnight black', 'champagne gold', 'dark silver', 'platinum'
    ]
    
    # Skip words - don't consider these as part of color terms
    skip_words = ['watch', 'watches', 'timepiece', 'timepieces', 'wristwatch', 'wristwatches', 
                  'the', 'a', 'an', 'and', 'or', 'but', 'for', 'with', 'by', 'of', 'in', 'on', 'at']
    
    # Normalize the search term
    search_lower = search_term.lower().strip()
    
    # First check for colors in the original term - important for compound terms like "red watches"
    original_words = search_lower.split()
    found_colors = []
    
    # Check individual words in original query
    for word in original_words:
        if word in [c.lower() for c in common_colors]:
            # Find the original case version
            for color in common_colors:
                if color.lower() == word:
                    found_colors.append(color)
                    break
    
    # Remove common non-color words for additional processing
    cleaned_search = search_lower
    for word in skip_words:
        cleaned_search = cleaned_search.replace(f" {word} ", " ").replace(f" {word}", "").replace(f"{word} ", "")
    
    cleaned_words = cleaned_search.split()
    
    # If no matches yet, try with the cleaned search
    if not found_colors:
        # Check individual words after cleaning
        for word in cleaned_words:
            if word in [c.lower() for c in common_colors]:
                # Find the original case version
                for color in common_colors:
                    if color.lower() == word:
                        found_colors.append(color)
                        break
    
    # If still no matches, check for exact color matches with word boundaries
    if not found_colors:
        for color in common_colors:
            color_lower = color.lower()
            
            # Check in original search term with word boundaries
            if f" {color_lower} " in f" {search_lower} ":
                found_colors.append(color)
            elif search_lower == color_lower or search_lower.startswith(f"{color_lower} ") or search_lower.endswith(f" {color_lower}"):
                found_colors.append(color)
                
            # Also check in cleaned search term
            if cleaned_search != search_lower:
                if f" {color_lower} " in f" {cleaned_search} ":
                    found_colors.append(color)
                elif cleaned_search == color_lower or cleaned_search.startswith(f"{color_lower} ") or cleaned_search.endswith(f" {color_lower}"):
                    found_colors.append(color)
    
    # Check for compound colors
    # First in original search term
    for i in range(len(original_words) - 1):
        compound_color = f"{original_words[i]} {original_words[i+1]}"
        if compound_color in [c.lower() for c in common_colors]:
            # Find the original case version from common_colors
            for color in common_colors:
                if color.lower() == compound_color:
                    found_colors.append(color)
                    break
    
    # Then in cleaned search term
    if not any(len(color.split()) > 1 for color in found_colors):  # If no compound colors found yet
        for i in range(len(cleaned_words) - 1):
            compound_color = f"{cleaned_words[i]} {cleaned_words[i+1]}"
            if compound_color in [c.lower() for c in common_colors]:
                # Find the original case version from common_colors
                for color in common_colors:
                    if color.lower() == compound_color:
                        found_colors.append(color)
                        break
    
    # Remove duplicates while preserving order
    unique_colors = []
    seen = set()
    for color in found_colors:
        if color.lower() not in seen:
            unique_colors.append(color)
            seen.add(color.lower())
    
    return unique_colors

def extract_function_display_terms(search_term):
    """Extract function display terms from search query"""
    # Common watch function displays
    function_displays = [
        'analog', 'digital', 'smart', 'chronograph', 'automatic', 'quartz',
        'mechanical', 'touch', 'hybrid', 'fitness', 'sport', 'dress', 'casual',
        'dive', 'pilot', 'field', 'military', 'skeleton', 'led', 'lcd', 'tourbillon',
        'perpetual calendar', 'gmt', 'moon phase', 'alarm', 'date', 'chronometer'
    ]
    
    # Skip words - don't consider these as part of function display terms
    skip_words = ['watch', 'watches', 'timepiece', 'timepieces', 'wristwatch', 'wristwatches', 
                 'the', 'a', 'an', 'and', 'or', 'but', 'for', 'with', 'by', 'of', 'in', 'on']
    
    # Normalize the search term
    search_lower = search_term.lower().strip()
    search_words = search_lower.split()
    found_displays = []
    
    # First check original term with word boundaries
    for display in function_displays:
        display_lower = display.lower()
        
        # Check for exact term with word boundaries
        if f" {display_lower} " in f" {search_lower} ":
            found_displays.append(display)
        # Check for term at start or end of search string
        elif search_lower == display_lower or search_lower.startswith(f"{display_lower} ") or search_lower.endswith(f" {display_lower}"):
            found_displays.append(display)
        # Check for common phrases like "digital watch" or "chronograph watch"
        elif f"{display_lower} watch" in search_lower or f"{display_lower} watches" in search_lower:
            found_displays.append(display)
    
    # If no matches, try removing skip words and check again
    if not found_displays:
        # Create a cleaned search term without skip words
        cleaned_search = search_lower
        for word in skip_words:
            cleaned_search = cleaned_search.replace(f" {word} ", " ").replace(f" {word}", "").replace(f"{word} ", "")
        
        if cleaned_search != search_lower:
            # Check the cleaned search term
            for display in function_displays:
                display_lower = display.lower()
                
                # Only do these checks if the cleaned term is different
                if f" {display_lower} " in f" {cleaned_search} ":
                    found_displays.append(display)
                elif cleaned_search == display_lower or cleaned_search.startswith(f"{display_lower} ") or cleaned_search.endswith(f" {display_lower}"):
                    found_displays.append(display)
    
    # Last resort - check individual words
    if not found_displays:
        for word in search_words:
            if word in [d.lower() for d in function_displays] and word not in skip_words:
                for display in function_displays:
                    if display.lower() == word:
                        found_displays.append(display)
                        break
    
    # Remove duplicates while preserving order
    unique_displays = []
    seen = set()
    for display in found_displays:
        if display.lower() not in seen:
            unique_displays.append(display)
            seen.add(display.lower())
    
    return unique_displays
