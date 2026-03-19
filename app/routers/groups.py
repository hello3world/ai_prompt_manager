from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PromptGroup
from app.schemas import GroupCreate, GroupUpdate, GroupOut, GroupListItem

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[GroupListItem])
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromptGroup).order_by(PromptGroup.name))
    return result.scalars().all()


@router.get("/{group_id}", response_model=GroupOut)
async def get_group(group_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromptGroup).where(PromptGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(data: GroupCreate, db: AsyncSession = Depends(get_db)):
    group = PromptGroup(name=data.name)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.put("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: int, data: GroupUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PromptGroup).where(PromptGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)

    await db.commit()
    await db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromptGroup).where(PromptGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(group)
    await db.commit()
