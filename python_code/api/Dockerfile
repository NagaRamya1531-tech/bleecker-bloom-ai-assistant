# RunPod serverless image for the agent API.
# Build from python_code/ so the menu and knowledge base are included:
#   cd python_code
#   docker build --platform linux/amd64 -f api/Dockerfile -t <dockerhub-user>/coffee-chatbot:latest .
FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# The agents read ../products and ../knowledge_base relative to api/.
COPY products/ products/
COPY knowledge_base/ knowledge_base/
COPY api/ api/

WORKDIR /app/api

ENTRYPOINT ["python", "-u", "main.py"]
