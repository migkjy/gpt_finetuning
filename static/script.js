
function extractDataFrameMAIN() {
    const tableElement = document.getElementById('dataframe');
    if (!tableElement) {
        return;
    }

    // Get the HTML content of the table
    const htmlContent = document.getElementById('dataframe').outerHTML;
    // Send an AJAX request to the server to extract the DataFrame
    fetch('/extract_dataframe', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ html_content: htmlContent })
    })
    .then(response => response.json())
    .then(data => {
        // Print the extracted DataFrame
        console.log(data);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to extract DataFrame.');
    });
}

function clearProgress() {
    fetch('/clear_progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.ok) {
            console.log('App restarted successfully');
            showClearButton(false);
            window.location.reload();
        } else {
            console.error('Failed to restart the app');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function showClearButton(showClear) {
    const clearButton = document.getElementById('clear-session');
    if (showClear) {
        clearButton.style.display = 'block';
    } else {
        clearButton.style.display = 'none';
    }
}


function fetchStatus() {
    fetch('/get_status')
    .then(response => response.json())
    .then(data => {
        if (data.example_data) {
            showClearButton(true);
        } else {
            showClearButton(false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}



document.addEventListener('DOMContentLoaded', function() {
    fetchStatus();
    let modelId = null; // Variable to store the model ID

    // Event listener for the temperature input
    document.getElementById('temperature').addEventListener('input', function() {
        document.getElementById('temperature-value').textContent = this.value;
    });

    // Start training event listener
    document.getElementById('generate-examples').addEventListener('click', function() {
        showClearButton(true);
        const data = {
            apiKey: document.getElementById('api-key').value,
            model: document.getElementById('gpt-model').value,
            prompt: document.getElementById('prompt-input').value,
            temperature: parseFloat(document.getElementById('temperature').value),
            numExamples: parseInt(document.getElementById('num-examples').value, 10),
        };
        extractDataFrameMAIN();
        showLoader();
        fetch('/generate_examples', {
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
        let text = document.getElementById('status-area').innerText;
        let modelId = null;
        if (text.includes('Job ID')) {
            let match = text.match(/Job ID: (\S+)/);
            // If a match is found, the file ID will be in the second element of the match array (index 1)
            if (match && match[1]) {
                // Assign the extracted file ID to modelId
                modelId = match[1];
                console.log(modelId);
            }
        }
        
        if (modelId == null) {
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
                    const linkWrapper = document.createElement('div'); // Create a div to wrap the link
                    linkWrapper.appendChild(link); // Append the link to the div
                    document.getElementById('status-area').appendChild(linkWrapper); // Append the div to the status area                    
                    hideLoader();
                    clearInterval(intervalId); // Stop polling
                }
                
                // Training is done and examples are ready to be reviewed
                if (data.example_data)
                {
                    hideLoader();
                    clearInterval(intervalId); // Stop polling
                    const dataToSend = {
                        training_data: data.example_data,
                        system_message: data.system_message,

                    };
                    fetch('/edit_examples', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(dataToSend)
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok');
                        }
                        // Assuming the response is HTML
                        return response.text();
                    })
                    .then(htmlContent => {
                        // Display the HTML content inside the div with id "dataframeElement"
                        document.getElementById('dataframeElement').innerHTML = htmlContent;
                        // Dynamically create a script element
                        var scriptElement = document.createElement('script');

                        // Set the source of the script element
                        // If you're using a templating engine that processes JavaScript files, you might need to adjust this URL
                        scriptElement.src = "/static/review-script.js"; // Update this path to where your JS file is located

                        // Optionally, set the type to "module" if your script uses ES6 modules
                        // scriptElement.type = "module";

                        // Append the script element to the document, triggering its load and execution
                        document.body.appendChild(scriptElement);

                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });

                }
                //Training is done
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

document.getElementById('toggle-password').addEventListener('click', function (e) {
    const apiKeyInput = document.getElementById('api-key');
    const toggleIcon = document.getElementById('toggle-password');
    const type = apiKeyInput.getAttribute('type') === 'password' ? 'text' : 'password';
    apiKeyInput.setAttribute('type', type);
    // Change the icon for visual feedback
    toggleIcon.textContent = type === 'text' ? '👁️' : '👁️‍🗨️'; // Example uses different eye icons
});


document.getElementById('num-examples').addEventListener('blur', enforceRange);

function enforceRange() {
    const input = document.getElementById('num-examples');
    const min = parseInt(input.min, 10);
    const max = parseInt(input.max, 10);
    let value = parseInt(input.value, 10);

    if (value < min) {
        input.value = min;
    } else if (value > max) {
        input.value = max;
    }
}

function changeValue(step) {
    const input = document.getElementById('num-examples');
    let value = parseInt(input.value, 10) || 0; // Fallback to 0 if input.value is not a number
    value += step;
    input.value = value;
    enforceRange(); // Ensure the new value respects min and max
}