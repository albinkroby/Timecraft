let currentChatSession = null;
let currentPage = 1;
let isLoadingMessages = false;
let hasMoreMessages = true;

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
        scrollToBottom();
    });

    minimizeBtn.addEventListener('click', () => {
        chatWidget.style.display = 'none';
        openChatBtn.style.display = 'block';
    });

    // Send message function
    function processMessage(message) {
        if (!message.trim() || !currentChatSession?.id) return;

        // Show typing indicator
        showTypingIndicator();

        // Add user message to UI immediately
        addUserMessage(message);

        // Clear input
        userInput.value = '';

        fetch('/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                message: message,
                session_id: currentChatSession.id
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
            if (data.error) {
                addBotMessage("I'm sorry, I encountered an error. Please try again.");
                console.error('Error:', data.error);
            } else {
                addBotMessage(data.response);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            hideTypingIndicator();
            addBotMessage("I'm sorry, I encountered an error. Please try again.");
        });
    }

    // Event listeners for sending messages
    sendMessage.addEventListener('click', () => {
        const message = userInput.value.trim();
        if (message) {
            processMessage(message);
        }
    });
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = userInput.value.trim();
            if (message) {
                processMessage(message);
            }
        }
    });

    // Add message to chat
    function addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'user-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function addBotMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'bot-message');
        
        try {
            // Try to parse the message as JSON
            const data = typeof message === 'string' ? JSON.parse(message) : message;
            
            // Check if it's a product response
            if (data.type === 'product_response') {
                // Add the introduction message
                const introText = document.createElement('div');
                introText.classList.add('intro-text');
                introText.textContent = data.message;
                messageDiv.appendChild(introText);
                
                // Create product cards container
                const cardsContainer = document.createElement('div');
                cardsContainer.classList.add('product-cards-container');
                
                // Create cards for each product
                data.products.forEach(product => {
                    const card = createProductCard(product);
                    cardsContainer.appendChild(card);
                });
                
                messageDiv.appendChild(cardsContainer);
            } else {
                // Regular message formatting
                messageDiv.textContent = message;
            }
        } catch (e) {
            // If not JSON or error occurs, treat as regular message
            const formattedMessage = message.split('\n').map(line => {
                line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                if (line.match(/^\d+[\.\)-]\s/)) {
                    return `<div class="list-item">${line}</div>`;
                }
                return `<div class="text-line">${line}</div>`;
            }).join('');
            
            messageDiv.innerHTML = formattedMessage;
        }
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function createProductCard(product) {
        const card = document.createElement('div');
        card.classList.add('product-card');
        
        card.innerHTML = `
            <div class="product-image">
                <img src="${product.image_url || '/static/images/default-watch.png'}" alt="${product.name}">
            </div>
            <div class="product-info">
                <h4>${product.name}</h4>
                <p class="price">₹${product.price}</p>
                <div class="product-details">
                    ${product.details.map(detail => `<p>${detail}</p>`).join('')}
                </div>
                <a href="${product.url}" class="view-product-btn">View Product</a>
            </div>
        `;
        
        return card;
    }

    // Add quick action buttons
    function addQuickActions() {
        const quickActionsDiv = document.createElement('div');
        quickActionsDiv.classList.add('quick-actions');
        
        const actions = [
            'How to use TimeCraft?',
            'Product Information',
            'Pricing Details',
            'Contact Support'
        ];

        actions.forEach(action => {
            const button = document.createElement('button');
            button.classList.add('quick-action-btn');
            button.textContent = action;
            button.addEventListener('click', () => {
                processMessage(action);
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

    // Add new chat button
    const newChatBtn = document.createElement('button');
    newChatBtn.id = 'new-chat-btn';
    newChatBtn.innerHTML = '<i class="fas fa-plus"></i>';
    newChatBtn.classList.add('new-chat-btn');
    document.querySelector('.chat-header').appendChild(newChatBtn);

    // Add event listener for new chat button
    newChatBtn.addEventListener('click', startNewChat);

    // Initial session load
    loadChatSession();

    function startNewChat() {
        // Clear messages
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = '';
        
        // Clear current session
        currentChatSession = null;
        localStorage.removeItem('chatSessionId');
        
        // Initialize new session
        initializeNewSession();
    }

    function initializeNewSession() {
        // Check if user is authenticated
        fetch('/chat/check-auth/')
            .then(response => response.json())
            .then(data => {
                if (data.is_authenticated) {
                    createNewSession(data.username);
                } else {
                    askForName();
                }
            })
            .catch(error => {
                console.error('Error checking auth:', error);
                addBotMessage("Sorry, there was an error starting a new chat. Please try again.");
            });
    }

    function askForName() {
        const chatMessages = document.getElementById('chat-messages');
        const namePrompt = document.createElement('div');
        namePrompt.classList.add('name-prompt');
        namePrompt.innerHTML = `
            <div class="name-input-container">
                <input type="text" id="guest-name" placeholder="Please enter your name">
                <button id="submit-name">Start Chat</button>
            </div>
        `;
        chatMessages.appendChild(namePrompt);

        const submitButton = document.getElementById('submit-name');
        const nameInput = document.getElementById('guest-name');

        submitButton.addEventListener('click', () => {
            const name = nameInput.value.trim();
            if (name) {
                createNewSession(name);
                namePrompt.remove();
            }
        });

        nameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const name = nameInput.value.trim();
                if (name) {
                    createNewSession(name);
                    namePrompt.remove();
                }
            }
        });
    }

    function createNewSession(name) {
        fetch('/chat/session/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ guest_name: name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            currentChatSession = data.session;
            localStorage.setItem('chatSessionId', data.session.id);
            initialize();
        })
        .catch(error => {
            console.error('Error creating session:', error);
            addBotMessage("Sorry, there was an error starting a new chat. Please try again.");
        });
    }

    function getCsrfToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        return csrfToken;
    }

    function loadChatSession() {
        const sessionId = localStorage.getItem('chatSessionId');
        if (sessionId) {
            loadMessages(sessionId, true);
        } else {
            initializeNewSession();
        }
    }

    function loadMessages(sessionId, isInitial = false) {
        if (isLoadingMessages || (!hasMoreMessages && !isInitial)) return;
        
        isLoadingMessages = true;
        showLoadingIndicator();

        fetch(`/chat/session/${sessionId}?page=${currentPage}`)
            .then(response => response.json())
            .then(data => {
                if (data.session) {
                    currentChatSession = data.session;
                    hasMoreMessages = data.has_more;

                    // If it's initial load, clear existing messages
                    if (isInitial) {
                        chatMessages.innerHTML = '';
                    }

                    // Add messages at the top
                    const fragment = document.createDocumentFragment();
                    data.messages.forEach(msg => {
                        const messageDiv = document.createElement('div');
                        messageDiv.classList.add('message', msg.is_user ? 'user-message' : 'bot-message');
                        
                        if (msg.is_user) {
                            messageDiv.textContent = msg.message;
                        } else {
                            try {
                                // Handle product cards and other formatted messages
                                const parsedMessage = typeof msg.message === 'string' ? 
                                    JSON.parse(msg.message) : msg.message;
                                if (parsedMessage.type === 'product_response') {
                                    // Add product cards
                                    messageDiv.innerHTML = formatProductResponse(parsedMessage);
                                } else {
                                    messageDiv.textContent = msg.message;
                                }
                            } catch (e) {
                                messageDiv.textContent = msg.message;
                            }
                        }
                        
                        fragment.insertBefore(messageDiv, fragment.firstChild);
                    });

                    // Add load more button if there are more messages
                    if (data.has_more) {
                        const loadMoreBtn = document.createElement('button');
                        loadMoreBtn.classList.add('load-more-btn');
                        loadMoreBtn.textContent = 'Load Previous Messages';
                        fragment.insertBefore(loadMoreBtn, fragment.firstChild);
                    }

                    // Insert all content at the top of chat
                    chatMessages.insertBefore(fragment, chatMessages.firstChild);

                    if (isInitial) {
                        scrollToBottom();
                    }

                    currentPage++;
                } else {
                    initializeNewSession();
                }
            })
            .catch(error => {
                console.error('Error loading messages:', error);
                if (isInitial) {
                    initializeNewSession();
                }
            })
            .finally(() => {
                isLoadingMessages = false;
                hideLoadingIndicator();
            });
    }

    function showLoadingIndicator() {
        const existingIndicator = document.querySelector('.messages-loading');
        if (!existingIndicator) {
            const indicator = document.createElement('div');
            indicator.classList.add('messages-loading');
            indicator.textContent = 'Loading messages...';
            chatMessages.insertBefore(indicator, chatMessages.firstChild);
        }
    }

    function hideLoadingIndicator() {
        const indicator = document.querySelector('.messages-loading');
        if (indicator) {
            indicator.remove();
        }
    }

    chatMessages.addEventListener('scroll', () => {
        if (chatMessages.scrollTop === 0 && hasMoreMessages) {
            loadMessages(currentChatSession.id);
        }
    });

    function formatProductResponse(response) {
        let html = `<div class="intro-text">${response.message}</div>`;
        html += '<div class="product-cards-container">';
        response.products.forEach(product => {
            html += `
                <div class="product-card">
                    <div class="product-image">
                        <img src="${product.image_url || '/static/images/default-watch.png'}" alt="${product.name}">
                    </div>
                    <div class="product-info">
                        <h4>${product.name}</h4>
                        <p class="price">₹${product.price}</p>
                        <div class="product-details">
                            ${product.details.map(detail => `<p>${detail}</p>`).join('')}
                        </div>
                        <a href="${product.url}" class="view-product-btn">View Product</a>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        return html;
    }

    function scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});