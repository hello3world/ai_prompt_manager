import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Prompt
from app.schemas import (
    PromptCreate, PromptUpdate, PromptOut, PromptListItem,
    PromptExportItem, ImportResult, PromptMoveRequest,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptListItem])
async def list_prompts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).order_by(Prompt.name))
    return result.scalars().all()


@router.get("/export")
async def export_prompts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).order_by(Prompt.name))
    prompts = result.scalars().all()
    data = [
        PromptExportItem(
            name=p.name,
            description=p.description,
            template_text=p.template_text,
        ).model_dump()
        for p in prompts
    ]
    filename = f"prompts_backup_{date.today().isoformat()}.json"
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ImportResult)
async def import_prompts(
    file: UploadFile = File(...),
    strategy: Literal["skip", "update"] = Query(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted")

    body = await file.read()
    if len(body) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    try:
        items = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of prompts")

    imported = 0
    skipped = 0
    updated = 0
    errors: list[str] = []

    for idx, item in enumerate(items):
        try:
            entry = PromptExportItem(**item)
        except Exception:
            errors.append(f"Item {idx}: invalid structure")
            continue

        result = await db.execute(
            select(Prompt).where(Prompt.name == entry.name)
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            db.add(Prompt(
                name=entry.name,
                description=entry.description,
                template_text=entry.template_text,
            ))
            imported += 1
        elif strategy == "skip":
            skipped += 1
        else:
            existing.description = entry.description
            existing.template_text = entry.template_text
            updated += 1

    await db.commit()
    return ImportResult(imported=imported, skipped=skipped, updated=updated, errors=errors)


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("", response_model=PromptOut, status_code=201)
async def create_prompt(data: PromptCreate, db: AsyncSession = Depends(get_db)):
    prompt = Prompt(
        name=data.name,
        description=data.description,
        template_text=data.template_text,
        group_id=data.group_id,
        feature_id=data.feature_id,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.put("/{prompt_id}", response_model=PromptOut)
async def update_prompt(
    prompt_id: int, data: PromptUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prompt, key, value)

    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await db.delete(prompt)
    await db.commit()


@router.patch("/{prompt_id}/move", response_model=PromptOut)
async def move_prompt(
    prompt_id: int, data: PromptMoveRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt.group_id = data.group_id
    await db.commit()
    await db.refresh(prompt)
    return prompt
