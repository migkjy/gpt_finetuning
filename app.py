from flask import Flask, jsonify,request, render_template
import threading
import time
from gpt_testing import train, fine_tune
import openai

app = Flask(__name__)

# Simulated task status
task_status = {"message": "Ready to start training."}

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

def train_thread(apiKey, prompt, temperature, number_of_examples):
    global task_status
    train(apiKey, prompt, temperature, number_of_examples, set_status)

def fine_tune_thread(job_id):
    global task_status
    fine_tune(job_id, set_status)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_training', methods=['POST'])
def start_training():
    # Extract parameters from the request
    data = request.get_json()
    print("Starting training with parameters:", data)
    apiKey = data.get("apiKey")
    prompt = data.get("prompt")
    temp = data.get("temperature")
    examples = data.get("numExamples")
    # Simulate processing time
    # Implement your training logic here
    threading.Thread(target=train_thread, args=[apiKey, prompt, temp, examples]).start()
    return jsonify({"message": "Training started!"})

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


if __name__ == '__main__':
    app.run(debug=True)
