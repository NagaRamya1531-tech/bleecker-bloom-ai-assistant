# 🛠️ API Folder

This folder contains the code for deploying the chatbot's agent-based system. This is considered the backend of the application. Below is an overview of the folder structure and its components.

## 📂 Folder Structure

### Agents Folder

The `agents` folder follows an agent-based architecture, where each agent is responsible for a specific task within the chatbot system:

- **guard_agent.py**: Responsible for blocking unrelated or harmful queries.
- **classification_agent.py**: Classifies the user's input and determines which agent should respond.
- **details_agent.py**: Handles questions related to coffee shop details and menu items.
- **order_taking_agent.py**: Manages the order-taking process, ensuring structured and accurate order data.
- **recommendation_agent.py**: Extracts the customer's request with the LLM and asks the `recommender/` engine for suggestions.
- **utils.py**: Contains utility functions for:
  - Retrieving responses from the LLM (Large Language Model).
  - Generating embeddings.
  - Validating JSON outputs for structured data.

### Recommendation Objects Folder

- **recommendation_objects**: Contains the trained recommendation models that are used by the `recommendation_agent.py` to suggest products.

### Other Files

- **agent_controller.py**: Orchestrates the interaction between the agents, coordinating their responses and managing the flow of information.
- **main.py**: Calls the `agent_controller` and integrates with RunPod's deploy functionality.
- **Dockerfile**: Builds the code into a Docker image for deployment.

# 🐳 Deploying on RunPod
To deploy the chatbot API on RunPod:

1. Push Docker Image:
    Push the Dockerfile to your DockerHub account, or you can use the pre-built image:
    ```
    abdullah57/chatbot
    ```
2. Create RunPod Endpoint:

Go to the RunPod serverless section and create a new endpoint.
Fill in the required information, including the DockerHub image.
Add the necessary environment variables from your .env file.

Your API is now ready to be deployed and used in the chatbot system!

## 🚀 Running the Code Locally

### Fully local development (Ollama)

The API can run locally without RunPod. Ollama must be running with the `llama3.1:8b` model available, the local Ollama tag corresponding to the `meta-llama/Llama-3.1-8B-Instruct` model named in the cloud example. This quantized 8B model is memory-intensive. The Details Agent uses hybrid retrieval (BM25 + a local Chroma vector index) over the Markdown knowledge base in `python_code/knowledge_base/`; no hosted vector database is needed (see Local RAG below). Supabase is optional: without its keys the API keeps conversations in memory and the app reads products from the local API.

From the repository root:

```bash
cd python_code
python3.11 -m venv .venv-local
source .venv-local/bin/activate
python -m pip install -r api/requirements.txt
cp .env.local.example .env
ollama pull nomic-embed-text
```

Then launch the API from `python_code/api`:

```bash
cd api
python -m uvicorn local_server:app --host 0.0.0.0 --port 8000
```

The chat endpoint is `POST /` and retains the RunPod request/response shape. The local product catalog is `GET /products`.

In another terminal, configure and run Expo:

```bash
cd coffee_shop_app
cp .env.local.example .env
npm ci
npm start
```

The example URL works for web and the iOS simulator. For an Android emulator, use `http://10.0.2.2:8000`; for a physical phone, use the computer's LAN address. Set that same reachable address in both `.env` files. The local API does not validate `EXPO_PUBLIC_RUNPOD_API_KEY`.

### Local RAG

The Details Agent answers from `python_code/knowledge_base/`: Markdown documents covering the menu (with allergens, caffeine, and dietary tags), retail beans and tea, brewing guides, delivery and refund policies, the loyalty program, an FAQ, and catering and events.

- **Chunking**: every `##`/`###` heading becomes one chunk, prefixed with its heading path and tagged with front matter metadata (`doc_type`, `category`, `Tags:`).
- **Hybrid search**: BM25 keyword search plus `nomic-embed-text` vectors in a local Chroma store, merged with Reciprocal Rank Fusion. Metadata filters are supported, e.g. `search(q, filters={"tags": "vegan"})`.
- **Query rewriting**: follow-up questions are rewritten into standalone search queries using the conversation history.
- **Citations**: retrieved chunk ids are returned in `memory.sources`.
- **Fallbacks**: if the embedding model is unavailable the retriever uses BM25 only; if `chromadb`/`rank_bm25` are not installed the agent uses the bundled text files.

The index is built automatically on first start and rebuilt whenever the knowledge base changes. From `python_code/api`:

```bash
python -m rag.ingest "is the almond croissant safe for nut allergies?"   # build index and try a query
python -m rag.evaluate --misses                                            # retrieval eval
```

Retrieval eval on 64 labeled questions (`rag/eval_questions.jsonl`, k=4), 64-item menu (162 chunks), `text-embedding-3-small`:

| mode   | hit@1 | hit@4 | MRR   |
|--------|-------|-------|-------|
| BM25   | 70%   | 91%   | 0.785 |
| vector | 89%   | 98%   | 0.935 |
| hybrid | 91%   | 98%   | 0.943 |

The one hybrid miss is "What's the cheapest coffee you have?": comparing prices across items is a structured query that belongs in a tool, not in retrieval. On the earlier 21-item menu and 50 questions, hybrid search with the local `nomic-embed-text` model scored 92% hit@1 and 100% hit@4.

Answer eval (`python -m rag.evaluate_answers`, `rag/eval_answers.jsonl`): 23 questions with required facts plus 5 the knowledge base cannot answer, where the agent must say it is not sure instead of guessing.

| chat model    | correct answers | says "not sure" when it should |
|---------------|-----------------|--------------------------------|
| `gemma:2b`    | 14/15           | 5/5                            |
| `gpt-4o-mini` | 23/23           | 5/5                            |

(`gemma:2b` was measured on the first 15 questions, before the menu was expanded.)

Allergy questions about a named menu item are answered directly from that item's allergen line rather than by the LLM, because a small model was observed calling the Almond Croissant safe for nut allergies.

### Conversations and orders (Supabase)

The local server keeps each customer's conversation on the server, so the app only sends the new message, the chat popup and the full chat screen share one conversation, and it survives app restarts.

| Endpoint | Purpose |
|---|---|
| `GET /chat` | The customer's saved conversation |
| `POST /chat` `{"message": "..."}` | Send a message; the server loads the history, runs the agents, and saves the reply |
| `DELETE /chat` | Start a new conversation |
| `POST /orders` `{"items": [{"item": "Latte", "quantity": 1}]}` | Record an order with prices recomputed from the menu, then clear the conversation |
| `GET /orders` | The customer's 5 most recent orders |
| `GET /health` | Shows whether the `supabase` or `memory` store is active |
| `POST /` | The original stateless endpoint (same shape as RunPod), kept for compatibility |

**Storage.** With `SUPABASE_URL` and `SUPABASE_SECRET_KEY` set in `python_code/.env`, conversations are stored in the `chats` table (one row per customer, messages as `jsonb`) and orders in the `orders` table, written only by the API through Supabase's REST API. Row Level Security is on with no policies for those tables, so the app's publishable key can't read or write them. Without the keys, an in-memory store is used (fine for development, lost when the server restarts).

**Identity.** With `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` set in `coffee_shop_app/.env`, the app signs in anonymously (no account needed) and sends its Supabase access token; the API verifies it with Supabase Auth (cached for 60 seconds), so a customer can only reach their own conversation. Without Supabase, the app sends a random device id saved on the phone.

**Prices.** The server recomputes every order line from `products.jsonl` (in the Order Taking Agent and at checkout) and drops anything that isn't on the menu, so neither the LLM nor a modified app can change a price.

**Supabase setup** (one time, free plan): run `supabase/schema.sql` in the SQL Editor (creates `products`, `chats`, `orders`, the policies, and the public `product-images` bucket), enable **Allow anonymous sign-ins** under Authentication > Sign In / Providers, add the keys to both `.env` files, then run `python -m supabase_seed` to upload the menu and photos. The app reads products from Supabase when `EXPO_PUBLIC_PRODUCTS_API_URL` is not set.

### Menu

The menu has 64 items in 8 categories, modeled on a typical independent New York coffee shop: Espresso Drinks (10), Brewed Coffee (6), Cold Coffee (5), Tea & Tea Lattes (11), Hot Chocolate & Steamers (3), Bakery (14), Breakfast & Lunch (7), and Add-ons (8). `python_code/products/products.jsonl` is the single source of truth: the Order Taking Agent, the Details Agent, and the guard all read the menu from it through `agents/menu.py`.

- 34 items have real sales history and record where they appear in the receipts with `dataset_name` and `dataset_category` (e.g. "Colombian Drip" is "Columbian Medium Roast" in category "Coffee").
- 30 items are new and have no sales history. Each names a hand-picked `similar_to` item with sales (e.g. Cold Brew -> Brazilian Organic Drip, same beans; Chai Latte -> Traditional Blend Chai) that the recommender borrows pairings from. No sales data was invented for them.

To add an item: add it to `products.jsonl` (with `similar_to` if it has no sales history), add a section under `knowledge_base/menu/` with a `Tags:` line that includes exactly one of `contains-caffeine`, `low-caffeine`, or `caffeine-free`, then run `python -m recommender.train` (it validates the tags) and `python -m agents.menu` (refreshes `menu_items_text.txt`). Product photos live in `python_code/products/images/`. Photos for the items added in 2026 come from Wikimedia Commons under free licenses (CC0, public domain, CC BY, CC BY-SA); `products/images/CREDITS.md` lists the author, license, and source for each, which CC BY and CC BY-SA require. Items without a photo (`"image_path": ""`, currently only Egg & Cheese) show a placeholder in the app.

Note: the Dockerfile builds from `api/` only, so a cloud image does not include `python_code/products/`, which the agents now read.

### Recommendations

`recommender/` is the recommendation engine used by the Recommendation Agent and by the Order Taking Agent's "customers often add..." suggestions. The LLM only extracts what the customer wants (items, categories, dietary needs, budget) using JSON mode, every value is validated against the menu, and the engine picks the items, so the LLM cannot recommend something that is not on the menu.

- **Basket pairings** learned from the April 2019 sales receipts, limited to items on the app menu (retail items like packaged chocolate are excluded). Baskets are keyed by `(transaction_id, transaction_date, sales_outlet_id)`; the original notebook's `transaction_id + customer_id` key merged 39,271 real transactions into 23,281 because ids restart daily and half the rows are the anonymous customer 0.
- **Daypart popularity** (morning / midday / afternoon) for "what's popular?" requests.
- **Cold start** for the 30 menu items with no sales history: each borrows the pairings of its hand-picked `similar_to` item, at a discount and only one hop deep (a new item is never suggested on the strength of another new item). Reasons say so ("Cold Brew is new, so this is based on orders of the similar Brazilian Organic Drip"). An automatic ingredient/tag similarity is only a fallback; it picked poor matches (Cold Brew -> espresso, Yogurt Parfait -> caramel syrup) when whole categories were new.
- **One drink per suggestion**: if the cart already has a drink, suggestions are food and add-ons, not a second drink.
- **Filters** from the knowledge base tags: `vegan`, `dairy-free`, `nut-free`, `gluten-free`, `low-caffeine`, `caffeine-free`, `sugar-free`, plus category and max price. When nothing matches, the agent says so instead of suggesting something unsuitable; allergy requests get a cross-contact note.
- **Explanations**: every suggestion carries a reason ("ordered with the Latte in 12% of Latte orders"), returned in `memory.recommendations`. The app shows them as tappable chips that send "Add one X to my order" to the Order Taking Agent.

From `python_code/api`:

```bash
python -m recommender.train      # rebuild recommendation_objects/recommender.json
python -m recommender.evaluate   # offline evaluation
```

Offline evaluation on the 64-item menu: train on April 1-22, test on April 23-29 (1,722 baskets with 2+ menu items, 3,508 trials). Hide one item from each basket, recommend 3 from the rest, and count a hit if the hidden item is recommended:

| method                                         | hit@3 |
|------------------------------------------------|-------|
| popularity (overall)                           | 7.2%  |
| popularity (by daypart)                        | 6.7%  |
| confidence, original basket key                | 25.6% |
| confidence, fixed basket key                   | 33.6% |
| lift                                           | 27.9% |
| original basket key + fill + one-drink rule    | 33.4% |
| fixed basket key + fill + one-drink rule (production) | 33.8% |

Lift over-rewards rare pairings, so production ranks by confidence. Most of the basket-key fix's gain came from removing fake drink-plus-drink pairs created by merged baskets; once the one-drink rule filters drink suggestions, the original key nearly catches up (33.4% vs 33.8%). The 30 new items cannot be evaluated offline because they have no sales history.
`recommendation_engine_training.ipynb` and the `apriori_recommendations.json` / `popularity_recommendation.csv` files it produced are no longer used by the API.

### Using a RunPod vLLM endpoint

The agents talk to any OpenAI-compatible server, including a RunPod serverless vLLM endpoint. In `python_code/.env`:

```
RUNPOD_TOKEN=<RunPod API key, rpa_...>
RUNPOD_CHATBOT_URL=https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1
MODEL_NAME=<the exact id the endpoint serves, e.g. meta-llama/llama-3.1-8b-instruct>
EMBEDDING_API_KEY=<key for the embeddings provider, if different from RUNPOD_TOKEN>
```

- The URL must end in `/openai/v1` (vLLM's OpenAI route), not `/run` or `/runsync` (RunPod's job API).
- `MODEL_NAME` must match what `GET /openai/v1/models` returns, or vLLM rejects the request.
- Embeddings can stay on another provider (e.g. OpenAI `text-embedding-3-small`) via `EMBEDDING_API_KEY`.
- The Order Taking Agent uses JSON-schema structured outputs, which vLLM supports; it falls back to JSON mode on servers that don't.
- Serverless workers scale to zero: the first request after idling took about 2 minutes. Raise the idle timeout or keep one active worker for a demo.

### Existing cloud deployment

1. **Set Up Environment Variables**:  
   Ensure that the required variables are set in your `.env` file.
   
2. **Install Dependencies**:  
   Install the necessary dependencies by running:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Code**:   
    You can run the chatbot locally by executing:
    ```bash
    python development_code.py
    ```