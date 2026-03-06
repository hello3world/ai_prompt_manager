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
    bug_report_template = (
        "Ты — Senior QA Engineer. Твоя задача — оформить мои черновые заметки "
        "в структурированный, лаконичный и профессиональный баг-репорт (или задачу) "
        "на основе стиля, который мы выработали в предыдущих примерах.\n\n"
        "**Требования к оформлению:**\n\n"
        "1.  **Заголовок:**\n"
        "    *   Начинается с `[FE]` (фронтенд) или `[BE]` (бэкенд).\n"
        "    *   Далее: Страница/Модуль. Суть проблемы.\n"
        "    *   Пример: `[FE] Страница Containers. Обновить статусы работы "
        "оборудования и цветовую схему`\n\n"
        "2.  **Серьезность (Severity):**\n"
        "    *   Выбери один из уровней исходя из описания проблемы: "
        "`Ultra Low`, `Low`, `Medium`, `High`, `Ultra High`.\n"
        "    *   *Критерии:* UI/Опечатки = Low/Medium; Функционал сломан = High; "
        "Критическая ошибка/Потеря данных = Ultra High.\n\n"
        "3.  **Окружение (Environment):**\n"
        "    *   Оставь шаблонную строку (я отредактирую её при необходимости):\n"
        "    *   `Frontend version: [vX.X.X] | Environment: [Stage/Prod] | "
        "Browser: [Chrome]`\n\n"
        "4.  **Структура отчета:**\n"
        "    *   **Предусловия:** Авторизация, подключенный контейнер. "
        "Обязательно включи параметры моков (JSON поля) для сценариев "
        "(Включено, Отключено, Авария), если они упомянуты в черновике.\n"
        "    *   **Шаги воспроизведения:** Нумерованный список, четко и по делу.\n"
        "    *   **Ожидаемый результат:** Текст + Таблица "
        "(если есть сравнение статусов/цветов/значений).\n"
        "    *   **Фактический результат:** Текст + Таблица "
        "(расхождения Факт vs Ожидание).\n"
        "    *   **Описание проблемы:** Краткое резюме "
        "(что унифицируем, что ломаем, какая логика нарушена).\n"
        "    *   **Критерии приемки (Acceptance Criteria):** Чек-лист условий, "
        "при которых задача считается выполненной "
        "(например: «Статусы на странице X соответствуют странице Y», "
        "«Цвет индикатора изменен на желтый»).\n"
        "    *   **Вопросы для уточнения:** "
        "(Если логика не очевидна, есть сомнения в дизайне или поведении — "
        "выноси сюда).\n\n"
        "5.  **Стиль и содержание:**\n"
        "    *   Язык: Русский.\n"
        "    *   Тон: Деловой, технический, без эмоций.\n"
        "    *   Лаконичность: Избегать длинных описаний, "
        "использовать таблицы для сравнения.\n"
        "    *   Технические детали: Сохранять точные названия полей из моков "
        "(например, `InverterCurrentStatus: 3`).\n"
        "    *   Визуальные баги: Делать акцент на сравнении с эталоном "
        "(например, страница Overview).\n"
        "    *   **Блок \"Вложения\" не добавлять** "
        "(я добавлю скриншоты сам).\n\n"
        "**Входные данные (мой черновик):**\n"
        "{QUERY}"
    )
    bug_report_prompt = Prompt(
        name="Bug Report Template",
        description="Оформление черновых заметок в структурированный баг-репорт. "
        "Формат: заголовок [FE]/[BE], Severity, Environment, предусловия, "
        "шаги, ОР/ФР с таблицами, критерии приемки.",
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
