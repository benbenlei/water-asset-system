"""Pydantic schemas = your request/response DTOs with built-in validation.

FastAPI uses these for model binding (request body) and serialization
(response). `Field(ge=1, le=5)` is declarative validation, like data
annotations ([Range(1,5)]) in ASP.NET.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import AssetStatus


# ----- Inspections ---------------------------------------------------------
class InspectionCreate(BaseModel):
    condition_score: int = Field(ge=1, le=5, description="1=excellent, 5=critical")
    notes: str | None = None


class InspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read straight off ORM objs

    id: int
    condition_score: int
    notes: str | None
    inspected_at: datetime


# ----- Assets: shared read shape -------------------------------------------
class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    asset_type: str
    status: AssetStatus
    zone: str | None
    installed_date: date


# ----- Per-type create payloads --------------------------------------------
class PumpCreate(BaseModel):
    name: str
    zone: str | None = None
    installed_date: date | None = None
    flow_rate_lps: float | None = Field(default=None, gt=0)
    power_kw: float | None = Field(default=None, gt=0)


class PipeCreate(BaseModel):
    name: str
    zone: str | None = None
    installed_date: date | None = None
    length_m: float | None = Field(default=None, gt=0)
    diameter_mm: int | None = Field(default=None, gt=0)
    material: str | None = None


class ValveCreate(BaseModel):
    name: str
    zone: str | None = None
    installed_date: date | None = None
    valve_kind: str | None = None
    diameter_mm: int | None = Field(default=None, gt=0)


# ----- Health response ------------------------------------------------------
class AssetHealth(BaseModel):
    asset_id: int
    asset_type: str
    latest_condition: int
    risk_score: float
    inspections_count: int
