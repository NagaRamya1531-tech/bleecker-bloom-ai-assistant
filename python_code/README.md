# Python Code for Coffee Shop Chatbot
This folder contains the Python code and notebooks necessary for building and deploying the chatbot system for the coffee shop app. The code is organized into several components, each serving a specific function within the overall project.

## 📂 Directory Structure
```bash
├── python_code
│   ├── API/               # Chatbot API for agent-based system
│   ├── dataset/           # Dataset for training recommendation engine    
│   ├── products/          # Product data (names, prices, descriptions, images)   
│   ├── knowledge_base/    # Markdown documents for RAG (indexed into a local Chroma store)
│   ├── recommendation_engine_training.ipynb    # Original notebook (replaced by api/recommender/) 
```
## 📚 Components Overview
### API
This folder contains the code for the API that handles requests to the chatbot agent system. It serves as the bridge between the React Native app and the backend functionality.
### Dataset
This folder includes the downloaded dataset from Kaggle used for training the recommendation engine. It serves as the foundation for generating personalized product suggestions.
### Products
Contains product information utilized in the app, including names, prices, descriptions, and images. This data is essential for displaying products within the app and for the chatbot's responses.
### Notebooks
The vector index is built by `python -m rag.ingest` and products are uploaded to Supabase by `python -m supabase_seed` (both run from `api/`), replacing the original notebooks.
#### recommendation_engine_training.ipynb: 
The original market basket notebook. The API now uses `api/recommender/` (`python -m recommender.train`); see [ARCHITECTURE.md](../ARCHITECTURE.md).


## 🚀 Getting Started

For Detailed instructions follow my Youtube tutorial
To set up the project and run the notebooks, follow these steps:

1. **Install Requirements**:  
   Ensure you have the necessary dependencies installed by running:
   ```bash
   pip install -r requirements.txt
    ```
2. **Create a Huggingface account**:
    * Create a [Hugging Face](https://huggingface.co)
    * Choose an LLM model and If necessary agree to the terms of use for the model you are going to use (necessary for LLama 3). I am going to use [LLama 3](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct).
    * Create a Hugging face account token. You are going to need when setting up the Chatbot on Runpod.
    * Create .env tile python_code folder and add the enviroement variable.
    ```
    MODEL_NAME=<your_chosen_hugginface_model>
    ```

3. **Create a RunPod Account**:
    * Sign up for a [RunPod](https://rebrand.ly/Runpod-Abdullah) account.
    * Create a ChatBot endpoint and an embedding endpoint.
    * Obtain your RunPod token and fill in the .env file with the following:
    ```
    RUNPOD_TOKEN=<your_runpod_token>
    RUNPOD_CHATBOT_URL=<your_chatbot_endpoint>
    RUNPOD_EMBEDDING_URL=<your_embedding_endpoint>
    ``
4. **Vector database (no account needed)**:
    * Retrieval uses a local [Chroma](https://docs.trychroma.com) index plus BM25 keyword search over `knowledge_base/`. It is built automatically the first time the API starts, or with `python -m rag.ingest` from `api/`.
    * Set the embedding model in the .env file (any OpenAI-compatible embeddings endpoint):
    ```
    EMBEDDING_MODEL_NAME=<your_embedding_model>
    ```
5. **Create a Supabase project** (optional; the free plan is enough):
    * Run `supabase/schema.sql` (repository root) in the dashboard's SQL Editor.
    * Enable Authentication > Sign In / Providers > **Allow anonymous sign-ins**.
    * Copy the project URL and the secret (service_role) key from Project Settings > API into the .env file:
    ```
    SUPABASE_URL=<your_project_url>
    SUPABASE_SECRET_KEY=<your_secret_key>
    ```
    * Upload the menu and photos with `python -m supabase_seed` from `api/`.
5. **Run Notebooks** :
    * You are now ready to run each Jupyter notebook without any issues. Open the notebooks and execute the cells as needed.