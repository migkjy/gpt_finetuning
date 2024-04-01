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

def list_to_df(prev_examples):
    """
    Convert a list of examples into a DataFrame containing prompts and responses.

    Args:
    - prev_examples (list): List of examples in string format.

    Returns:
    - DataFrame: DataFrame containing prompts and responses.
    """
    # Initialize lists to store prompts and responses
    prompts = []
    responses = []

    # Iterate through each example in the list
    for example in prev_examples:
        #print(f"[!] Converting Example: {example}")
        try:
            # Split the example string into prompt and response using '-----------' as delimiter
            split_example = example.split('-----------')
            
            # Extract and append the prompt (index 1) and response (index 3) to respective lists
            prompt = split_example[1].strip()
            response = split_example[3].strip()
            prompts.append(prompt)  # Prompt
            responses.append(response)  # Response
            #print(f"[+] Example Added Successfully. Prompt: {prompt}. Response: {response}")
        except:
            #print(f"Error while converting example: {example}")
            # If an error occurs during parsing, ignore and continue to the next example
            pass

    # Create a DataFrame from the lists of prompts and responses
    df = pd.DataFrame({
        'prompt': prompts,
        'response': responses
    })

    # Remove duplicates based on the first column (prompts)
    #df = df.drop_duplicates(subset=df.columns[0])

    # Return the DataFrame
    return df


def df_to_list(df):
    """
    Convert a DataFrame containing prompts and responses into a list of example strings.

    Args:
    - df (DataFrame): DataFrame containing prompts and responses.

    Returns:
    - list: List of example strings.
    """
    # Initialize an empty list to store example strings
    examples_list = []

    # Iterate through each row in the DataFrame
    for index, row in df.iterrows():
        # Extract prompt and response from the current row
        prompt = row.iloc[0]  # Prompt is located in the first column
        response = row.iloc[1]  # Response is located in the second column

        # Format the example string using prompt and response
        example_string = f"""```\nprompt\n-----------\n{prompt}\n-----------\n\nresponse\n-----------{response}\n-----------\n```"""

        # Append the formatted example string to the list
        examples_list.append(example_string)

    # Return the list of example strings
    return examples_list


def regenerate_example(index, prev_examples, temperature):
    """
    Regenerate an example at the specified index.

    Args:
    - index (int): Index of the example to regenerate.
    - prev_examples (list): List of examples in string format.
    - temperature (float): The temperature parameter controlling the randomness of the generated example.

    Returns:
    - list: Updated list of examples after regenerating the example at the specified index.
    """
    try:
        print(f"Regenerating example {index}..")
        temp_examples = prev_examples[:index] + prev_examples[index + 1:]

        df = list_to_df(prev_examples)
        prompt = df.iloc[index, 0]

        prev_examples[index] = generate_example(prompt, temp_examples, temperature)
        return prev_examples
    except Exception as e:
        print(f"-------\nError while regenerating example {index}: {e}\nprev_examples:{prev_examples}\nlist_to_df:{df}\n---------\n")
        return prev_examples

@retry(stop=stop_after_attempt(N_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=70))
def generate_example(prompt, prev_examples, temperature=.5, model='gpt-3.5-turbo'):
    """
    Generate an example based on a prompt, previous examples, and a temperature parameter.

    Args:
    - prompt (str): The prompt for generating the example.
    - prev_examples (list): List of previous examples in string format.
    - temperature (float, optional): The temperature parameter controlling the randomness of the generated example. 
                                     Defaults to 0.5.

    Returns:
    - str: The generated example.
    """

    messages=[
        {
            "role": "system",
            "content": f"You are generating data which will be used to train a machine learning model.\n\nYou will be given a high-level description of the model we want to train, and from that, you will generate data samples, each with a prompt/response pair.\n\nYou will do so in this format:\n```\nprompt\n-----------\n$prompt_goes_here\n-----------\n\nresponse\n-----------\n$response_goes_here\n-----------\n```\n\nOnly one prompt/response pair should be generated per turn.\n\nFor each turn, make the example slightly more complex than the last, while ensuring diversity.\n\nMake sure your samples are unique and diverse, yet high-quality and complex enough to train a well-performing model.\n\nHere is the type of model we want to train:\n`{prompt}`"
        }
    ]

    #Convert the df to list format before passing to GPT
    #prev_examples = df_to_list(prev_examples_df)
    if len(prev_examples) > 0:
        #It keeps the length of prev_examples sent to gpt at 8. Randomizing them each time.
        #ensuring diversity in the selection
        if len(prev_examples) > 8:
            prev_examples = random.sample(prev_examples, 8)
        for example in prev_examples:
            messages.append({
                "role": "assistant",
                "content": example
            })

    #
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=1000,
    )
    str_response = response.choices[0].message['content']
    item = list_to_df([str_response])
    try:
        print(f"[*] Prompt: {item.iloc[0, 0]}\n[~] Response: {item.iloc[0, 1]}")
    except:
        return generate_example(prompt, prev_examples, temperature)
    #print(f"RAW RESPONSE:\n{str_response}\n")
    #return {'prompt': item.iloc[0, 0], 'response': item.iloc[0, 1]}
    return str_response

def generate_system_message(prompt):
    """
    Generate a system message based on a given prompt.

    Args:
    - prompt (str): The prompt for generating the system message.

    Returns:
    - str: The generated system message.
    """
    # Create a system message using the OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Model used for generating the message
        messages=[
            {
                "role": "system",
                "content": "You will be given a high-level description of the model we are training, and from that, "
                           "you will generate a simple system prompt for that model to use. Remember, you are not "
                           "generating the system message for data generation -- you are generating the system message "
                           "to use for inference. A good format to follow is `Given $INPUT_DATA, you will "
                           "$WHAT_THE_MODEL_SHOULD_DO.`.\n\nMake it as concise as possible. Include nothing but the "
                           "system prompt in your response.\n\nFor example, never write: `$SYSTEM_PROMPT_HERE`.\n\n"
                           "It should be like: `$SYSTEM_PROMPT_HERE`."
            },
            {
                "role": "user",
                "content": prompt.strip(),  # Prompt provided by the user
            }
        ],
        temperature=temperature,  # Temperature parameter controlling randomness of generated text
        max_tokens=500,  # Maximum number of tokens (words) in the generated text
    )

    # Return the content of the generated system message
    return response.choices[0].message['content']

def save_training_file_as_jsonl(training_examples):
    """
    Save training examples to a JSON Lines (.jsonl) file.

    Args:
    - training_examples (list): List of training examples in dictionary format.

    Raises:
    - TypeError: If training_examples is not a list.
    - IOError: If an error occurs while writing to the file.

    Returns:
    - None
    """
    try:
        # Check if training_examples is a list
        if not isinstance(training_examples, list):
            raise TypeError("Training examples must be provided as a list.")

        # Open the file in write mode
        with open('training_examples.jsonl', 'w') as f:
            # Write each training example as a JSON object on a separate line
            for example in training_examples:
                f.write(json.dumps(example) + '\n')

    except TypeError as e:
        # Handle TypeError
        print(f"Error: {e}")

    except IOError as e:
        # Handle IOError
        print(f"Error: {e}")

def create_json_training_examples(training_df, system_message):
    """
    Create training examples in the format required for fine-tuning GPT-3.5-turbo.

    Args:
    - training_df (DataFrame): The DataFrame containing training data with 'prompt' and 'response' columns.

    Returns:
    - list: List of training examples, each formatted as a dictionary.
    """
    # Initialize list to store training examples
    training_examples = []

    # Create training examples in the format required for GPT-3.5-turbo fine-tuning
    for index, row in training_df.iterrows():
        # Create a training example dictionary with 'messages' list containing system, user, and assistant messages
        training_example = {
            "messages": [
                {"role": "system", "content": system_message.strip()},  # System message
                {"role": "user", "content": row['prompt']},  # User prompt
                {"role": "assistant", "content": row['response']}  # Assistant response
            ]
        }
        # Append the training example to the list of training examples
        training_examples.append(training_example)

    # Return the list of training examples
    return training_examples

def upload_training_examples(training_examples):
    """
    Uploads training examples to OpenAI for fine-tuning.

    Args:
    - training_examples (list): List of training examples in dictionary format.

    Returns:
    - str: ID of the uploaded file.
    """
    # Create an in-memory text stream
    file_like_object = io.StringIO()

    # Write the training examples as JSON lines to the in-memory file
    for example in training_examples:
        file_like_object.write(json.dumps(example) + '\n')

    # Move the cursor of the file-like object to the start
    file_like_object.seek(0)

    # Upload the file with OpenAI API
    response = openai.File.create(
        file=file_like_object,
        purpose='fine-tune'
    )

    # Retrieve the ID of the uploaded file
    file_id = response.id

    # Close the file-like object
    file_like_object.close()

    # Return the ID of the uploaded file
    return file_id


def generate_examples(apiKey, prompt, temperature, number_of_examples, task_status, df, model):
    openai.api_key = apiKey
    # Generate examples
    prev_examples = []
    for i in range(number_of_examples):
        #print(f'Generating example [{i}/{number_of_examples}]')
        task_status({'message': f'Generating example [{i}/{number_of_examples}]'})
        example = generate_example(prompt, prev_examples, temperature, model)
        prev_examples.append(example)

    system_message = generate_system_message(prompt)

    
    df_data = list_to_df(prev_examples)
    #print(f"Prev Examples: {prev_examples}")
    if len(df) > 0:
        df_data = pd.concat([df, df_data], ignore_index=True)

    json_data = df_data.to_json(orient='records')

    #print(f"Examples df: {df_data}")
    status_dict = {'message': f'{number_of_examples} Examples generated successfully.\nTotal Generated: {len(df_data)}', 'prompt_used': prompt,'example_data': json_data, 'system_message': system_message,
                 }
    task_status(status_dict)
    print(status_dict)


def train(apiKey, prompt, temperature, number_of_examples, task_status):
    global system_message
    openai.api_key = apiKey

    # Generate examples
    prev_examples = generate_examples(apiKey, prompt, temperature, number_of_examples, task_status)


    system_message = generate_system_message(prompt)
    while False:
        #
        #input(f"Previous Examples:\n{'\n'.join(prev_examples)}")
        #for index, item in enumerate(prev_examples):
        #    print(f"{index}: {item}")
        print(list_to_df(prev_examples))
        x = input("Enter index of example to regenerate, otherwise hit enter to continue: ")
        if x == "":
            break
        else:
            #ON WEBPAGE: I will display the df using
            df = list_to_df(prev_examples)
            #To send it to function regenerate_example, I will use:
            prev_examples = df_to_list(df)
            #input(f"Prev Examples after converting back to list:\n{prev_examples}")
            # Now I can send it back after the user edits it on webpage, using 
            x_int = int(x)
            prev_examples = regenerate_example(x_int, prev_examples, temperature)

    

    print(f'The system message is: `{system_message}`. Feel free to re-run this cell if you want a better result.')

    df = list_to_df(prev_examples)
    json_data = df.to_json(orient='records')
    print(json_data)
    input("Exit")
    #df.to_csv('df_for_test.csv', index=False)
    
    # print('There are ' + str(len(df)) + ' successfully-generated examples.')
    # task_status({'message': 'There are ' + str(len(df)) + ' successfully-generated examples.'})

    training_examples = create_json_training_examples(df, system_message)

    save_training_file_as_jsonl(training_examples)

    file_id = upload_training_examples(training_examples)

    task_status({'message': f'Job ID: {file_id}', 'modelId': file_id, 'systemMessage': system_message})

#def task_status(dic):
#    print(dic)

def fine_tune(file_id, set_status, SYSTEM_MESSAGE):
    global system_message
    system_message = SYSTEM_MESSAGE
    job = openai.FineTuningJob.create(training_file=file_id, model="gpt-3.5-turbo")

    job_id = job.id

    print(f"Got Job Id: {job_id}")
    #task_status({'message': f'Got job id {job_id}'})

    while True:
        js_events = openai.FineTuningJob.list_events(id=job_id, limit=10)
        datas = js_events.get("data")
        frst_message = datas[0].get("message")
        print(frst_message)
        set_status({"message": frst_message})

        if frst_message == "The job has successfully completed":
            break
        time.sleep(60)

    model_name_pre_object = openai.FineTuningJob.retrieve(job_id)
    model_name = model_name_pre_object.fine_tuned_model
    print(model_name)
    set_status({"message": f"[*] Fine Tuning Completed!\nModel Name: {model_name}", "modelName": model_name, "systemMessage": system_message,
                 "apiKey": openai.api_key})


#openai.api_key = apiKey
#files = openai.File.list()
examples_list = ['```\nprompt\n-----------\nCreate a comprehensive emergency response plan for your office, including evacuation routes, safety procedures, and emergency contacts.\n-----------\n\nresponse\n-----------\nIn the event of an emergency in our office, all employees should immediately evacuate the building using the nearest exit. Once outside, everyone should gather at the designated assembly point in the parking lot. The safety team will conduct a head count to ensure everyone is accounted for. Emergency contacts should be posted in visible areas throughout the office, including numbers for local emergency services, management, and designated first aid responders.\n-----------', '```\nprompt\n-----------\nCreate a comprehensive emergency response plan for your office, including evacuation routes, safety procedures, and emergency contacts.\n-----------\n\nresponse\n-----------\nIn addition to the evacuation routes and safety procedures, our office emergency response plan should include specific roles and responsibilities for designated employees during an emergency. These roles may include a floor warden responsible for ensuring all employees on their floor evacuate safely, a first aid responder trained to provide medical assistance if needed, and a communication coordinator responsible for relaying updates to employees and emergency services.\n-----------', '```\nprompt\n-----------\nCreate a comprehensive emergency response plan for your office, including evacuation routes, safety procedures, and emergency contacts.\n-----------\n\nresponse\n-----------\nOur office emergency response plan should also detail procedures for different types of emergencies, such as fires, earthquakes, or medical emergencies. Employees should be trained on how to respond to each type of emergency, including when to evacuate, when to shelter in place, and how to assist others in need. Regular drills and training sessions should be conducted to ensure everyone is prepared and knows their role in an emergency situation.\n-----------']
#df_data = list_to_df(examples_list)
#print(df_data)

#generate_examples(apiKey, prompt, temperature, number_of_examples, task_status)
#train(apiKey, prompt, temperature, number_of_examples, task_status)