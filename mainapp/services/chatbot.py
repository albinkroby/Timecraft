from django.conf import settings
from openai import OpenAI
from adminapp.models import BaseWatch, Brand, Material, Feature, Category
from django.db.models import Q
import json
import re

class ChatbotService:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=settings.OPENAI_API_KEY
        )
        
        # Get product information from database
        self.product_info = self._get_product_info()
        
        self.system_prompt = """You are Timely, a customer service assistant for TimeCraft Watches.
            Your purpose is to help customers with:
            - Watch-related queries
            - Store policies and information
            - Product recommendations
            - Shipping and delivery
            - Returns and warranty
            
            Store Information:
            - Free shipping on orders above ₹999
            - 7-day return policy
            - Payment methods: Credit/Debit Cards, UPI, Net Banking
            - Standard delivery: 5-7 business days
            
            Current Product Catalog:
            {self.product_info}
            
            When discussing products:
            - Use accurate prices and specifications from the product catalog
            - Mention available colors and materials
            - Include water resistance information when relevant
            - Share warranty details if available
            
            Important Instructions:
            1. Respond naturally to greetings and common pleasantries
            2. For other non-watch topics (sports, politics, general knowledge, etc.), politely explain that you can only help with watch-related queries
            3. Stay focused on helping customers with their watch shopping needs
            4. your name is Timely, a friendly customer service assistant for TimeCraft Watches
            
            Respond in a friendly, professional manner. Keep responses concise but helpful.
            """

    def _get_product_info(self):
        """Fetch and format product information from database"""
        products = BaseWatch.objects.filter(is_active=True).select_related(
            'brand', 'category', 'materials', 'details'
        ).prefetch_related('features')

        product_info = []
        for product in products:
            try:
                info = f"""
                Product: {product.model_name}
                Image: {product.primary_image.url if product.primary_image else ''}
                URL: /product/{product.slug}/
                Brand: {product.brand.brand_name}
                Price: ₹{product.selling_price or product.base_price}
                Color: {product.color}
                """

                if hasattr(product, 'materials') and product.materials:
                    materials = product.materials
                    info += f"Strap: {materials.strap_material.name if materials.strap_material else 'N/A'}\n"

                if hasattr(product, 'details') and product.details:
                    details = product.details
                    if details.water_resistance_depth:
                        info += f"Water Resistance: {details.water_resistance_depth}m\n"
                    if details.warranty_period:
                        info += f"Warranty: {details.warranty_period} months\n"

                product_info.append(info)
            except Exception as e:
                print(f"Error processing product {product.model_name}: {str(e)}")
                continue

        return "\n\n".join(product_info)

    def get_response(self, user_message):
        try:
            # Define greeting keywords
            greeting_keywords = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 
                              'good evening', 'thanks', 'thank you', 'bye', 'goodbye', 'can you help me','who are you','what is your name','what is your purpose','what is your job','what is your role','what is your function','what is your task','what is your objective','what is your goal','what is your mission','what is your purpose','what is your function','what is your job','what is your role','what is your task','what is your objective','what is your goal','what is your mission']
            
            # Define watch and store-related keywords
            watch_keywords = ['watch', 'price', 'cost', 'brand', 'strap', 'time', 'warranty', 
                            'delivery', 'shipping', 'return', 'payment', 'order', 'timecraft', 'pricing details']
            
            product_keywords = ['watch', 'price', 'cost', 'show', 'looking', 'need', 'want', 'search', 'find']
            
            message_lower = user_message.lower()
            
            # Check if message is a greeting
            is_greeting = any(keyword in message_lower for keyword in greeting_keywords)
            
            # Check if message contains watch-related keywords
            is_watch_query = any(keyword in message_lower for keyword in watch_keywords)
            
            # Change this line - store result directly in variable
            is_product_query = any(keyword in message_lower for keyword in product_keywords)
            
            if is_greeting:
                # Handle greetings using GPT-4
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a friendly customer service assistant. Keep responses warm but brief."},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7,
                    max_tokens=50
                )
                return response.choices[0].message.content
            
            elif is_watch_query:
                # Check if it's a general pricing query
                if any(term in message_lower for term in ['price range', 'pricing', 'how much', 'cost range']):
                    return self.handle_pricing_overview()
                
                # Process specific product queries
                if is_product_query:
                    return self.handle_product_query(user_message)
                
                # For other watch-related queries, use GPT-4
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                return response.choices[0].message.content
            else:
                # For non-watch related queries, return a polite redirect
                return ("I apologize, but I can only help you with questions about watches, our store, "
                       "and our services. Is there anything specific about our watches or services "
                       "that you'd like to know?")
            
        except Exception as e:
            print(f"Error in ChatbotService: {str(e)}")
            return "I apologize, but I'm having trouble processing your request."
        
        
    def handle_product_query(self,user_message):
        price_match = re.search(r'(?:less than|under|below|maximum|max|up to)\s*(?:Rs\.?|\₹)?\s*(\d+)', user_message.lower())
        if price_match:
            max_price = int(price_match.group(1))
            products = self.search_products(user_message, max_price=max_price)
        else:
            price_range_match = re.search(r'between\s*(?:Rs\.?|\₹)?\s*(\d+)\s*(?:and|to)\s*(\d+)', user_message.lower())
            if price_range_match:
                min_price = int(price_range_match.group(1))
                max_price = int(price_range_match.group(2))
                products = self.search_products(user_message, min_price=min_price, max_price=max_price)
            else:
                products = self.search_products(user_message)

        if products.exists():
            return self.format_products_as_cards(products)

    def search_products(self, query, min_price=None, max_price=None):
        """Search for products matching the query and price range"""
        # Start with all active products
        products = BaseWatch.objects.filter(is_active=True)

        # Apply price filters
        if max_price:
            products = products.filter(selling_price__lte=max_price)
        if min_price:
            products = products.filter(selling_price__gte=min_price)

        # Check for color terms
        color_terms = ['black', 'blue', 'red', 'gold', 'silver', 'brown']
        color = next((term for term in color_terms if term in query.lower()), None)
        if color:
            products = products.filter(color__icontains=color)

        # Check for gender terms
        if 'men' in query.lower() or 'male' in query.lower():
            products = products.filter(gender__icontains='M')
        elif 'women' in query.lower() or 'female' in query.lower():
            products = products.filter(gender__icontains='F')

        # Check for material terms
        if 'leather' in query.lower():
            products = products.filter(materials__strap_material__name__icontains='leather')
        elif 'metal' in query.lower():
            products = products.filter(materials__strap_material__name__icontains='metal')

        return products.select_related(
            'brand', 'materials', 'details'
        ).prefetch_related('features')[:5]  # Limit to 5 products

    def format_products_as_cards(self, products):
        """Format products as cards"""
        formatted_products = []
        
        for product in products:
            try:
                product_info = {
                    "type": "product_card",
                    "name": f"{product.brand.brand_name} - {product.model_name}",
                    "image_url": product.primary_image.url if product.primary_image else None,
                    "price": str(product.selling_price or product.base_price),
                    "url": f"/product/{product.slug}/",
                    "details": []
                }

                # Add materials if available
                if hasattr(product, 'materials') and product.materials:
                    if product.materials.strap_material:
                        product_info["details"].append(f"Strap: {product.materials.strap_material.name}")

                # Add watch details if available
                if hasattr(product, 'details') and product.details:
                    if product.details.water_resistance_depth:
                        product_info["details"].append(f"Water Resistance: {product.details.water_resistance_depth}m")
                    if product.details.warranty_period:
                        product_info["details"].append(f"Warranty: {product.details.warranty_period} months")

                formatted_products.append(product_info)
            except Exception as e:
                print(f"Error formatting product {product.model_name}: {str(e)}")
                continue

        # Return the formatted response
        return {
            "type": "product_response",
            "message": "Here are some watches that match your request:",
            "products": formatted_products
        }

    def handle_pricing_overview(self):
        """Generate a pricing overview of available watches"""
        products = BaseWatch.objects.filter(is_active=True).values(
            'brand__brand_name', 
            'selling_price', 
            'base_price',
            'model_name'
        ).order_by('selling_price')
        
        if not products:
            return "I apologize, but we don't have any watches in stock at the moment."
        
        min_price = min(p['selling_price'] or p['base_price'] for p in products)
        max_price = max(p['selling_price'] or p['base_price'] for p in products)
        
        # Group watches by price range
        budget_watches = [p for p in products if (p['selling_price'] or p['base_price']) < 5000]
        mid_range_watches = [p for p in products if 5000 <= (p['selling_price'] or p['base_price']) <= 15000]
        premium_watches = [p for p in products if (p['selling_price'] or p['base_price']) > 15000]
        
        overview = f"Our watches range from ₹{min_price:,} to ₹{max_price:,}. Here's a detailed breakdown:\n\n"
        
        if budget_watches:
            overview += "Budget Friendly Watches (Under ₹5,000):\n"
            for watch in budget_watches[:3]:  # Show up to 3 examples
                overview += f"- {watch['brand__brand_name']} {watch['model_name']}: ₹{watch['selling_price'] or watch['base_price']:,}\n"
            overview += "\n"
        
        if mid_range_watches:
            overview += "Mid-Range Watches (₹5,000 - ₹15,000):\n"
            for watch in mid_range_watches[:3]:
                overview += f"- {watch['brand__brand_name']} {watch['model_name']}: ₹{watch['selling_price'] or watch['base_price']:,}\n"
            overview += "\n"
        
        if premium_watches:
            overview += "Premium Watches (Above ₹15,000):\n"
            for watch in premium_watches[:3]:
                overview += f"- {watch['brand__brand_name']} {watch['model_name']}: ₹{watch['selling_price'] or watch['base_price']:,}\n"
            overview += "\n"
        
        overview += "\nWould you like to see more watches in any specific price range? You can ask for:\n"
        overview += "- Watches under ₹5,000\n"
        overview += "- Watches between ₹5,000 and ₹15,000\n"
        overview += "- Premium watches above ₹15,000"
        
        return overview