"""Data-access layer: thin async functions over the ORM.

Keeping queries here (instead of in the routers) mirrors a repository/
service split. Every function takes an AsyncSession, like passing a
DbContext into a repository method.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


async def create_pump(db: AsyncSession, data: schemas.PumpCreate) -> models.Pump:
    pump = models.Pump(
        name=data.name,
        zone=data.zone,
        flow_rate_lps=data.flow_rate_lps,
        power_kw=data.power_kw,
        **({"installed_date": data.installed_date} if data.installed_date else {}),
    )
    db.add(pump)
    await db.commit()
    await db.refresh(pump)
    return pump


async def create_pipe(db: AsyncSession, data: schemas.PipeCreate) -> models.Pipe:
    pipe = models.Pipe(
        name=data.name,
        zone=data.zone,
        length_m=data.length_m,
        diameter_mm=data.diameter_mm,
        material=data.material,
        **({"installed_date": data.installed_date} if data.installed_date else {}),
    )
    db.add(pipe)
    await db.commit()
    await db.refresh(pipe)
    return pipe


async def create_valve(db: AsyncSession, data: schemas.ValveCreate) -> models.Valve:
    valve = models.Valve(
        name=data.name,
        zone=data.zone,
        valve_kind=data.valve_kind,
        diameter_mm=data.diameter_mm,
        **({"installed_date": data.installed_date} if data.installed_date else {}),
    )
    db.add(valve)
    await db.commit()
    await db.refresh(valve)
    return valve


async def get_asset(db: AsyncSession, asset_id: int) -> models.Asset | None:
    return await db.get(models.Asset, asset_id)


async def get_asset_with_inspections(
    db: AsyncSession, asset_id: int
) -> models.Asset | None:
    """Eager-load inspections and maintenance_jobs so risk_score() works under async."""
    stmt = (
        select(models.Asset)
        .where(models.Asset.id == asset_id)
        .options(
            selectinload(models.Asset.inspections),
            selectinload(models.Asset.maintenance_jobs),
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_assets(
    db: AsyncSession,
    status: models.AssetStatus | None = None,
    asset_type: str | None = None,
) -> list[models.Asset]:
    stmt = select(models.Asset)
    if status is not None:
        stmt = stmt.where(models.Asset.status == status)
    if asset_type is not None:
        stmt = stmt.where(models.Asset.asset_type == asset_type)
    return list((await db.execute(stmt)).scalars().all())


async def list_assets_at_risk(db: AsyncSession) -> list[models.Asset]:
    """Eager-load both relationships needed by risk_score(); caller sorts.

    Sorting is intentionally left to the caller so risk_score() is computed
    exactly once per asset (for both the sort key and the response payload).
    """
    stmt = select(models.Asset).options(
        selectinload(models.Asset.inspections),
        selectinload(models.Asset.maintenance_jobs),
    )
    return list((await db.execute(stmt)).scalars().all())


async def set_asset_status(
    db: AsyncSession, asset_id: int, new_status: models.AssetStatus
) -> models.Asset | None:
    asset = await db.get(models.Asset, asset_id)
    if asset is None:
        return None
    if asset.status == new_status:
        return asset
    asset.status = new_status
    await db.commit()
    return asset


async def add_inspection(
    db: AsyncSession, asset_id: int, data: schemas.InspectionCreate
) -> models.Inspection:
    inspection = models.Inspection(
        asset_id=asset_id,
        condition_score=data.condition_score,
        notes=data.notes,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return inspection


async def create_maintenance_job(
    db: AsyncSession, asset_id: int, data: schemas.MaintenanceJobCreate
) -> models.MaintenanceJob:
    job = models.MaintenanceJob(
        asset_id=asset_id,
        inspection_id=data.inspection_id,
        assigned_to=data.assigned_to,
        scheduled_date=data.scheduled_date,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def list_maintenance_jobs(
    db: AsyncSession, asset_id: int
) -> list[models.MaintenanceJob]:
    stmt = (
        select(models.MaintenanceJob)
        .where(models.MaintenanceJob.asset_id == asset_id)
        .order_by(nulls_last(desc(models.MaintenanceJob.completed_at)))
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_maintenance_job(
    db: AsyncSession, job_id: int
) -> models.MaintenanceJob | None:
    return await db.get(models.MaintenanceJob, job_id)


async def update_job_status(
    db: AsyncSession, job_id: int, data: schemas.JobStatusPatch
) -> models.MaintenanceJob | None:
    job = await db.get(models.MaintenanceJob, job_id)
    if job is None:
        return None

    terminal = {models.JobStatus.COMPLETED, models.JobStatus.CANCELLED}
    if job.status in terminal:
        raise ValueError(f"Cannot transition out of terminal state '{job.status}'")

    if data.status == models.JobStatus.COMPLETED and data.outcome is None:
        raise ValueError("outcome is required when transitioning to 'completed'")

    if data.outcome is not None and data.status != models.JobStatus.COMPLETED:
        raise ValueError("outcome can only be set when transitioning to 'completed'")

    if data.post_job_condition is not None and data.status != models.JobStatus.COMPLETED:
        raise ValueError(
            "post_job_condition can only be set when transitioning to 'completed'"
        )

    job.status = data.status
    if data.status == models.JobStatus.COMPLETED:
        job.completed_at = datetime.now(timezone.utc)
    if data.outcome is not None:
        job.outcome = data.outcome
    if data.post_job_condition is not None:
        job.post_job_condition = data.post_job_condition

    await db.commit()
    return job
