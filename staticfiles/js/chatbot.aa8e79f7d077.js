document.addEventListener('DOMContentLoaded', function() {
    const chatButton = document.getElementById('chatButton');
    const chatContainer = document.getElementById('chatContainer');
    const closeChat = document.getElementById('closeChat');
    const chatInput = document.getElementById('chatInput');
    const sendMessage = document.getElementById('sendMessage');
    const chatMessages = document.getElementById('chatMessages');
    const typingIndicator = document.getElementById('typingIndicator');

    let chatWidget = document.querySelector('.chat-widget');

    chatButton.addEventListener('click', function() {
        chatWidget.classList.add('active');
        chatContainer.style.display = 'flex';
    });

    closeChat.addEventListener('click', function() {
        chatWidget.classList.remove('active');
        chatContainer.style.display = 'none';
    });

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        typingIndicator.style.display = 'block';
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function hideTypingIndicator() {
        typingIndicator.style.display = 'none';
    }

    async function sendChatMessage() {
        const message = chatInput.value.trim();
        if (message) {
            addMessage(message, true);
            chatInput.value = '';
            showTypingIndicator();

            try {
                const response = await fetch('/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                hideTypingIndicator();
                addMessage(data.response);
            } catch (error) {
                hideTypingIndicator();
                addMessage('Sorry, I encountered an error. Please try again.');
            }
        }
    }

    sendMessage.addEventListener('click', sendChatMessage);

    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
}); 