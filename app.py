from flask import Flask, jsonify,request, render_template, redirect, url_for
import threading
import time
from gpt_functions import generate_examples, fine_tune
from gpt_functions import regenerate_example, list_to_df, df_to_list, generate_system_message, create_json_training_examples, upload_training_examples
from bs4 import BeautifulSoup
import openai
import pandas as pd
import os
import uuid
import json
import sys

app = Flask(__name__)

df = pd.DataFrame()

# Simulated task status
task_status = {"message": "[!] Loading..."}

def set_status(status):
    global task_status
    task_status = status

def long_running_task2():
    global task_status
    #task_status = {"message": "Training started successfully!"}
    for i in range(0,20):
        task_status = {"message": f"test {i}!"}
        time.sleep(1)  
    task_status = {"message": "Training finished!"}
    task_status = {"message": "[*] Model ID: XXXXXXX", "modelId": "XXXXXXX"}

def call_generate_examples(apiKey, prompt, temperature, number_of_examples, model):
    global task_status, df
    generate_examples(apiKey, prompt, temperature, number_of_examples, set_status, df, model)

def fine_tune_thread(job_id):
    global task_status, SYSTEM_MESSAGE
    fine_tune(job_id, set_status, SYSTEM_MESSAGE)

@app.route('/')
def index():
    # global df
    # if len(df) > 0:
    #     showClear = True
    # else:
    #     showClear = False

    return render_template('index.html')


@app.route('/generate_examples', methods=['POST'])
def api_generate_examples():
    # Extract parameters from the request
    data = request.get_json()
    print("Generating Examples with parameters:", data)
    apiKey = data.get("apiKey")
    model = data.get("model")
    prompt = data.get("prompt")
    temp = data.get("temperature")
    examples = data.get("numExamples")

    threading.Thread(target=call_generate_examples, args=[apiKey, prompt, temp, examples, model]).start()
    return jsonify({"message": "Training started!"})

def html_table_to_df(html_content):
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the table element
    table = soup.find('table')

    # Initialize lists to store column names and data
    columns = []
    data = []

    # Extract column names from the table header (th) elements
    for th in table.find('thead').find_all('th'):
        columns.append(th.text.strip())

    # Extract data from the table rows (tr) and cells (td)
    for tr in table.find('tbody').find_all('tr'):
        row = {}
        for i, td in enumerate(tr.find_all('td')):
            row[columns[i]] = td.text.strip()
        data.append(row)

    # Create a DataFrame from the extracted data
    df_html = pd.DataFrame(data)

    # Drop the last column (Action Column)
    df_html = df_html.iloc[:, :-1]

    # Change all column names to lowercase
    df_html.columns = [column.lower() for column in df_html.columns]

    # Return the DataFrame as JSON data
    #print(df_html)
    #df = df_html
    return df_html


SYSTEM_MESSAGE = ""
@app.route('/confirm_training_data', methods=['POST'])
def upload_training_data():
    global SYSTEM_MESSAGE
    html_content = request.json['html_content']
    system_message = request.json['system_message']
    SYSTEM_MESSAGE = system_message
    set_status({'message': 'Uploading Training Data..'})
    training_df = html_table_to_df(html_content)
    list_of_trainings = create_json_training_examples(training_df, system_message)
    file_id = upload_training_examples(list_of_trainings)

    set_status({'message': f'Job ID: {file_id}', 'modelId': file_id})
    return jsonify({'message': f'Job ID: {file_id}', 'modelId': file_id})


@app.route('/start_fine_tuning', methods=['POST'])
def start_fine_tuning():
    set_status({"message": f"Starting fine-tuning.."})
    # Extract parameNoters from the request
    data = request.get_json()
    print("Starting fine-tuning with parameters:", data)

    job_id = data.get("modelId")
    threading.Thread(target=fine_tune_thread, args=[job_id]).start()
    
    return jsonify({"message": "Fine-tuning started!"})


@app.route('/get_status', methods=['GET'])
def get_status():
    return jsonify(task_status)

@app.route('/chat')
def chat():
    model = request.args.get('model')
    apiKey = request.args.get('apiKey')
    systemMessage = request.args.get('systemMessage')
    return render_template('chatting.html', model=model, apiKey=apiKey, systemMessage=systemMessage)



def save_temp_training_data(training_data_list):
    # Directory to save the file
    directory = 'files'

    # Create the directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Generate a random filename
    filename = str(uuid.uuid4()) + '.csv'

    # Save the DataFrame to a CSV file
    file_path = os.path.join(directory, filename)

    df = pd.DataFrame(training_data_list)

    df.to_csv(file_path, index=False)
    return file_path

@app.route('/edit_examples', methods=['POST'])
def edit_examples():
    payload = request.json
    #print(f"Payload Recieved:\n{payload}")
    if request.method == 'POST':
        
        html_content = request.json['html_content']
        df = html_table_to_df(html_content)
        # Assuming you're sending the DataFrame as a JSON object
        jsonData = request.get_json()
        df_data = jsonData.get('training_data')
        sys_message = jsonData.get('system_message')
        # Check if training_data is a string
        if isinstance(df_data, str):
            # Convert string to list of dictionaries
            training_data_list = json.loads(df_data)
        elif isinstance(df_data, list):
            # If it's already a list, no need for conversion
            training_data_list = df_data

        #filename = save_temp_training_data(training_data_list)
        #return jsonify({'example_data': training_data_list})
        #return redirect(url_for('view_examples', filename=filename))
        df = pd.DataFrame(training_data_list)
        #print(df)
        #return jsonify({'example_data': training_data_list})
        #return df.to_html()

        return render_template('review.html', dataframe=df, system_message=sys_message)

@app.route('/regenerate/<int:index>', methods=['POST'])
def regenerate(index):
    global df
    try:
        # Get the HTML content of the table from the request
        html_content = request.json['html_content']

        df_html = extract_df_from_htmlcontent(html_content)

        prev_examples = df_to_list(df_html)

        print(f"Regenerating EXAMPLE: {index}\nLOG:\nprev_examples: {prev_examples}\ndf:{df}\n=======")
        # Call the regenerate_df function to regenerate the DataFrame
        df = list_to_df(regenerate_example(index, prev_examples, 0.4))
        print(f"New DF:\n{df}")
        # Return the regenerated DataFrame as JSON response
        return jsonify(df.to_dict(orient='records')), 200
    except IndexError as e:
        # If the index is out of range, return an error message
        print("Error: ", e)
        return jsonify({'message': str(e)}), 404
    

@app.route('/get_system_message', methods=['GET'])
def get_system_message():
    api_key = request.args.get('apiKey')
    model = request.args.get('model')
    prompt = request.args.get('prompt')
    system_message = generate_system_message(prompt)
    return jsonify({'system_message': system_message})


def extract_df_from_htmlcontent(html_content):
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the table element
    table = soup.find('table')

    # Initialize lists to store column names and data
    columns = []
    data = []

    # Extract column names from the table header (th) elements
    for th in table.find('thead').find_all('th'):
        columns.append(th.text.strip())

    # Extract data from the table rows (tr) and cells (td)
    for tr in table.find('tbody').find_all('tr'):
        row = {}
        for i, td in enumerate(tr.find_all('td')):
            row[columns[i]] = td.text.strip()
        data.append(row)

    # Create a DataFrame from the extracted data
    df_html = pd.DataFrame(data)

    # Drop the last column (Action Column)
    #df_html = df_html.iloc[:, :-1]

    # Change all column names to lowercase
    df_html.columns = [column.lower() for column in df_html.columns]

    # Replace column names
    df_html.rename(columns={"user": "prompt", "assistant": "response"}, inplace=True)

    # Drop all other columns except "prompt" and "response"
    df_html = df_html[["prompt", "response"]]
    return df_html

@app.route('/extract_dataframe', methods=['POST'])
def extract_dataframe():
    global df
    try:
        # Get the HTML content of the table from the request
        html_content = request.json['html_content']

        df_html = extract_df_from_htmlcontent(html_content)

        # Return the DataFrame as JSON data
        print(f"Extracted df:\n-----\n{df_html}\n------\n")
        df = df_html.copy()
        return jsonify(df.to_dict(orient='records')), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500
    


@app.route('/view_examples', methods=['GET'])
def view_examples():
    if request.method == 'GET':
        filename = request.args.get('filename')
        df = pd.read_csv(filename)

    # Use filename to load the data or render the template
    # Example: df = load_data(filename)
    # Then render the template with df
    
    return render_template('review.html', dataframe=df)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    prompt = data['prompt']
    model = data['model']
    apiKey = data['apiKey']
    systemMessage = data['systemMessage']
    print(f"api-chat end point with data: {data}")
    openai.api_key = apiKey
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": systemMessage},
                {"role": "user", "content": prompt},
            ]
        )
        message_content = response.choices[0].message['content'].strip()
        print(message_content)
        return jsonify({'response': message_content})
    except Exception as e:
        error_message = f"An error occurred: {e}"
        print(error_message)
        return jsonify({'error': error_message}), 500

@app.route('/clear_progress', methods=['POST'])
def clear_progress():
    global df, SYSTEM_MESSAGE
    if request.method == 'POST':
        # Restart the Flask app
        #os.execl(sys.executable, sys.executable, *sys.argv)
        set_status({"message": "Session cleared."})
        df = pd.DataFrame()
        SYSTEM_MESSAGE = ""
        return redirect(url_for('index'))
    else:
        return 'Method not allowed', 405

if __name__ == '__main__':
    app.run(debug=True)
