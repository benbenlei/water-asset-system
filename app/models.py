"""ORM models for the water asset system.

Demonstrates:
  - Classes + inheritance (Asset -> Pump / Pipe / Valve)
  - SQLAlchemy single-table inheritance (≈ EF Core's Table-Per-Hierarchy)
  - A relationship (Asset 1 --- * Inspection)
  - A polymorphic domain method (risk_score) overridden per subtype
  - Type hints throughout (Mapped[...] is the 2.0 idiom)
"""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import ForeignKey, String, desc, nulls_last
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class AssetStatus(str, enum.Enum):
    """A C# enum equivalent. Subclassing `str` makes it serialize nicely."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class JobStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Outcome(str, enum.Enum):
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    DEFERRED = "deferred"


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    # 1 = excellent ... 5 = critical
    condition_score: Mapped[int]
    notes: Mapped[str | None] = mapped_column(default=None)
    inspected_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    asset: Mapped[Asset] = relationship(back_populates="inspections")


class MaintenanceJob(Base):
    __tablename__ = "maintenance_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    inspection_id: Mapped[int | None] = mapped_column(
        ForeignKey("inspections.id"), default=None
    )
    assigned_to: Mapped[str]
    scheduled_date: Mapped[date]
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.SCHEDULED)
    outcome: Mapped[Outcome | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    # Technician-observed condition on completion (1=excellent, 5=critical).
    # When set, overrides Inspection-based condition in risk_score().
    post_job_condition: Mapped[int | None] = mapped_column(default=None)

    asset: Mapped[Asset] = relationship(back_populates="maintenance_jobs")
    inspection: Mapped[Inspection | None] = relationship()


class Asset(Base):
    """Base asset. All subtypes live in this one table (single-table
    inheritance), discriminated by the `asset_type` column."""
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    asset_type: Mapped[str] = mapped_column(String(20))  # discriminator
    status: Mapped[AssetStatus] = mapped_column(default=AssetStatus.ACTIVE)
    zone: Mapped[str | None] = mapped_column(default=None)
    installed_date: Mapped[date] = mapped_column(default=date.today)

    inspections: Mapped[list[Inspection]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="Inspection.inspected_at.desc()",
    )
    maintenance_jobs: Mapped[list[MaintenanceJob]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by=lambda: nulls_last(desc(MaintenanceJob.completed_at)),
    )

    __mapper_args__ = {
        "polymorphic_on": "asset_type",
        "polymorphic_identity": "asset",
        # Always load subclass columns (flow_rate_lps, length_m, ...) in the
        # same query. Without this, single-table inheritance DEFERS them, and
        # touching one later triggers a lazy load that fails under async.
        "with_polymorphic": "*",
    }

    def latest_condition(self) -> int:
        """Most recent inspection score, or 1 (excellent) if never inspected.

        NOTE: reads self.inspections, so callers must eager-load that
        relationship (selectinload) — lazy loading does not work under async.
        """
        if not self.inspections:
            return 1
        return self.inspections[0].condition_score  # ordered desc by date

    def _effective_condition(self) -> int:
        """Condition from the most recent completed job (if post_job_condition
        is set AND the job closed more recently than the latest inspection),
        otherwise the latest inspection score.

        NOTE: reads self.maintenance_jobs and self.inspections — callers must
        eager-load both relationships.
        """
        for job in self.maintenance_jobs:
            if job.status == JobStatus.COMPLETED and job.post_job_condition is not None:
                latest_insp = self.inspections[0] if self.inspections else None
                # Strip tzinfo before comparing — SQLite returns naive datetimes
                # even when values were stored as UTC-aware.
                job_at = job.completed_at.replace(tzinfo=None)
                insp_at = latest_insp.inspected_at.replace(tzinfo=None) if latest_insp else None
                if insp_at is None or job_at >= insp_at:
                    return job.post_job_condition
                break  # most-recent completed job predates latest inspection; use inspection
        return self.latest_condition()

    def risk_score(self) -> float:
        """Higher = more urgent maintenance. Overridden per subtype.

        This is the polymorphism payoff: list mixed assets, call
        risk_score() on each, and the right subclass logic runs.
        """
        return self._effective_condition() * 10.0


class Pump(Asset):
    # Subtype columns must be nullable under single-table inheritance,
    # because pipes/valves share the same physical table.
    flow_rate_lps: Mapped[float | None] = mapped_column(default=None)
    power_kw: Mapped[float | None] = mapped_column(default=None)

    __mapper_args__ = {"polymorphic_identity": "pump"}

    def risk_score(self) -> float:
        # Pumps are active equipment: high-throughput pumps failing is worse.
        base = super().risk_score()
        load_factor = 1.5 if (self.flow_rate_lps or 0) > 100 else 1.0
        return base * load_factor


class Pipe(Asset):
    length_m: Mapped[float | None] = mapped_column(default=None)
    # Pipe and Valve both have a diameter -> they share ONE physical column.
    # use_existing_column avoids a "column already exists" clash.
    diameter_mm: Mapped[int | None] = mapped_column(
        default=None, use_existing_column=True
    )
    material: Mapped[str | None] = mapped_column(default=None)

    __mapper_args__ = {"polymorphic_identity": "pipe"}

    def risk_score(self) -> float:
        # Long mains are costly/disruptive to dig up, so weight by length.
        base = super().risk_score()
        return base + (self.length_m or 0) * 0.05


class Valve(Asset):
    valve_kind: Mapped[str | None] = mapped_column(default=None)  # gate/ball/...
    diameter_mm: Mapped[int | None] = mapped_column(
        default=None, use_existing_column=True
    )

    __mapper_args__ = {"polymorphic_identity": "valve"}

    # Inherits the base risk_score unchanged — that's fine and intentional.
