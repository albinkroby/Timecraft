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

def find_similar_watches(search_features, image_features, similarity_threshold=0.5):
    similar_watches = []
    for watch, watch_features in image_features:
        similarity = compute_similarity(search_features, watch_features)
        print(f"Similarity: {similarity}")
        
        if similarity > similarity_threshold:
            similar_watches.append((watch, similarity))
    
    return sorted(similar_watches, key=lambda x: x[1], reverse=True)
