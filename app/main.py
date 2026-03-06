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


async def seed_default_prompts(db: AsyncSession):
    """Seed default prompts if the DB is empty."""
    result = await db.execute(select(Prompt).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    # Prompt 1: Bug Report Template
    instruction_path = Path(__file__).parent.parent / "bug_report_prompt.md"
    if instruction_path.exists():
        instruction = instruction_path.read_text(encoding="utf-8")
    else:
        # Default instruction if file doesn't exist
        instruction = (
            "Структура баг-репорта:\n"
            "- **Title**: Краткое описание проблемы\n"
            "- **Environment**: Платформа, версия, браузер/ОС\n"
            "- **Steps to Reproduce**: Пошаговая инструкция\n"
            "- **Actual Result**: Что происходит на самом деле\n"
            "- **Expected Result**: Что должно происходить\n"
            "- **Severity/Priority**: Критичность\n"
            "- **Attachments**: Скриншоты, логи"
        )

    bug_report_template = (
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
    bug_report_prompt = Prompt(
        name="Bug Report Template",
        description="Генерация подробного баг-репорта по краткому описанию. "
        "Формат включает платформу, окружение, шаги воспроизведения, "
        "фактический и ожидаемый результат.",
        template_text=bug_report_template,
    )
    db.add(bug_report_prompt)

    # Prompt 2: Test Case Generator (Map)
    test_case_template = (
        "Ты — Senior QA Engineer с экспертизой в функциональном тестировании UI/UX. "
        "Твоя задача: на основе приложенного дизайн-макета и описания функционала "
        "раздела 'Карта' (Map) сформировать полный набор тест-кейсов.\n\n"
        "## STYLE GUIDE (строго соблюдать):\n\n"
        "### 1. Формат заголовка:\n"
        "`[ID] [Название тест-кейса]`\n"
        "- Используй префикс **MAP-** для всех ID\n"
        "- Нумерация: MAP-001, MAP-002, и т.д.\n"
        "- Название должно быть лаконичным и отражать суть проверки\n\n"
        "### 2. Структура каждого тест-кейса:\n\n"
        "| Поле | Описание |\n"
        "|------|----------|\n"
        "| **Description** | Краткая суть проверки (1-2 предложения). Если нечего добавить — пиши 'Not set'. |\n"
        "| **Pre-conditions** | Состояние системы перед выполнением (например, 'Пользователь авторизован', 'На карте есть активные воркеры в статусе Online'). |\n"
        "| **Post-conditions** | Результат после выполнения. Если действие не меняет состояние системы глобально — пиши 'Not set'. |\n"
        "| **Steps** | Нумерованный список четких действий. Используй императивы: 'Нажать', 'Ввести', 'Проверить', 'Перетащить'. |\n"
        "| **Expected result** | Конкретное ожидаемое поведение системы. Что должен увидеть/получить пользователь. |\n\n"
        "### 3. Стиль шагов:\n"
        "```\n"
        "1. Нажать на [элемент].\n"
        "2. Проверить [результат].\n"
        "3. Сравнить [значение A] со [значением B].\n"
        "```\n\n"
        "## КАТЕГОРИИ ТЕСТОВ (создать минимум по 2-3 кейса в каждой):\n\n"
        "### A. Отображение (UI)\n"
        "- Проверка наличия всех элементов из макета\n"
        "- Иконки, подписи, легенда, зум-панель, тулбар\n"
        "- Корректность отображения при разных разрешениях\n\n"
        "### B. Интерактив (UX)\n"
        "- Клик по объекту на карте\n"
        "- Hover-эффекты (подсказки, тултипы)\n"
        "- Drag-and-drop (перетаскивание карты)\n"
        "- Zoom In/Out (кнопки, скролл, pinch)\n\n"
        "### C. Состояния (States)\n"
        "- Отображение воркеров в разных статусах: Online, Offline, Warning, Critical\n"
        "- Визуальная дифференциация (цвета, иконки, анимация)\n"
        "- Переходы между статусами\n\n"
        "### D. Данные (Consistency)\n"
        "- Соответствие цифр на карте значениям в хедере/боковой панели\n"
        "- Синхронизация фильтров и отображаемых объектов\n"
        "- Актуальность данных при обновлении\n\n"
        "### E. Негативные сценарии\n"
        "- Отсутствие воркеров на карте (пустое состояние)\n"
        "- Потеря связи с сервером (спиннер, ошибка, retry)\n"
        "- Некорректные/невалидные данные\n"
        "- Граничные значения (максимальное количество объектов)\n\n"
        "## ВВОДНЫЕ ДАННЫЕ:\n\n"
        "**Функционал раздела 'Карта':**\n"
        "{QUERY}\n\n"
        "---\n\n"
        "Проанализируй предоставленный дизайн-макет и сформируй полный набор тест-кейсов, "
        "строго следуя Style Guide выше. Если на макете есть элементы, не описанные во вводных данных — "
        "создай на них тест-кейсы или укажи вопросы для уточнения."
    )
    test_case_prompt = Prompt(
        name="Test Case Generator (Map)",
        description="Генерация тест-кейсов для раздела 'Карта' (Map) с префиксом MAP-. "
        "Включает UI, UX, States, Consistency и негативные сценарии.",
        template_text=test_case_template,
    )
    db.add(test_case_prompt)

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
