# AI Prompt Hub

Web-application for working with AI (Qwen) through pre-configured prompt templates. Includes CRUD for prompts, theme switching, rich-text copy for Jira, and localStorage persistence.

## Prerequisites

- [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) (includes Docker Compose)
- Git

## Deployment on macOS

### 1. Clone the repository

```bash
git clone https://github.com/hello3world/ai_prompt_manager.git
cd ai_prompt_manager
```

### 2. Create the environment file

Copy the example and fill in your API keys:

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` and set your values:

```dotenv
# AI Provider
AI_PROVIDER=qwen

# QWEN
QWEN_API_KEY=<your-qwen-api-key>
QWEN_API_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max

# AI Settings
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.5

# Database (keep defaults for local Docker setup)
DB_HOST=db
DB_PORT=5432
DB_NAME=prompthub
DB_USER=postgres
DB_PASSWORD=prompthub_secret
```

### 3. Build and run

```bash
docker compose up --build -d
```

This starts two containers:
- **prompthub-db** -- PostgreSQL 16 database
- **prompthub-app** -- FastAPI application on port 8000

### 4. Open the application

Open in browser: [http://localhost:8000](http://localhost:8000)

On first launch, the default "Bug Report Template" prompt is automatically seeded into the database.

### 5. Stop the application

```bash
docker compose down
```

To also remove the database volume (all stored prompts will be lost):

```bash
docker compose down -v
```

## Usage

- **Select a prompt** in the left sidebar
- **Enter your query** in the text area -- it replaces the `{QUERY}` placeholder in the prompt template
- **Click Generate** or press `Ctrl+Enter`
- **Copy the response** -- copies both rich HTML (for Jira) and plain markdown
- **Manage prompts** -- click "Manage Prompts" to create, edit, or delete prompt templates
- **Switch themes** -- Dark, Gray, Charcoal (no blue), White via buttons in the header
- **Reset** -- clears the input and output, removes cached response

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI app, lifespan, /generate endpoint
│   ├── database.py           # Async SQLAlchemy engine & session
│   ├── models.py             # Prompt ORM model
│   ├── schemas.py            # Pydantic schemas
│   ├── routers/
│   │   └── prompts.py        # CRUD API /api/prompts
│   └── templates/
│       └── index.html        # Frontend (vanilla JS)
├── bug_report_prompt.md      # Default prompt (seeded on first run)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.prod                 # Environment variables (not committed)
```

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy (async), asyncpg
- **Database:** PostgreSQL 16
- **Frontend:** Vanilla JS, marked.js
- **AI:** Qwen (DashScope API)
- **Deploy:** Docker Compose
