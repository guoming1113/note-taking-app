# import libraries
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() # Loads environment variables from .env
token = os.environ["GITHUB_TOKEN"]
endpoint = "https://models.github.ai/inference"
model = "openai/gpt-4.1-mini"
# A function to call an LLM model and return the response
def call_llm_model(model, messages, temperature=1.0, top_p=1.0): 
    client = OpenAI(base_url=endpoint,api_key=token)
    response = client.chat.completions.create(
        messages=messages,
        temperature=temperature, 
        top_p=top_p, 
        model=model)
    return response.choices[0].message.content

# A function to translate to target language
def translate_note(note_content, target_language):
    messages = [
        {
            "role": "system",
            "content": f"You are a translator. Translate the following content into {target_language} accurately. Keep the structure of the content unchanged."
        },
        {
            "role": "user",
            "content": note_content
        }
    ]
    return call_llm_model(model, messages)

def process_user_notes(language, user_input):
    system_prompt = '''Extract the user's notes into the following structured fields:
    1. Title: A concise title of the notes less than 5 words
    2. Notes: The notes based on user input written in full sentences.
    3. Tags (A list): At most 3 Keywords or tags that categorize the content of the notes.
    4. Date (optional): Extract date from input, format as YYYY - MM - DD. If no date, omit this field.
    5. Time (optional): Extract time from input, format as HH:MM. If no time, omit this field.
    Output in JSON format without ```json. Output title and notes in the language: {lang}.
    Example:
    Input: "Badminton tmr 5pm @polyu"
    Output:
    {{
    "Title": "Badminton at PolyU",
    "Notes": "Remember to play badminton at 5pm tomorrow at PolyU.",
    "Tags": ["badminton", "sports"]
    "Date": "tomorrow,
    "Time": "17:00"
    }}'''
    system_prompt_filled = system_prompt.format(lang = language)
    messages = [
        {"role": "system", "content": system_prompt_filled},
        {"role": "user", "content": user_input}
    ]
    response_content = call_llm_model(model, messages)
    import json
    return json.loads(response_content)

# if __name__ == "__main__":
#     result1 = process_user_notes("Chinese", "Get up tomorrow 7am")
#     print(result1)
#     result2 = process_user_notes("English", "Lunch 12:30pm tomorrow")
#     print(result2)