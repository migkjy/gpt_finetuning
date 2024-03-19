import os
import openai
import random
from tenacity import retry, stop_after_attempt, wait_exponential
import json
import pandas as pd
import time
import io


N_RETRIES = 3

prompt = "A model that takes in a puzzle-like reasoning-heavy question in English, and responds with a well-reasoned, step-by-step thought out response in Arabic."
temperature = .4
number_of_examples = 10
system_message = ""

def train(apiKey, prompt, temperature, number_of_examples, task_status):
    global system_message
    openai.api_key = apiKey
    @retry(stop=stop_after_attempt(N_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=70))
    def generate_example(prompt, prev_examples, temperature=.5):
        messages=[
            {
                "role": "system",
                "content": f"You are generating data which will be used to train a machine learning model.\n\nYou will be given a high-level description of the model we want to train, and from that, you will generate data samples, each with a prompt/response pair.\n\nYou will do so in this format:\n```\nprompt\n-----------\n$prompt_goes_here\n-----------\n\nresponse\n-----------\n$response_goes_here\n-----------\n```\n\nOnly one prompt/response pair should be generated per turn.\n\nFor each turn, make the example slightly more complex than the last, while ensuring diversity.\n\nMake sure your samples are unique and diverse, yet high-quality and complex enough to train a well-performing model.\n\nHere is the type of model we want to train:\n`{prompt}`"
            }
        ]

        if len(prev_examples) > 0:
            if len(prev_examples) > 8:
                prev_examples = random.sample(prev_examples, 8)
            for example in prev_examples:
                messages.append({
                    "role": "assistant",
                    "content": example
                })

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=temperature,
            max_tokens=1000,
        )

        return response.choices[0].message['content']

    # Generate examples
    prev_examples = []
    for i in range(number_of_examples):
        print(f'Generating example [{i}/{number_of_examples}]')
        task_status({'message': f'Generating example [{i}/{number_of_examples}]'})
        example = generate_example(prompt, prev_examples, temperature)
        prev_examples.append(example)

    print(prev_examples)

    def generate_system_message(prompt):

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
            {
                "role": "system",
                "content": "You will be given a high-level description of the model we are training, and from that, you will generate a simple system prompt for that model to use. Remember, you are not generating the system message for data generation -- you are generating the system message to use for inference. A good format to follow is `Given $INPUT_DATA, you will $WHAT_THE_MODEL_SHOULD_DO.`.\n\nMake it as concise as possible. Include nothing but the system prompt in your response.\n\nFor example, never write: `\"$SYSTEM_PROMPT_HERE\"`.\n\nIt should be like: `$SYSTEM_PROMPT_HERE`."
            },
            {
                "role": "user",
                "content": prompt.strip(),
            }
            ],
            temperature=temperature,
            max_tokens=500,
        )

        return response.choices[0].message['content']

    system_message = generate_system_message(prompt)

    print(f'The system message is: `{system_message}`. Feel free to re-run this cell if you want a better result.')
    # Initialize lists to store prompts and responses
    prompts = []
    responses = []

    # Parse out prompts and responses from examples
    for example in prev_examples:
        try:
            split_example = example.split('-----------')
            prompts.append(split_example[1].strip())
            responses.append(split_example[3].strip())
        except:
            pass

    # Create a DataFrame
    df = pd.DataFrame({
        'prompt': prompts,
        'response': responses
    })

    # Remove duplicates
    df = df.drop_duplicates()

    print('There are ' + str(len(df)) + ' successfully-generated examples.')
    task_status({'message': 'There are ' + str(len(df)) + ' successfully-generated examples.'})
    # Initialize list to store training examples
    training_examples = []

    # Create training examples in the format required for GPT-3.5 fine-tuning
    for index, row in df.iterrows():
        training_example = {
            "messages": [
                {"role": "system", "content": system_message.strip()},
                {"role": "user", "content": row['prompt']},
                {"role": "assistant", "content": row['response']}
            ]
        }
        training_examples.append(training_example)

    # OLD METHOD OF STORING ACTUAL JSONL FILE
        # Save training examples to a .jsonl file
        #with open('training_examples.jsonl', 'w') as f:
        #    for example in training_examples:
        #        f.write(json.dumps(example) + '\n')

        #file_id = openai.File.create(
        #    file=open("training_examples.jsonl", "rb"),
        #    purpose='fine-tune'
        #    ).id

    # Create an in-memory text stream
    file_like_object = io.StringIO()
    # Write the JSON lines to the in-memory file
    for example in training_examples:
        file_like_object.write(json.dumps(example) + '\n')
    # Move the cursor of the file-like object to the start
    file_like_object.seek(0)

    # Create the file with OpenAI API
    response = openai.File.create(
        file=file_like_object,
        purpose='fine-tune'
    )

    file_id = response.id
    
    file_like_object.close()

    task_status({'message': f'Job ID: {file_id}', 'modelId': file_id, 'systemMessage': system_message})

def fine_tune(file_id, task_status):
    job = openai.FineTuningJob.create(training_file=file_id, model="gpt-3.5-turbo")

    job_id = job.id

    print(f"Got Job Id: {job_id}")
    #task_status({'message': f'Got job id {job_id}'})

    while True:
        js_events = openai.FineTuningJob.list_events(id=job_id, limit=10)
        datas = js_events.get("data")
        frst_message = datas[0].get("message")
        print(frst_message)
        task_status({"message": frst_message})

        if frst_message == "The job has successfully completed":
            break
        time.sleep(60)

    model_name_pre_object = openai.FineTuningJob.retrieve(job_id)
    model_name = model_name_pre_object.fine_tuned_model
    print(model_name)
    task_status({"message": f"[*] Fine Tuning Completed!\nModel Name: {model_name}", "modelName": model_name, "systemMessage": system_message,
                 "apiKey": openai.api_key})