# AI Prompt Hub

Web-application for working with AI (Qwen) through pre-configured prompt templates. Organize prompts into groups, manage API tokens, link feature descriptions, and generate structured output for Jira.

## Features

- **Prompt Management** -- CRUD operations for prompt templates with search and filtering
- **Groups** -- Organize prompts into collapsible groups (e.g., "General", "API Tests")
- **Feature Descriptions** -- Link prompts to feature descriptions for context-aware generation
- **API Token Management** -- Store and manage multiple API tokens with activation/deactivation
- **Import/Export** -- Backup and restore prompts via JSON export/import
- **Vision Support** -- Upload images for visual analysis with AI
- **Theme Switching** -- Dark, Gray, Charcoal, and White themes
- **Rich Copy** -- Copy output as formatted HTML for Jira or plain markdown

## Prerequisites

- [Docker Desktop](https://docs.docker.com/desktop/install/) (Windows, Mac, or Linux)
- Git

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/hello3world/ai_prompt_manager.git
cd ai_prompt_manager
```

### 2. Create the environment file

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` and set your Qwen API key:

```dotenv
# AI Provider
AI_PROVIDER=qwen

# QWEN (required)
QWEN_API_KEY=your-api-key-here
QWEN_API_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max

# AI Settings
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.5

# Database (keep defaults for Docker)
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

Navigate to: [http://localhost:8000](http://localhost:8000)

Default prompts ("Bug Report Template", "Test Case Generator", etc.) are automatically seeded on first launch.

### 5. Stop the application

```bash
docker compose down
```

To remove all data including the database:

```bash
docker compose down -v
```

## Usage

1. **Select a prompt** from the left sidebar (organized by groups)
2. **Enter your query** -- it replaces the `{QUERY}` placeholder in the template
3. **Click Generate** or press `Ctrl+Enter`
4. **Copy the response** -- formatted for Jira (rich HTML) or markdown
5. **Manage prompts** -- click "Manage Prompts" to create, edit, delete, or organize templates
6. **Manage Groups** -- organize prompts into collapsible groups
7. **Feature Descriptions** -- add context descriptions linked to prompts
8. **API Tokens** -- manage multiple AI API tokens in Settings

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/prompts` | List all prompts |
| `POST /api/prompts` | Create new prompt |
| `GET /api/groups` | List prompt groups |
| `POST /api/groups` | Create new group |
| `GET /api/features` | List feature descriptions |
| `GET /api/tokens` | List API tokens |
| `POST /generate` | Generate AI response |
| `POST /generate-vision` | Generate with image upload |

## Database Connection

Connect to PostgreSQL inside Docker:

```bash
docker exec -it prompthub-db psql -U postgres -d prompthub
```

Or connect from external tools (pgAdmin, DBeaver) using:
- Host: `localhost`
- Port: `5432` (or `5433` if mapped differently)
- Database: `prompthub`
- User: `postgres`
- Password: `prompthub_secret`

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI app, lifespan, /generate endpoints
│   ├── default_prompts.py   # Default prompt definitions
│   ├── database.py          # Async SQLAlchemy engine & session
│   ├── models.py            # ORM models (Prompt, Group, Feature, Token)
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── prompts.py       # Prompt CRUD API
│   │   ├── groups.py        # Group management API
│   │   ├── features.py      # Feature descriptions API
│   │   └── tokens.py        # API token management API
│   └── templates/
│       └── index.html       # Frontend (vanilla JS)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.prod.example        # Environment template
└── .env.prod                # Your environment variables (not committed)
```

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), asyncpg
- **Database:** PostgreSQL 16
- **Frontend:** Vanilla JavaScript, marked.js
- **AI:** Qwen (DashScope API) with vision support
- **Deploy:** Docker Compose
