from dotenv import load_dotenv
import os
import json
from copy import deepcopy
from .utils import get_chatbot_response, parse_json_output
from openai import OpenAI
load_dotenv()

class ClassificationAgent():
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("RUNPOD_TOKEN"),
            base_url=os.getenv("RUNPOD_CHATBOT_URL"),
        )
        self.model_name = os.getenv("MODEL_NAME")
    
    def get_response(self,messages):
        messages = deepcopy(messages)

        system_prompt = """
            You are a helpful AI assistant for Bleecker & Bloom, a coffee shop that serves coffee, tea, hot chocolate, pastries, and breakfast and lunch food.
            Your task is to determine what agent should handle the user input. You have 3 agents to choose from:
            1. details_agent: This agent is responsible for answering questions about the coffee shop, like location, delivery places, working hours, details about menue items. Or listing items in the menu items. Or by asking what we have.
            2. order_taking_agent: This agent is responsible for taking orders from the user. It's responsible to have a conversation with the user about the order untill it's complete.
            3. recommendation_agent: This agent is responsible for giving recommendations to the user about what to buy. If the user asks for a recommendation, this agent should be used.

            Your output should be in a structured json format like so. each key is a string and each value is a string. Make sure to follow the format exactly:
            {
            "chain of thought": go over each of the agents above and write some your thoughts about what agent is this input relevant to.
            "decision": "details_agent" or "order_taking_agent" or "recommendation_agent". Pick one of those. and only write the word.
            "message": leave the message empty.
            }
            """
        
        input_messages = [
            {"role": "system", "content": system_prompt},
        ]

        input_messages += messages[-3:]

        chatbot_output =get_chatbot_response(self.client,self.model_name,input_messages,json_mode=True)
        output = self.postprocess(chatbot_output, messages)
        return output

    def postprocess(self,output,messages=()):
        output = parse_json_output(output)
        decision = output.get('decision')
        if decision not in ("details_agent", "order_taking_agent", "recommendation_agent"):
            # Unreadable output: stay with the agent that handled the last turn, else answer questions.
            previous = [m.get("memory", {}).get("agent") for m in messages if m["role"] == "assistant"]
            decision = next((agent for agent in reversed(previous)
                             if agent in ("details_agent", "order_taking_agent", "recommendation_agent")), "details_agent")

        dict_output = {
            "role": "assistant",
            "content": output.get('message', ''),
            "memory": {"agent":"classification_agent",
                       "classification_decision": decision
                      }
        }
        return dict_output

    
