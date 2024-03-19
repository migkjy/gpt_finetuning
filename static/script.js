document.addEventListener('DOMContentLoaded', function() {
    let modelId = null; // Variable to store the model ID

    // Event listener for the temperature input
    document.getElementById('temperature').addEventListener('input', function() {
        document.getElementById('temperature-value').textContent = this.value;
    });

    // Start training event listener
    document.getElementById('train').addEventListener('click', function() {
        const data = {
            apiKey: document.getElementById('api-key').value,
            prompt: document.getElementById('prompt-input').value,
            temperature: parseFloat(document.getElementById('temperature').value),
            numExamples: parseInt(document.getElementById('num-examples').value, 10),
        };

        showLoader();
        fetch('/start_training', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(data => {
            showLoader()
            document.getElementById('status-area').innerText = 'Training initiated...';
            pollForUpdates(); // Start polling for updates
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('status-area').innerText = 'Error initiating training.';
            hideLoader();
        });
    });

    // Start fine-tuning event listener
    document.getElementById('create-fine-tune').addEventListener('click', function() {
        if (!modelId) {
            document.getElementById('status-area').innerText = 'No job id found. Please complete training first.';
            return;
        }

        showLoader();
        const data = { modelId: modelId }; // Pass the model ID for fine-tuning
        fetch('/start_fine_tuning', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(data => {
            //document.getElementById('status-area').innerText = data.message;
            pollForUpdates(); // Optionally, poll for updates on fine-tuning as well
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('status-area').innerText = 'Error initiating fine-tuning.';
            hideLoader();
        });
    });

    // Function to poll for updates on the server's task status
    function pollForUpdates() {
        const intervalId = setInterval(() => {
            fetch('/get_status')
            .then(response => response.json())
            .then(data => {
                
                document.getElementById('status-area').innerText = data.message;
                showLoader();
                if (data.message.includes("[*] Fine Tuning Completed!")) {
                    console.log("Hiding loader bec Fine Tuning Completed is found!");
                    const modelName = data.modelName
                    const systemMessage = data.systemMessage
                    const api = data.apiKey
                    const link = document.createElement('a');
                    link.href = `/chat?model=${modelName}&apiKey=${api}&systemMessage=${systemMessage}`;
                    link.textContent = "Click here to chat with this model";
                    document.getElementById('status-area').appendChild(link);
                    hideLoader();
                    clearInterval(intervalId); // Stop polling
                }
            
            
                if (data.modelId) {
                    modelId = data.modelId; // Save the model ID if present
                    //document.getElementById('status-area').innerText += "\nJob ID received: " + modelId;
                    console.log("Hiding loader bec modelId is found!");
                    hideLoader();
                    clearInterval(intervalId); // Stop polling
                }
                if ((data.message === "Training finished!" || data.message.includes("[*]")) && false) {
                    console.log("Hiding loader bec Fine Tuning Completed is found!");
                    hideLoader();
                    clearInterval(intervalId); // Stop polling
                }
            })
            .catch(error => {
                console.error('Error polling status:', error);
                clearInterval(intervalId);
            });
        }, 2000); // Poll every 2000 milliseconds (2 seconds)
    }

    function showLoader() {
        let loader = document.getElementById('loader');
        statusText = document.getElementById('status-area').innerText
        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'loader';
            loader.innerHTML = `
            <div class="loader-content">
                <div class="loader-circle"></div>
                <div id="loader-text">${statusText}</div>
            </div>`; // Flex container for circle and text
            document.body.appendChild(loader);
        } else {
            // Update the loader text if loader already exists
            document.getElementById('loader-text').textContent = statusText;
        }
    }
    
    function hideLoader() {
        const loader = document.getElementById('loader');
        if (loader) {
            loader.remove();
        }
    }
    
    // Make sure to update the status area and loader text together
    function updateStatus(message) {
        document.getElementById('status-area').innerText = message;
        showLoader(message); // Update loader text to match status
    }
        
});
