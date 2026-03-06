import base64
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_db
from app.default_prompts import DEFAULT_PROMPTS
from app.models import Base, Prompt
from app.routers.prompts import router as prompts_router
from app.schemas import GenerateRequest

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env.prod")


async def seed_default_prompts(db: AsyncSession):
    """Seed default prompts — adds any missing prompts by name."""
    for prompt_data in DEFAULT_PROMPTS:
        result = await db.execute(
            select(Prompt).where(Prompt.name == prompt_data["name"])
        )
        if result.scalar_one_or_none() is None:
            db.add(Prompt(**prompt_data))

    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        pass
    from app.database import async_session

    async with async_session() as db:
        await seed_default_prompts(db)

    yield

    await engine.dispose()


app = FastAPI(title="AI Prompt Hub", lifespan=lifespan)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

app.include_router(prompts_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == req.prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Replace {QUERY} placeholder with user query
    full_prompt = prompt.template_text.replace("{QUERY}", req.query)

    api_key = os.getenv("QWEN_API_KEY")
    api_url = os.getenv(
        "QWEN_API_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    model = os.getenv("QWEN_MODEL", "qwen-max")
    max_tokens = int(os.getenv("AI_MAX_TOKENS", "2000"))
    temperature = float(os.getenv("AI_TEMPERATURE", "0.5"))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            generated_text = data["choices"][0]["message"]["content"]
            return {"success": True, "report": generated_text}
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"API Error: {e.response.status_code} - {e.response.text}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post("/generate-vision")
async def generate_vision(
    prompt_id: int = Form(...),
    query: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. Allowed: jpeg, png, gif, webp",
        )

    # Read and validate file size
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Max 10 MB.")

    # Load prompt template
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    full_prompt = prompt.template_text.replace("{QUERY}", query)

    # Build base64 data URI
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{file.content_type};base64,{b64}"

    # API config
    api_key = os.getenv("QWEN_API_KEY")
    api_url = os.getenv(
        "QWEN_API_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    vl_model = os.getenv("QWEN_VL_MODEL", "qwen-vl-max")
    max_tokens = int(os.getenv("AI_MAX_TOKENS", "2000"))
    temperature = float(os.getenv("AI_TEMPERATURE", "0.5"))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": vl_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": full_prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            generated_text = data["choices"][0]["message"]["content"]
            return {"success": True, "report": generated_text}
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"API Error: {e.response.status_code} - {e.response.text}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
