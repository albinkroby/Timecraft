import numpy as np
from PIL import Image
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.cluster import KMeans
from collections import Counter

def extract_features(image_file):
    model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
    img = Image.open(image_file)
    img = img.convert('RGB')
    img = img.resize((224, 224))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    resnet_features = model.predict(x).flatten()
    
    # Extract color features
    color_features = extract_color_features(img)
    
    # Combine ResNet and color features
    combined_features = np.concatenate((resnet_features, color_features))
    
    return combined_features

import numpy as np
from sklearn.cluster import KMeans

def extract_color_features(img):
    # Resize the image to a standard size
    img = img.resize((224, 224))
    
    # Convert to RGB if it's not already
    img = img.convert('RGB')
    
    # Reshape the image data into a 2D array of pixels
    pixels = np.array(img).reshape(-1, 3)
    
    # Use KMeans to find the most dominant colors
    n_colors = 20
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    
    # Get the RGB values of the cluster centers (dominant colors)
    dominant_colors = kmeans.cluster_centers_
    
    # Calculate the percentage of each dominant color
    labels = kmeans.labels_
    color_percentages = np.bincount(labels) / len(labels)
    
    # Combine colors and their percentages
    features = np.concatenate([dominant_colors.flatten(), color_percentages])
    
    # Ensure we have a fixed-size feature vector of 20 elements
    if len(features) > 20:
        features = features[:20]  # Truncate to 20 features
    elif len(features) < 20:
        features = np.pad(features, (0, 20 - len(features)))  # Pad to 20 features
    
    return features