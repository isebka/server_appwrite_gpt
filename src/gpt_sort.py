from g4f.client import Client
import os,json
from .excel import excel_manager

file_path = os.environ.get("file_path")

def gpt_response(text, user_id):
    if not text or not user_id:
        return None
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    modified_content = content.replace('[ТЕКСТ_ЗДЕСЬ]', text)

    client = Client()
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": modified_content}],
        web_search=False
    )
    # Parse the string content as JSON
    content_str = response.choices[0].message.content
    try:
        content_dict = json.loads(content_str)  # This converts the string to a dict
        excel_manager(content_dict, user_id)  # Now pass the dict to your function
    except json.JSONDecodeError:
        print("Error: The response content is not valid JSON:", content_str)