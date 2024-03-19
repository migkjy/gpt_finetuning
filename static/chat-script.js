document.addEventListener('DOMContentLoaded', () => {
    const model = new URLSearchParams(window.location.search).get('model');
    const apiKey = new URLSearchParams(window.location.search).get('apiKey');
    const systemMessage = new URLSearchParams(window.location.search).get('systemMessage');

    function sendMessage() {
        const prompt = document.getElementById('chat-input').value;
        if (!prompt.trim()) return; // Prevent sending empty messages
        displayMessage(prompt, 'user');
        document.getElementById('chat-input').value = ''; // Clear input after sending
        document.getElementById('loading').style.display = 'block'; // Show loading animation

        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt, model, apiKey, systemMessage }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading').style.display = 'none'; // Hide loading animation
            if(data.response) {
                displayMessage(data.response, 'gpt');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('loading').style.display = 'none';
        });
    }

    document.getElementById('send-prompt').addEventListener('click', sendMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function scrollToBottom() {
        var chatContainer = document.getElementById('chat-output');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    function displayMessage(message, sender) {
        const chatOutput = document.getElementById('chat-output');
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.innerHTML = `<span class="icon-${sender}"></span> <span class="text">${message}</span>`;
        chatOutput.appendChild(messageDiv);
        scrollToBottom();
    }

});
