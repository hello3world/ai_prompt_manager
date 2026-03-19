from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiToken
from app.schemas import (
    ApiTokenCreate, ApiTokenUpdate, ApiTokenOut, ApiTokenListItem,
)

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


def mask_token(token_value: str) -> str:
    if len(token_value) <= 8:
        return "****"
    return token_value[:4] + "****" + token_value[-4:]


@router.get("", response_model=list[ApiTokenListItem])
async def list_tokens(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiToken).order_by(ApiToken.created_at.desc()))
    tokens = result.scalars().all()
    return [
        ApiTokenListItem(
            id=t.id,
            name=t.name,
            is_active=t.is_active,
            token_masked=mask_token(t.token_value),
        )
        for t in tokens
    ]


@router.get("/active/current")
async def get_active_token(db: AsyncSession = Depends(get_db)):
    """Returns whether there is an active API token configured."""
    result = await db.execute(
        select(ApiToken).where(ApiToken.is_active == True).limit(1)
    )
    token = result.scalar_one_or_none()
    return {"has_token": token is not None}


@router.get("/{token_id}", response_model=ApiTokenOut)
async def get_token(token_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiToken).where(ApiToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


@router.post("", response_model=ApiTokenOut, status_code=201)
async def create_token(data: ApiTokenCreate, db: AsyncSession = Depends(get_db)):
    token = ApiToken(name=data.name, token_value=data.token_value)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


@router.put("/{token_id}", response_model=ApiTokenOut)
async def update_token(
    token_id: int, data: ApiTokenUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ApiToken).where(ApiToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(token, key, value)

    await db.commit()
    await db.refresh(token)
    return token


@router.delete("/{token_id}", status_code=204)
async def delete_token(token_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiToken).where(ApiToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    await db.delete(token)
    await db.commit()
