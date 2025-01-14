document.addEventListener('DOMContentLoaded', function() {
    const chatWidget = document.getElementById('chatbot-widget');
    const openChatBtn = document.getElementById('open-chat');
    const minimizeBtn = document.getElementById('minimize-chat');
    const messagesContainer = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-message');
    const sendBtn = document.getElementById('send-message');
    const typingIndicator = document.querySelector('.typing-indicator');

    let chatContext = {};

    // Show typing indicator
    function showTypingIndicator() {
        const indicator = typingIndicator.cloneNode(true);
        indicator.style.display = 'block';
        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return indicator;
    }

    // Hide typing indicator
    function hideTypingIndicator(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }

    // Add welcome message and show quick actions
    function showWelcomeMessage() {
        messagesContainer.innerHTML = ''; // Clear existing messages
        addMessage('👋 Hello! How can I help you today? Please select an option below or type your question.', 'bot-message welcome-message');
        document.getElementById('quick-actions').style.display = 'grid';
    }

    // Toggle chat widget
    openChatBtn.addEventListener('click', () => {
        chatWidget.style.display = 'flex';
        openChatBtn.style.display = 'none';
        showWelcomeMessage(); // Show welcome message instead of loading chat history
    });

    minimizeBtn.addEventListener('click', () => {
        chatWidget.style.display = 'none';
        openChatBtn.style.display = 'block';
    });

    // Handle quick action button clicks
    document.querySelectorAll('.quick-action-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const action = button.dataset.action;
            document.getElementById('quick-actions').style.display = 'none';
            
            // Add user's selection as a message
            addMessage(button.textContent.trim(), 'user-message');
            
            // Show typing indicator
            const indicator = showTypingIndicator();
            
            // Add artificial delay
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Hide typing indicator
            hideTypingIndicator(indicator);
            
            // Add response based on action
            let response;
            switch(action) {
                case 'orders':
                    response = "You can check your order status and history in your account dashboard. Would you like me to help you track a specific order?";
                    break;
                case 'payment':
                    response = "We accept all major credit cards, UPI, and net banking. What specific payment information do you need?";
                    break;
                case 'shipping':
                    response = "We typically deliver within 5-7 business days across India. Would you like to know about shipping costs or tracking an existing order?";
                    break;
                case 'returns':
                    response = "Our return policy allows returns within 7 days of delivery. Would you like to know more about the return process or initiate a return?";
                    break;
                case 'contact':
                    response = "You can reach our support team at support@example.com or call us at 1800-XXX-XXXX. How would you like to contact us?";
                    break;
                default:
                    response = "I'm here to help! What would you like to know?";
            }
            addMessage(response, 'bot-message');
        });
    });

    // Send message with improved error handling
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        try {
            addMessage(message, 'user-message');
            userInput.value = '';
            
            const indicator = showTypingIndicator();

            const response = await fetch('/chat/message/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ 
                    message: message,
                    context: chatContext 
                })
            });

            hideTypingIndicator(indicator);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.error) {
                console.error('Server error:', data.error);
                addMessage('Sorry, something went wrong. Please try again.', 'bot-message');
            } else {
                addMessage(data.response, 'bot-message');
                chatContext = data.context || {};
                
                // Show quick actions if available
                if (data.context && data.context.quick_actions) {
                    showQuickActions(data.context.quick_actions);
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            addMessage('Sorry, there was an error sending your message. Please try again.', 'bot-message');
        }
    }

    // Add message to chat with error handling
    function addMessage(message, className) {
        try {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${className}`;
            messageDiv.textContent = message;
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } catch (error) {
            console.error('Error adding message to chat:', error);
        }
    }

    // Load chat history with error handling
    async function loadChatHistory() {
        try {
            const response = await fetch('/chat/history/');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            messagesContainer.innerHTML = '';
            data.history.forEach(item => {
                addMessage(item.message, 'user-message');
                addMessage(item.response, 'bot-message');
            });
        } catch (error) {
            console.error('Error loading chat history:', error);
            addMessage('Error loading chat history. Please refresh the page.', 'bot-message');
        }
    }

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Improved CSRF token getter
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showQuickActions(actions) {
        const quickActionsContainer = document.getElementById('quick-actions');
        quickActionsContainer.innerHTML = '';
        
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'quick-action-btn';
            button.textContent = action.text;
            button.onclick = () => handleQuickAction(action);
            quickActionsContainer.appendChild(button);
        });
        
        quickActionsContainer.style.display = 'grid';
    }
});