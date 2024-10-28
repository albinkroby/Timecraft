import io
import numpy as np
from PIL import Image
from rembg import remove
from django.core.files.uploadedfile import InMemoryUploadedFile
from scipy.spatial.distance import cosine

# Global variables
global_model = None
global_preprocess_input = None

def get_model():
    global global_model, global_preprocess_input
    if global_model is None:
        # Import TensorFlow and Keras only when needed
        from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
        global_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
        global_preprocess_input = preprocess_input
    return global_model, global_preprocess_input

def remove_background(image_file):
    img = Image.open(image_file)
    img_without_bg = remove(img)
    img_byte_arr = io.BytesIO()
    img_without_bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return InMemoryUploadedFile(
        img_byte_arr,
        'ImageField',
        f"{image_file.name.split('.')[0]}_nobg.png",
        'image/png',
        img_byte_arr.tell(),
        None
    )

def preprocess_image(image_file):
    img = Image.open(image_file)
    img = remove(img)  # Remove background
    img = img.convert('RGB')
    img = img.resize((224, 224))
    x = np.array(img)
    x = np.expand_dims(x, axis=0)
    _, preprocess_input = get_model()  # This will load TensorFlow if not already loaded
    x = preprocess_input(x)
    return x

def extract_features(image_file):
    model, _ = get_model()  # This will load TensorFlow if not already loaded
    x = preprocess_image(image_file)
    features = model.predict(x)
    return features.flatten()

def compute_similarity(feature1, feature2):
    return 1 - cosine(feature1, feature2)  # Cosine similarity

def find_similar_watches(search_features, image_features, similarity_threshold=0.7, min_results=3):
    similar_watches = []
    print(f"Number of watches to compare: {len(image_features)}")
    print(f"Search features shape: {search_features.shape}")
    print(f"Using threshold: {similarity_threshold}")
    
    # Calculate all similarities first
    all_similarities = []
    for watch, watch_features in image_features:
        if watch_features.shape != search_features.shape:
            print(f"Shape mismatch: {watch_features.shape} vs {search_features.shape}")
            continue
            
        similarity = compute_similarity(search_features, watch_features)
        all_similarities.append((watch, similarity))
        print(f"Watch: {watch.model_name}, Similarity: {similarity}")
    
    # Sort by similarity
    all_similarities = sorted(all_similarities, key=lambda x: x[1], reverse=True)
    
    # Either use threshold or take top min_results
    threshold_matches = [x for x in all_similarities if x[1] > similarity_threshold]
    
    if len(threshold_matches) >= min_results:
        similar_watches = threshold_matches[:10]  # Limit to top 10
    else:
        similar_watches = all_similarities[:min_results]  # Take top min_results
    
    print(f"Found {len(similar_watches)} similar watches")
    return similar_watches
