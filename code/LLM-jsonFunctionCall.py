from dotenv import load_dotenv
import os  
from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel
import json


load_dotenv()

azure_client = AzureOpenAI(  
    azure_endpoint=os.getenv("AZURE_ENDPOINT_URL"),  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version="2024-12-01-preview",  
)  

deepseek_client = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API")
)

print("s")

# Normal Chat Process
response = azure_client.chat.completions.create(
    model="gpt-4o-mini",
    messages= [
        {"role": "system", "content": "Your are a helpful assistant."},
        {"role": "user", "content": "How many Apple can you eat everyday?"},
        {"role": "assistant", "content": "I can eat 5 apple per day."},
        {"role": "user", "content": "What I just ask you about?"},
    ],
    temperature=1,
    top_p=1,
)

response


# Json Response
response = azure_client.chat.completions.create(
    model="gpt-4o-mini",
    messages= [
        {"role": "system", "content": "Extract the event information in json formate."},
        {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
    ],
    response_format={"type": "json_object"}, 
)

response

# Structure Output
class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

response = azure_client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Extract the event information."},
        {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
    ],
    response_format=CalendarEvent,
)

response


# Function Calling
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for provided coordinates in celsius.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"}
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

messages = [{"role": "user", "content": "What's the weather like in Paris today?"}]

completion = azure_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

tool_call = completion.choices[0].message.tool_calls[0]
args = json.loads(tool_call.function.arguments)

def get_weather(a, b):
    return "14°C (57.2°F)"

result = get_weather(args["latitude"], args["longitude"])

messages.append(completion.choices[0].message)
messages.append({                               
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": str(result)
})

completion_2 = azure_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

completion_2



# Streaming
response = deepseek_client.chat.completions.create(
    model="deepseek-reasoner",
    messages= [
        {"role": "system", "content": "Extract the event information."},
        {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
    ],
    stream=True
)

for chunk in response:
    if len(chunk.choices) > 0:
        delta = chunk.choices[0].delta
        if delta.content:
            print(chunk.choices[0].delta.content, end="")
            # yield chunk.choices[0].delta.content


