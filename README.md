# Bleecker & Bloom: AI Coffee Shop Assistant ☕

A mobile coffee-shop app with an AI assistant that answers questions about the menu, recommends items, and takes orders through chat.

**Live demo:** https://bleecker-and-bloom.expo.app (open on a phone or desktop; the first chat message can take a minute while the servers wake up)

## Features

- **Ask anything about the shop.** Answers come from a knowledge base of 19 documents (menu, allergens, delivery, loyalty program, FAQ) using hybrid search, and each answer shows its sources.
- **Order by chatting.** "Two lattes and a croissant" updates the cart. The LLM only reports what changed; code applies the changes and prices them from the menu, so totals are always correct.
- **Recommendations from real sales data.** A recommender trained on 39,192 real coffee-shop baskets suggests items that go together, respects dietary needs (vegan, nut-free, caffeine-free, and more), and explains each suggestion.
- **Safe answers.** A guard agent blocks off-topic requests, and allergy questions are answered directly from the knowledge base, not by the model.
- **64-item menu** in 8 categories with product photos, a cart, and checkout.

## Architecture

```
React Native app (Expo, web + mobile)
   │
   ├── Supabase ............ menu, product photos, conversations, orders
   │
   └── Agent API (Python, Docker on RunPod Serverless)
          ├── Guard agent ............. blocks off-topic requests
          ├── Classification agent .... picks the right specialist
          ├── Details agent ........... RAG: BM25 + Chroma vectors + rank fusion
          ├── Order taking agent ...... schema-constrained cart updates
          └── Recommendation agent .... trained basket-analysis engine
                 │
                 └── LLM: Llama 3.1 8B on RunPod (any OpenAI-compatible API works)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design, data, and evaluation results.

## Results

| Evaluation | Result |
|---|---|
| Retrieval (64 questions, Hit@4) | 98% |
| Answer correctness (23 questions) | 23/23 with GPT-4o-mini and Llama 3.1 8B |
| Says "not sure" when it should (5 questions) | 5/5 |
| Recommendations (3,508 held-out baskets, Hit@3) | 33.8% vs 7.2% for popularity |

## Tech stack

**App:** React Native, Expo Router, TypeScript, NativeWind
**Backend:** Python, FastAPI, RunPod Serverless, Docker
**AI:** Llama 3.1 8B (vLLM), OpenAI embeddings, Chroma, BM25
**Data:** Supabase (Postgres, Auth, Storage), pandas

## Project structure

```
coffee_shop_app/          React Native app
python_code/
  api/                    Agents, RAG, recommender, API server, Dockerfile
  knowledge_base/         Markdown documents the assistant answers from
  products/               Menu (products.jsonl) and photos
  dataset/                Sales data used to train the recommender
supabase/schema.sql       Database tables and security rules
```

## Run it locally

**Backend**
```bash
cd python_code
python3.11 -m venv .venv-local && source .venv-local/bin/activate
pip install -r api/requirements.txt
cp .env.local.example .env          # add your LLM and embedding settings
cd api && python -m uvicorn local_server:app --host 0.0.0.0 --port 8000
```

**App**
```bash
cd coffee_shop_app
cp .env.local.example .env          # point it at the backend
npm ci
npx expo start
```

More detail, including RunPod and Supabase setup, is in [python_code/api/README.md](python_code/api/README.md).

## Deployment

- **Agent API:** Docker image on RunPod Serverless (`python_code/api/Dockerfile`, built from `python_code/`)
- **Web app:** Expo Hosting (`npx expo export -p web` then `npx eas-cli deploy --prod`)

## Acknowledgements

Started from Abdullah Tarek's coffee-shop chatbot tutorial. Product photos are from Wikimedia Commons; see `python_code/products/images/CREDITS.md`.
