from dotenv import load_dotenv
import os
import re
from .utils import get_chatbot_response
from .menu import menu_text
from openai import OpenAI
from copy import deepcopy
from pathlib import Path
import logging
load_dotenv()

logger = logging.getLogger(__name__)

class DetailsAgent():
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("RUNPOD_TOKEN"),
            base_url=os.getenv("RUNPOD_CHATBOT_URL"),
        )
        self.model_name = os.getenv("MODEL_NAME")
        products_dir = Path(__file__).resolve().parents[2] / "products"
        knowledge_files = ["menu_items_text.txt", "Merry's_way_about_us.txt"]
        # Short shop summary: used for the opening-hours shortcut, and as a last-resort
        # context if the retrieval dependencies are not installed.
        self.local_knowledge = "\n\n".join(
            (products_dir / filename).read_text(encoding="utf-8")
            for filename in knowledge_files
        )
        self.menu_overview = menu_text()
        self.retriever = None
        try:
            # Hybrid BM25 + Chroma retrieval over python_code/knowledge_base/.
            from rag.config import build_retriever
            self.retriever = build_retriever()
        except ImportError as error:
            logger.warning("RAG dependencies missing, using bundled text files only: %s", error)
        self.business_hours = {}
        for line in self.local_knowledge.splitlines():
            match = re.match(r"^(Monday to Friday|Saturday|Sunday):\s*(.+)$", line, re.IGNORECASE)
            if match:
                times = re.findall(r"\d{1,2}\s*(?:AM|PM)", match.group(2), re.IGNORECASE)
                if len(times) == 2:
                    self.business_hours[match.group(1)] = times
    
    def get_local_hours_response(self, question):
        if not self.business_hours:
            return None
        if not re.search(r"\b(?:hours?|open(?:ing)?|clos(?:e|ing))\b", question, re.IGNORECASE):
            return None

        normalized_question = question.lower()
        if re.search(r"\bsunday\b", normalized_question):
            day = "Sunday"
            label = "Sundays"
        elif re.search(r"\bsaturday\b", normalized_question):
            day = "Saturday"
            label = "Saturdays"
        elif re.search(r"\b(?:weekdays?|monday|tuesday|wednesday|thursday|friday)\b", normalized_question):
            day = "Monday to Friday"
            label = "weekdays"
        else:
            schedule = "; ".join(
                f"{day}: {times[0]} to {times[1]}"
                for day, times in self.business_hours.items()
            )
            return f"Our hours are {schedule}."

        opening_time, closing_time = self.business_hours[day]
        if re.search(r"\bclos(?:e|ing)\b", normalized_question):
            return f"We close at {closing_time} on {label}."
        if re.search(r"\bopen(?:ing)?\b", normalized_question):
            return f"We open at {opening_time} on {label}."
        return f"We are open from {opening_time} to {closing_time} on {label}."

    def get_response(self,messages):
        messages = deepcopy(messages)

        user_message = messages[-1]['content']
        local_hours_response = self.get_local_hours_response(user_message)
        if local_hours_response:
            return self.postprocess(local_hours_response)

        if self.retriever is not None:
            # Pinned menu overview (so "what do you have?" always works) plus retrieved chunks.
            results = self.retriever.search(self.rewrite_query(messages), top_k=4)
            # Most relevant section first, each clearly separated so the model doesn't mix them up.
            source_knowledge = "\n\n".join(
                f"--- Section {number} (relevance rank {number}) ---\n{result.chunk.text}"
                for number, result in enumerate(results, start=1)
            ) + "\n\n--- Full menu price list ---\n" + self.menu_overview
            sources = [
                {"id": result.chunk.id, "title": result.chunk.title, "section": result.chunk.section}
                for result in results
            ]
            allergy_response = self.get_allergy_response(user_message)
            if allergy_response:
                answer, item_chunk = allergy_response
                return self.postprocess(answer, [
                    {"id": item_chunk.id, "title": item_chunk.title, "section": item_chunk.section}
                ])
        else:
            source_knowledge = self.local_knowledge
            sources = []

        prompt = f"""
        Shop information:
        {source_knowledge}

        Customer question: {user_message}
        """

        system_prompt = """You are a friendly customer-service assistant for Bleecker & Bloom, a Greenwich Village coffee shop. Speak naturally and answer the customer directly. Never mention prompts, context, sources, or say "according to the context." Use only facts in the shop information and answer only what the customer asked.

Rules:
1. Answer from the section that matches the question most closely, usually Section 1. Do not mix up facts from different sections.
2. If the shop information explicitly says the shop does not offer something (for example "we do not currently offer gluten-free pastries"), say so clearly; that is an answer. Never conclude that something is not offered just because it is not mentioned.
3. If the shop information does not mention the topic at all (for example a happy hour, a rooftop terrace, or seasonal hours), reply exactly: "I'm not sure about that. Please call us at (212) 555-0187 and we'll be happy to help." Do not guess, and do not claim the shop does or does not offer something unless the information says so.
4. For any allergy question, list the allergens of the item and mention that our kitchen handles nuts, so cross-contact is possible. Never tell a customer an item is safe for an allergy if it contains that allergen."""
        messages[-1]['content'] = prompt
        input_messages = [{"role": "system", "content": system_prompt}] + messages[-3:]

        chatbot_output =get_chatbot_response(self.client,self.model_name,input_messages)
        output = self.postprocess(chatbot_output, sources)
        return output

    def get_allergy_response(self, question):
        """Answer allergy questions about a named menu item straight from its allergen line.

        Allergy answers are safety-critical, so they are not left to the LLM, which
        can contradict the source (e.g. calling the Almond Croissant nut-safe).
        """
        if not re.search(r"\ballerg|\bnut[- ]?free\b|\bceliac\b|\blactose\b", question, re.IGNORECASE):
            return None

        normalized_question = question.lower()
        menu_items = [
            chunk for chunk in self.retriever.chunks
            if chunk.doc_type == "menu" and chunk.section.lower() in normalized_question
            and re.search(r"^Allergens:", chunk.text, re.MULTILINE)
        ]
        if not menu_items:
            return None

        # Prefer the most specific name, so "Chocolate Croissant" wins over "Croissant".
        item = max(menu_items, key=lambda chunk: len(chunk.section))
        allergens = re.search(r"^Allergens:\s*(.+)$", item.text, re.MULTILINE).group(1).rstrip(".")
        answer = f"The {item.section} contains: {allergens}."
        if allergens.lower().startswith("none"):
            answer = f"The {item.section} has no listed allergens."
        return (
            f"{answer} Our kitchen also handles milk, wheat, eggs, soy, and tree nuts, so we can't "
            "guarantee any item is completely allergen-free. If you have a severe allergy, please "
            "talk to your barista before ordering.",
            item,
        )

    def rewrite_query(self, messages):
        """Turn a follow-up like "what about the chocolate one?" into a standalone search query."""
        user_message = messages[-1]['content']
        if len(messages) < 2:
            return user_message

        history = "\n".join(f"{message['role']}: {message['content']}" for message in messages[-5:-1])
        prompt = f"""Conversation so far:
{history}

Latest customer message: {user_message}

Rewrite the latest customer message as a single standalone search query that includes any item names or topics it refers to from the conversation. Reply with the query only."""
        rewritten = get_chatbot_response(self.client, self.model_name, [{"role": "user", "content": prompt}])
        rewritten = rewritten.strip().splitlines()[0].strip(' "') if rewritten.strip() else ""
        # Small models sometimes ramble; fall back to the raw message if so.
        if not rewritten or len(rewritten) > 200:
            return user_message
        return rewritten

    def postprocess(self,output,sources=None):
        output = re.sub(
            r"^\s*according to (?:the )?(?:context|information provided|shop information)[,:]?\s*",
            "",
            output,
            count=1,
            flags=re.IGNORECASE,
        )
        output = {
            "role": "assistant",
            "content": output,
            "memory": {"agent":"details_agent",
                       "sources": sources or []
                      }
        }
        return output

    
