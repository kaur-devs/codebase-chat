# Codebase Chat

Chat with any GitHub repository. Paste a repo URL, and ask questions about the code in natural language — get answers with source citations, file references, and line numbers.

# Deployed Link 
https://codebase-chat-vert.vercel.app/

## How it works

1. **Clone & Parse** — Clones the repo, parses code files using AST-aware chunking (splits at function/class boundaries, not arbitrary token counts)
2. **Embed & Index** — Embeds code chunks using Voyage `voyage-code-3` (code-optimized embeddings) and stores vectors in PostgreSQL via pgvector
3. **Retrieve & Answer** — On each question, retrieves relevant code chunks via cosine similarity, expands context using import graph analysis, and streams an answer via LLM

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL + pgvector (Supabase) |
| LLM | GPT-OSS 120B via Groq (LiteLLM) |
| Embeddings | Voyage `voyage-code-3` |
| Auth | GitHub OAuth + JWT |
| Deployment | Docker, Railway, Vercel |

## Features

- **AST-aware chunking** — Python files split by function/class using the `ast` module. Fallback chunking for other languages.
- **Import graph context** — When answering a question, retrieves not just matching code but also files that import or are imported by it
- **Streaming responses** — Tokens appear in real-time via Server-Sent Events
- **Source citations** — Every answer shows which files and line numbers were used
- **Syntax highlighting** — Code blocks rendered with Prism.js
- **Private repos** — GitHub OAuth with `repo` scope for indexing private repositories
- **Multi-provider LLM** — LiteLLM abstraction supports Groq, OpenAI, Anthropic — switch models with a config change
- **Conversation memory** — Follow-up questions work within a chat session

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL with pgvector (or use Supabase free tier)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/codebase-chat.git
cd codebase-chat
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

You'll need:
- **Supabase** project → connection string ([supabase.com](https://supabase.com))
- **Groq** API key → free at [console.groq.com](https://console.groq.com)
- **Voyage AI** API key → free at [dash.voyageai.com](https://dash.voyageai.com)

> **Indexing speed depends on your Voyage rate limit.** An account with no payment
> method is capped at 3 requests/min and 10,000 tokens/min, which puts a hard floor
> on indexing time: roughly one minute per 10,000 tokens of code, so a 1,600-chunk
> repo takes about half an hour no matter how it is batched. Adding a payment method
> raises the cap by orders of magnitude and the 200M free tokens still apply, so it
> is usually free. After adding one, raise `voyage_requests_per_minute` and
> `voyage_tokens_per_minute` in `backend/app/config.py`.
>
> If an index does fail partway through, progress is saved. Resume it with
> `POST /repos/{id}/reindex`, which embeds only the chunks still missing a vector.
- **GitHub OAuth App** → register at [github.com/settings/developers](https://github.com/settings/developers)

Run migrations:

```bash
alembic upgrade head
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Or use Docker

```bash
docker compose up --build
```

## Project Structure

```
codebase-chat/
├── backend/
│   ├── app/
│   │   ├── models/         # SQLAlchemy models (user, repo, conversation)
│   │   ├── routers/        # API endpoints (auth, repos, chat)
│   │   ├── services/       # Core logic (cloner, chunker, embedder, retriever, llm)
│   │   └── utils/          # Crypto, file filtering
│   ├── alembic/            # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # UI components 
│   │   ├── pages/          # Route pages (Home, Login, AuthCallback)
│   │   ├── hooks/          # Custom hooks (useAuth, useChat)
│   │   └── lib/            # API client with SSE streaming
│   └── vite.config.js
└── docker-compose.yml
```
