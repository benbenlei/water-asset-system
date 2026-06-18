"""Inspections router — nested under an asset."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/assets/{asset_id}/inspections", tags=["inspections"])


@router.post("", response_model=schemas.InspectionRead, status_code=status.HTTP_201_CREATED)
async def add_inspection(
    asset_id: int,
    data: schemas.InspectionCreate,
    db: AsyncSession = Depends(get_db),
):
    if await crud.get_asset(db, asset_id) is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return await crud.add_inspection(db, asset_id, data)


@router.get("", response_model=list[schemas.InspectionRead])
async def list_inspections(asset_id: int, db: AsyncSession = Depends(get_db)):
    asset = await crud.get_asset_with_inspections(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset.inspections
