from agents import (GuardAgent,
                    ClassificationAgent,
                    DetailsAgent,
                    OrderTakingAgent,
                    RecommendationAgent,
                    AgentProtocol
                    )
from pathlib import Path
from agents.order_taking_agent import is_finishing

API_DIR = Path(__file__).resolve().parent

class AgentController():
    def __init__(self):
        self.guard_agent = GuardAgent()
        self.classification_agent = ClassificationAgent()
        self.recommendation_agent = RecommendationAgent(
            API_DIR / 'recommendation_objects/recommender.json'
        )
        
        self.agent_dict: dict[str, AgentProtocol] = {
            "details_agent": DetailsAgent(),
            "order_taking_agent": OrderTakingAgent(self.recommendation_agent),
            "recommendation_agent": self.recommendation_agent
        }
    
    def get_response(self,input):
        # Extract User Input
        job_input = input["input"]
        messages = job_input["messages"]
        # The app's cart, sent with each message so items added outside the chat are kept.
        cart = job_input.get("cart")
        if messages:
            details_agent = self.agent_dict["details_agent"]
            hours_response = details_agent.get_local_hours_response(messages[-1]["content"])
            if hours_response:
                return details_agent.postprocess(hours_response)

        # Mid-order, "that's all" / "no thanks" always belongs to the order agent; the guard and
        # classifier can't judge these short replies without context.
        last_reply = next((m for m in reversed(messages[:-1]) if m["role"] == "assistant"), {})
        mid_order = last_reply.get("memory", {}).get("agent") == "order_taking_agent" and \
            last_reply.get("memory", {}).get("step number") != "done"
        if mid_order and is_finishing(messages[-1]["content"]):
            return self.agent_dict["order_taking_agent"].get_response(messages, cart)

        # Get GuardAgent's response
        guard_agent_response = self.guard_agent.get_response(messages)
        if guard_agent_response["memory"]["guard_decision"] == "not allowed":
            return guard_agent_response
        
        # Get ClassificationAgent's response
        classification_agent_response = self.classification_agent.get_response(messages)
        chosen_agent=classification_agent_response["memory"]["classification_decision"]

        # Get the chosen agent's response
        agent = self.agent_dict[chosen_agent]
        if chosen_agent == "order_taking_agent":
            response = agent.get_response(messages, cart)
        else:
            response = agent.get_response(messages)

        return response
