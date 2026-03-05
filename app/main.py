import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_db
from app.models import Base, Prompt
from app.routers.prompts import router as prompts_router
from app.schemas import GenerateRequest

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env.prod")


async def seed_default_prompt(db: AsyncSession):
    """Seed the default bug report prompt if the DB is empty."""
    result = await db.execute(select(Prompt).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    instruction_path = Path(__file__).parent.parent / "bug_report_prompt.md"
    if not instruction_path.exists():
        return

    instruction = instruction_path.read_text(encoding="utf-8")
    template = (
        "Ты — эксперт по составлению баг-репортов. На основании краткого описания "
        "бага создай подробный баг-репорт, следуя инструкции ниже.\n\n"
        "## ИНСТРУКЦИЯ ПО ОФОРМЛЕНИЮ БАГ-РЕПОРТА:\n"
        f"{instruction}\n\n"
        "## КРАТКОЕ ОПИСАНИЕ БАГА ОТ ПОЛЬЗОВАТЕЛЯ:\n"
        "{QUERY}\n\n"
        "## ЗАДАЧА:\n"
        "Создай подробный, структурированный баг-репорт на основе описания выше, "
        "строго следуя формату из инструкции. Если какая-то информация не указана "
        "в описании, укажи заглушку [УТОЧНИТЬ] или предложи типичные значения."
    )

    prompt = Prompt(
        name="Bug Report Template",
        description="Генерация подробного баг-репорта по краткому описанию. "
        "Формат включает платформу, окружение, шаги воспроизведения, "
        "фактический и ожидаемый результат.",
        template_text=template,
    )
    db.add(prompt)
    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        pass
    from app.database import async_session

    async with async_session() as db:
        await seed_default_prompt(db)

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
