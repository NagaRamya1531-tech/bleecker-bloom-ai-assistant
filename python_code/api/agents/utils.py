import json
import re


def get_chatbot_response(client,model_name,messages,temperature=0,json_mode=False,json_schema=None):
    input_messages = []
    for message in messages:
        input_messages.append({"role": message["role"], "content": message["content"]})

    # JSON mode constrains the model to emit valid JSON (OpenAI, Ollama, and vLLM support it).
    # A JSON schema goes further: the server forces the output to match it (OpenAI and vLLM).
    extra_args = {"response_format": {"type": "json_object"}} if json_mode else {}
    if json_schema:
        extra_args = {"response_format": {"type": "json_schema", "json_schema": json_schema}}
    response = client.chat.completions.create(
        model=model_name,
        messages=input_messages,
        temperature=temperature,
        top_p=0.8,
        max_tokens=2000,
        **extra_args,
    ).choices[0].message.content

    return response

def parse_json_output(text):
    """Parse a model's JSON reply, tolerating ```json fences and surrounding prose. Returns {} on failure."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}

def get_embedding(embedding_client,model_name,text_input):
    output = embedding_client.embeddings.create(input = text_input,model=model_name)
    
    embedings = []
    for embedding_object in output.data:
        embedings.append(embedding_object.embedding)

    return embedings

def double_check_json_output(client,model_name,json_string):
    prompt = f""" You will check this json string and correct any mistakes that will make it invalid. Then you will return the corrected json string. Nothing else. 
    If the Json is correct just return it.

    Do NOT return a single letter outside of the json string.

    {json_string}
    """

    messages = [{"role": "user", "content": prompt}]

    response = get_chatbot_response(client,model_name,messages)

    return response