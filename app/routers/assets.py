"""Assets router ≈ an ASP.NET Core controller.

`Depends(get_db)` is constructor injection. Async endpoints `await` the
data layer. Response models tell FastAPI how to serialize + document.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/pumps", response_model=schemas.AssetRead, status_code=status.HTTP_201_CREATED)
async def create_pump(data: schemas.PumpCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_pump(db, data)


@router.post("/pipes", response_model=schemas.AssetRead, status_code=status.HTTP_201_CREATED)
async def create_pipe(data: schemas.PipeCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_pipe(db, data)


@router.post("/valves", response_model=schemas.AssetRead, status_code=status.HTTP_201_CREATED)
async def create_valve(data: schemas.ValveCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_valve(db, data)


@router.get("", response_model=list[schemas.AssetRead])
async def list_assets(
    db: AsyncSession = Depends(get_db),
    status: models.AssetStatus | None = None,
    asset_type: str | None = Query(default=None, pattern="^(pump|pipe|valve)$"),
):
    return await crud.list_assets(db, status=status, asset_type=asset_type)


@router.get("/at-risk", response_model=list[schemas.AssetAtRiskRead])
async def list_at_risk_assets(db: AsyncSession = Depends(get_db)):
    assets = await crud.list_assets_at_risk(db)
    # Compute risk_score() once per asset — used for both sort key and response.
    scored = sorted(((a, a.risk_score()) for a in assets), key=lambda p: p[1], reverse=True)
    return [
        schemas.AssetAtRiskRead(
            **schemas.AssetRead.model_validate(a).model_dump(),
            risk_score=score,
        )
        for a, score in scored
    ]


@router.get("/{asset_id}", response_model=schemas.AssetRead)
async def get_asset(asset_id: int, db: AsyncSession = Depends(get_db)):
    asset = await crud.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}/status", response_model=schemas.AssetRead)
async def update_asset_status(
    asset_id: int, data: schemas.AssetStatusPatch, db: AsyncSession = Depends(get_db)
):
    asset = await crud.set_asset_status(db, asset_id, data.status)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/{asset_id}/health", response_model=schemas.AssetHealth)
async def get_asset_health(asset_id: int, db: AsyncSession = Depends(get_db)):
    asset = await crud.get_asset_with_inspections(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    # asset is really a Pump/Pipe/Valve instance — risk_score() dispatches
    # to the correct subclass override automatically.
    return schemas.AssetHealth(
        asset_id=asset.id,
        asset_type=asset.asset_type,
        latest_condition=asset.latest_condition(),
        risk_score=asset.risk_score(),
        inspections_count=len(asset.inspections),
    )
