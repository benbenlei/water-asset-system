"""MaintenanceJob router — nested creation/listing under assets, standalone PATCH/GET."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db

router = APIRouter(tags=["maintenance_jobs"])


@router.post(
    "/assets/{asset_id}/maintenance-jobs",
    response_model=schemas.MaintenanceJobRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_maintenance_job(
    asset_id: int,
    data: schemas.MaintenanceJobCreate,
    db: AsyncSession = Depends(get_db),
):
    if await crud.get_asset(db, asset_id) is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return await crud.create_maintenance_job(db, asset_id, data)


@router.get(
    "/assets/{asset_id}/maintenance-jobs",
    response_model=list[schemas.MaintenanceJobRead],
)
async def list_maintenance_jobs(asset_id: int, db: AsyncSession = Depends(get_db)):
    if await crud.get_asset(db, asset_id) is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return await crud.list_maintenance_jobs(db, asset_id)


@router.get("/maintenance-jobs/{job_id}", response_model=schemas.MaintenanceJobRead)
async def get_maintenance_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await crud.get_maintenance_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="MaintenanceJob not found")
    return job


@router.patch(
    "/maintenance-jobs/{job_id}/status",
    response_model=schemas.MaintenanceJobRead,
)
async def update_job_status(
    job_id: int,
    data: schemas.JobStatusPatch,
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await crud.update_job_status(db, job_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="MaintenanceJob not found")
    return job
