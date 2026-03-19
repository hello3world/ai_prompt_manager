from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import FeatureDescription
from app.schemas import FeatureCreate, FeatureUpdate, FeatureOut, FeatureListItem

router = APIRouter(prefix="/api/features", tags=["features"])


@router.get("", response_model=list[FeatureListItem])
async def list_features(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FeatureDescription).order_by(FeatureDescription.name)
    )
    return result.scalars().all()


@router.get("/{feature_id}", response_model=FeatureOut)
async def get_feature(feature_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FeatureDescription).where(FeatureDescription.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


@router.post("", response_model=FeatureOut, status_code=201)
async def create_feature(data: FeatureCreate, db: AsyncSession = Depends(get_db)):
    feature = FeatureDescription(
        name=data.name, description_text=data.description_text
    )
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return feature


@router.put("/{feature_id}", response_model=FeatureOut)
async def update_feature(
    feature_id: int, data: FeatureUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FeatureDescription).where(FeatureDescription.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feature, key, value)

    await db.commit()
    await db.refresh(feature)
    return feature


@router.delete("/{feature_id}", status_code=204)
async def delete_feature(feature_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FeatureDescription).where(FeatureDescription.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    await db.delete(feature)
    await db.commit()
