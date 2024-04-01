
function getSystemMessage() {
            event.preventDefault();
            console.log('getSystemMessage is called');
            const apiKey = document.getElementById('api-key').value;
            const model = document.getElementById('gpt-model').value;
            const prompt = document.getElementById('prompt-input').value;

            const url = new URL('/get_system_message', window.location.href);
            url.searchParams.append('prompt', prompt);


            
            fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                const systemMessage = data.system_message;
                document.getElementById('system-message').value = systemMessage;
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }

function extractDataFrame() {
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

function pollForUpdates() {
    const intervalId = setInterval(() => {
        fetch('/get_status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('status-area').innerText = data.message;
            if (data.modelId) {
                modelId = data.modelId; // Save the model ID if present
                //document.getElementById('status-area').innerText += "\nJob ID received: " + modelId;
                console.log("Hiding loader bec modelId is found!");
                hideLoader();
                clearInterval(intervalId); // Stop polling
            }})
            .catch(error => {
                console.error('Error polling status:', error);
                clearInterval(intervalId);
            });
        }, 2000); // Poll every 2000 milliseconds (2 seconds)
    }
function uploadTrainingData(){
    event.preventDefault();
    
    // Get the HTML content of the table
    const htmlContent = document.getElementById('dataframe').outerHTML;
    const systemMessage = document.getElementById('system-message').value;
    // Send an AJAX request to the server to extract the DataFrame
    fetch('/confirm_training_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ html_content: htmlContent, system_message: systemMessage })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('status-area').innerText = data.message;
        

        modelId = data.modelId;
        const element = document.getElementById('dataframeElement');
        if (element) {
            // Remove the element from the document
            //element.remove();
            toggleForm();
        }
        const genExamplesBTN = document.getElementById('generate-examples');
        if (genExamplesBTN)
        { }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to extract DataFrame.');
    });
}

function regenerateRow(index) {
    event.preventDefault();
    extractDataFrame();
    // Send an AJAX request to the server to regenerate the row
    fetch(`/regenerate/${index}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Update the HTML table with the new DataFrame
            updateTable(data);
        });
}


function deleteSelected() {
    const checkboxes = document.querySelectorAll('input[name="selectedRows"]:checked');
    
    checkboxes.forEach((checkbox) => {
        const index = parseInt(checkbox.value);
        deleteRow(index);
    });

    // Update the visibility of the delete button after deletion
    updateDeleteButtonVisibility();
}

function deleteRow(index) {
    event.preventDefault();
    // Find the row to delete
    var row = document.getElementById('row_' + index);
    
    // Remove the row from the table
    row.parentNode.removeChild(row);
    extractDataFrame();

}

function updateDeleteButtonVisibility() {
    const checkboxes = document.querySelectorAll('input[name="selectedRows"]');
    const deleteButton = document.getElementById('delete-selected');
    let anySelected = false;

    checkboxes.forEach((checkbox) => {
        if (checkbox.checked) {
            anySelected = true;
            return;
        }
    });

    if (anySelected) {
        deleteButton.style.display = 'block';
    } else {
        deleteButton.style.display = 'none';
    }
}


function updateTable(data) {
    const tableBody = document.querySelector('#dataframe tbody');
    tableBody.innerHTML = ''; // Clear the existing table rows
    
    // Iterate over the data and add new rows to the table
    data.forEach((row, index) => 
    {
        const tr = document.createElement('tr');
        tr.setAttribute('id', ('row_' + index));

    // <td><!-- Checkbox for each row -->
    // <input type="checkbox" id="checkbox_{{ index }}" name="selectedRows" value="{{ index }}" onclick="updateDeleteButtonVisibility()">
    // <label class="checkbox-label" for="checkbox_{{ index }}"></label>
    // </td> 

        // Create checkbox for each row
        const checkboxTd = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'selectedRows';
        checkbox.setAttribute('id', ('checkbox_' + index));
        checkbox.value = index;
        checkbox.onclick = updateDeleteButtonVisibility; // Call the updateDeleteButtonVisibility function when checkbox is clicked
        const labelcheckbox = document.createElement('label');
        labelcheckbox.className = 'checkbox-label';
        labelcheckbox.setAttribute('for', ('checkbox_' + index));

        checkboxTd.appendChild(checkbox);
        checkboxTd.appendChild(labelcheckbox);
        tr.appendChild(checkboxTd);

        // Create editable cells for data
        Object.values(row).forEach(value => {
            const td = document.createElement('td');
            td.setAttribute('contenteditable', true); // Make the cell editable
            td.classList.add('editable'); // Add the 'editable' class
            td.textContent = value;
            tr.appendChild(td);
        });

        // Create buttons for regeneration and deletion
        const regenerateBtn = document.createElement('button');
        regenerateBtn.textContent = 'Regenerate';
        regenerateBtn.className = 'regenerate-btn';
        regenerateBtn.onclick = () => regenerateRow(index); // Bind the onclick event to the regenerateRow function

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'delete-btn';
        deleteBtn.onclick = () => deleteRow(index); // Bind the onclick event to the deleteRow function

        // Create a cell for the buttons and append it to the table row
        const tdButton = document.createElement('td');
        tdButton.appendChild(regenerateBtn);
        tdButton.appendChild(deleteBtn);
        tr.appendChild(tdButton);

        // Append the table row to the table body
        tableBody.appendChild(tr);
    });
}


function toggleForm() {
    var form = document.getElementById('review-examples-html');
    var button = document.getElementById('toggleButton');
    if (form.style.display === 'none') {
        form.style.display = 'block'; // Uncollapse the form
        button.innerHTML = 'Hide Examples &uarr;'; // Change button text to hide and show up arrow
    } else {
        form.style.display = 'none'; // Collapse the form
        button.innerHTML = 'Show Examples &darr;'; // Change button text to show and show down arrow
    }
}