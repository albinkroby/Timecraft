document.addEventListener('DOMContentLoaded', function() {
    const chatWidget = document.getElementById('chatbot-widget');
    const openChatBtn = document.getElementById('open-chat');
    const minimizeBtn = document.getElementById('minimize-chat');
    const sendMessage = document.getElementById('send-message');
    const userInput = document.getElementById('user-message');
    const chatMessages = document.getElementById('chat-messages');
    const typingIndicator = document.querySelector('.typing-indicator');

    // Check if elements exist before adding event listeners
    if (!chatWidget || !openChatBtn || !minimizeBtn || !sendMessage || !userInput || !chatMessages) {
        console.error('Required chat elements not found');
        return;
    }

    // Initialize with welcome message
    function initialize() {
        console.log('Initializing chat...');
        addBotMessage("Hello! 👋 How can I help you today?");
        console.log('Adding quick actions...');
        addQuickActions();
    }

    // Toggle chat window
    openChatBtn.addEventListener('click', () => {
        chatWidget.style.display = 'flex';
        openChatBtn.style.display = 'none';
        if (chatMessages.children.length === 0) {
            initialize();
        }
    });

    minimizeBtn.addEventListener('click', () => {
        chatWidget.style.display = 'none';
        openChatBtn.style.display = 'block';
    });

    // Send message function
    function sendUserMessage() {
        const message = userInput.value.trim();
        if (message) {
            addUserMessage(message);
            showTypingIndicator();
            processUserMessage(message);
            userInput.value = '';
        }
    }

    // Event listeners for sending messages
    sendMessage.addEventListener('click', sendUserMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendUserMessage();
        }
    });

    // Add message to chat
    function addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'user-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addBotMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'bot-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Add quick action buttons
    function addQuickActions() {
        const quickActionsDiv = document.createElement('div');
        quickActionsDiv.classList.add('quick-actions');
        
        const actions = [
            'What is TimeCraft?',
            'Product Information',
            'Pricing Details',
            'Contact Support'
        ];

        actions.forEach(action => {
            const button = document.createElement('button');
            button.classList.add('quick-action-btn');
            button.textContent = action;
            button.addEventListener('click', () => {
                addUserMessage(action);
                showTypingIndicator();
                processUserMessage(action);
            });
            quickActionsDiv.appendChild(button);
        });

        chatMessages.appendChild(quickActionsDiv);
    }

    // Typing indicator functions
    function showTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = 'block';
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function hideTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = 'none';
        }
    }

    // Process user message and get bot response
    function processUserMessage(message) {
        // Get CSRF token from the meta tag
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                         document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                         
        if (!csrfToken) {
            console.error('CSRF token not found');
            addBotMessage('Sorry, there was an error processing your request.');
            return;
        }

        // Send message to backend
        fetch('/chat/', {  // Changed from '/chat/message/' to '/chat/'
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                message: message
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            hideTypingIndicator();
            setTimeout(() => {
                addBotMessage(data.response);
            }, 500);
        })
        .catch(error => {
            console.error('Error:', error);
            hideTypingIndicator();
            addBotMessage('Sorry, I encountered an error. Please try again.');
        });
    }
});