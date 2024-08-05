# utils.py
import hashlib
import base64

def hash_url(url):
    hashed = hashlib.sha256(url.encode()).digest()
    encoded = base64.urlsafe_b64encode(hashed).decode()
    return encoded

def verify_hashed_url(hashed_url, original_url):
    print(f"Hashed URL: {hashed_url}")
    print(f"Original URL: {original_url}")
    return hash_url(original_url) == hashed_url
