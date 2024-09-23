import os
import sys
import django
from decimal import Decimal
from django.utils.text import slugify
import random
import string

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Timecrafter.settings")
django.setup()

# Import models
from adminapp.models import (
    BaseWatch, WatchDetails, WatchMaterials, Brand, Category, 
    VendorProfile, WatchType, Collection, Material
)

def generate_model_name():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{letters}-{numbers}"

def create_sample_products():
    # Create or get necessary related objects
    vendor, _ = VendorProfile.objects.get_or_create(company_name="Time Craft")
    category, _ = Category.objects.get_or_create(name="Wristwatch")
    watch_type, _ = WatchType.objects.get_or_create(type_name="Analog")
    collection, _ = Collection.objects.get_or_create(name="Sample Collection")
    
    # Create materials
    leather, _ = Material.objects.get_or_create(name="Leather")
    mineral, _ = Material.objects.get_or_create(name="Mineral")
    resin, _ = Material.objects.get_or_create(name="Resin")
    stainless_steel, _ = Material.objects.get_or_create(name="Stainless Steel")

    # Create brands
    brands = ["Fastrack", "G-Shock", "Vintage"]
    brand_objects = [Brand.objects.get_or_create(brand_name=brand)[0] for brand in brands]

    # Sample product data
    products = [
        {
            "brand": random.choice(brand_objects),
            "gender": random.choice(["Men", "Women", "Unisex"]),
            "base_price": Decimal(random.uniform(50, 500)).quantize(Decimal("0.01")),
            "description": f"A stylish {random.choice(['casual', 'formal', 'sports'])} watch.",
            "total_stock": random.randint(50, 200),
            "color": random.choice(["Black", "Silver", "Gold", "Blue", "Red"]),
            "case_size": f"{random.randint(30, 45)} X {random.randint(30, 45)} X {random.randint(8, 15)}",
            "water_resistance": random.choice(["yes", "no"]),
            "water_resistance_depth": random.choice([30, 50, 100, 200]),
            "strap_color": random.choice(["Black", "Brown", "Silver", "Blue", "Red", "Green", "Yellow", "Orange", "Pink", "Purple"]),
            "dial_color": random.choice(["Black", "White", "Blue", "Green", "Red", "Yellow", "Orange", "Pink", "Purple"]),
            "warranty_period": random.choice([12, 24, 36]),
        }
        for _ in range(10)  # Create 10 sample products
    ]

    for product_data in products:
        model_name = generate_model_name()
        selling_price = (product_data["base_price"] * Decimal(random.uniform(0.8, 1.2))).quantize(Decimal("0.01"))

        # Create BaseWatch instance
        base_watch = BaseWatch.objects.create(
            vendor=vendor,
            category=category,
            brand=product_data["brand"],
            collection=collection,
            watch_type=watch_type,
            model_name=model_name,
            gender=product_data["gender"],
            slug=slugify(model_name),
            base_price=product_data["base_price"],
            selling_price=selling_price,
            description=product_data["description"],
            total_stock=product_data["total_stock"],
            available_stock=product_data["total_stock"],
            color=product_data["color"],
            style_code=model_name,
            is_active=True,
            is_in_stock=True,
        )

        # Create WatchDetails instance
        WatchDetails.objects.create(
            base_watch=base_watch,
            case_size=product_data["case_size"],
            water_resistance=product_data["water_resistance"],
            water_resistance_depth=product_data["water_resistance_depth"],
            strap_color=product_data["strap_color"],
            dial_color=product_data["dial_color"],
            warranty_period=product_data["warranty_period"],
        )

        # Create WatchMaterials instance
        WatchMaterials.objects.create(
            base_watch=base_watch,
            strap_material=random.choice([leather, resin]),
            glass_material=mineral,
            case_material=random.choice([resin, stainless_steel]),
        )

        print(f"Created product: {product_data['brand'].brand_name} {model_name}")

if __name__ == "__main__":
    create_sample_products()