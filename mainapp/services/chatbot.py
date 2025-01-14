from typing import Dict, Any, Optional
from django.conf import settings
from django.db.models import Q
import logging
import re
from ..models import Order, SupportTicket, ChatMessage
from adminapp.models import BaseWatch
from openai import OpenAI

# Set up logging
logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=settings.OPENAI_API_KEY)

class ChatbotService:
    def __init__(self, user):
        self.user = user
        self.intents = {
            'order_status': r'\b(order|track|status)\b',
            'product_info': r'\b(watch|product|price)\b',
            'shipping': r'\b(shipping|delivery|track)\b',
            'return': r'\b(return|refund|cancel)\b',
            'support': r'\b(help|support|issue)\b'
        }

    def detect_intent(self, message: str) -> str:
        message = message.lower()
        for intent, pattern in self.intents.items():
            if re.search(pattern, message):
                return intent
        return 'general'

    def get_order_info(self, order_id: Optional[str] = None) -> str:
        orders = Order.objects.filter(user=self.user)
        if order_id:
            order = orders.filter(order_id=order_id).first()
            if order:
                return (f"Order #{order.order_id}\n"
                       f"Status: {order.status}\n"
                       f"Total: ₹{order.total_amount}\n"
                       f"Created: {order.created_at.strftime('%Y-%m-%d')}")
            return "Order not found."
        
        recent_orders = orders.order_by('-created_at')[:3]
        if not recent_orders:
            return "You don't have any orders yet."
        
        response = "Recent Orders:\n"
        for order in recent_orders:
            response += f"- Order #{order.order_id}: {order.status}\n"
        return response

    def get_product_info(self, query: str) -> str:
        watches = BaseWatch.objects.filter(
            Q(model_name__icontains=query) |
            Q(brand__brand_name__icontains=query)
        )[:3]
        
        if not watches:
            return "No matching products found."
        
        response = "Found these watches:\n"
        for watch in watches:
            response += f"- {watch.model_name}: ₹{watch.base_price}\n"
        return response

    def create_support_ticket(self, issue: str) -> str:
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject="Chat Support Ticket",
            description=issue,
            priority='medium'
        )
        return f"Support ticket #{ticket.id} created. Our team will assist you soon."

    def process_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            intent = self.detect_intent(message)
            response = ""
            new_context = context or {}

            logger.info(f"Processing message with intent: {intent}")

            if context and context.get('expecting_order_id'):
                response = self.get_order_info(message)
                new_context = {}
            elif intent == 'order_status':
                response = self.get_order_info()
                new_context = {'expecting_order_id': True}
            elif intent == 'product_info':
                response = self.get_product_info(message)
            elif intent == 'support':
                response = self.create_support_ticket(message)
            else:
                # Use OpenAI for general inquiries
                response = self.get_ai_response(message, intent)

            # Create chat message record
            try:
                ChatMessage.objects.create(
                    user=self.user,
                    message=message,
                    response=response,
                    intent=intent,
                    context=new_context
                )
            except Exception as e:
                logger.error(f"Error creating chat message: {str(e)}")

            return {
                'response': response,
                'context': new_context
            }

        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            return {
                'response': "I apologize, but I'm having trouble processing your request. Please try again.",
                'context': {}
            }

    def get_ai_response(self, message: str, intent: str) -> str:
        try:
            logger.info("Attempting to get AI response")
            
            system_prompt = f"""You are Timely, a customer service assistant for TimeCraft Watches.
            Current user: {self.user.fullname}
            Intent detected: {intent}
            
            Store Information:
            - Free shipping on orders above ₹999
            - 7-day return policy
            - Payment methods: Credit/Debit Cards, UPI, Net Banking
            - Standard delivery: 5-7 business days
            
            Respond in a friendly, professional manner."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            if response.choices and len(response.choices) > 0:
                logger.info("Successfully received AI response")
                return response.choices[0].message.content
            
            logger.warning("No response choices available from OpenAI")
            return "I apologize, but I'm having trouble generating a response right now."
            
        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later." 