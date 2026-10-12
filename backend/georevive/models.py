"""Database tables. Spatial features live in the GeoPackage; these tables hold
registry, lineage, users, rescued facts, model runs and the audit trail."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


SOURCE_STATUSES = ("downloaded", "partial", "failed", "needs_manual_request", "needs_credentials")
ROLES = ("admin", "geologist", "analyst", "investor", "miner")
FACT_STATUSES = ("pending", "approved", "rejected", "edited")


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # connector key, e.g. "usgs_mrds"
    name: Mapped[str] = mapped_column(String(255))
    publisher: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    urls_tried: Mapped[list[Any]] = mapped_column(JSON, default=list)
    licence: Mapped[str] = mapped_column(Text, default="licence to confirm")
    licence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bbox: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raster_size: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="failed")
    note: Mapped[str] = mapped_column(Text, default="")
    usage: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    how_to_obtain: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_inbox: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    files: Mapped[list[SourceFile]] = relationship(back_populates="source", cascade="all, delete-orphan")
    layers: Mapped[list[Layer]] = relationship(back_populates="source", cascade="all, delete-orphan")


class SourceFile(Base):
    __tablename__ = "source_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(Text)  # relative to project root
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(Integer)
    source: Mapped[Source] = relationship(back_populates="files")


class Layer(Base):
    __tablename__ = "layers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "geology", "s2_iron_oxide"
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    group: Mapped[str] = mapped_column(String(64), default="context")
    kind: Mapped[str] = mapped_column(String(16))  # vector | raster
    gpkg_table: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raster_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlay_png: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlay_bounds: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    geometry_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    feature_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attribution: Mapped[str] = mapped_column(Text, default="")
    legend: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    style: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    derived_from: Mapped[list[Any]] = mapped_column(JSON, default=list)  # lineage
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[Source] = relationship(back_populates="layers")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(Text)
    organisation: Mapped[str] = mapped_column(String(128), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Share(Base):
    """Data-room share: grants a user access to a layer (dataset)."""

    __tablename__ = "shares"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layer_id: Mapped[str] = mapped_column(ForeignKey("layers.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    granted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    username: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(32), index=True)
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    title: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(Text)
    original_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    pages: Mapped[list[Page]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(Integer)  # 1-based
    original_image: Mapped[str] = mapped_column(Text)
    steps: Mapped[list[Any]] = mapped_column(JSON, default=list)  # [{name, path, params}]
    enhanced_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    quality_before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    quality_after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ocr_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    document: Mapped[Document] = relationship(back_populates="pages")
    words: Mapped[list[OcrWord]] = relationship(back_populates="page", cascade="all, delete-orphan")
    facts: Mapped[list[Fact]] = relationship(back_populates="page", cascade="all, delete-orphan")


class OcrWord(Base):
    __tablename__ = "ocr_words"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    conf: Mapped[float] = mapped_column(Float)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    w: Mapped[int] = mapped_column(Integer)
    h: Mapped[int] = mapped_column(Integer)
    line: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[Page] = relationship(back_populates="words")


class Fact(Base):
    __tablename__ = "facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    value: Mapped[str] = mapped_column(Text)
    units: Mapped[str | None] = mapped_column(String(32), nullable=True)
    normalized: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    context: Mapped[str] = mapped_column(Text, default="")
    bbox: Mapped[list[int]] = mapped_column(JSON)  # [x, y, w, h] in page pixels
    confidence: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(128))
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocode_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_uncertain: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    page: Mapped[Page] = relationship(back_populates="facts")
    reviews: Mapped[list[FactReview]] = relationship(back_populates="fact", cascade="all, delete-orphan")


class FactReview(Base):
    __tablename__ = "fact_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"))
    username: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))
    before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    comment: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    fact: Mapped[Fact] = relationship(back_populates="reviews")


class ModelWeights(Base):
    """Knowledge-driven model weights, editable by the geologist (versioned)."""

    __tablename__ = "model_weights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity: Mapped[str] = mapped_column(String(32))
    weights: Mapped[dict[str, Any]] = mapped_column(JSON)
    username: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelRun(Base):
    __tablename__ = "model_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity: Mapped[str] = mapped_column(String(32))
    method: Mapped[str] = mapped_column(String(32))  # fuzzy | logistic | gbm
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    features: Mapped[list[Any]] = mapped_column(JSON, default=list)  # lineage of evidence layers
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    grid_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlay_png: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlay_bounds: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    username: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    targets: Mapped[list[Target]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Target(Base):
    __tablename__ = "targets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    cell_row: Mapped[int] = mapped_column(Integer)
    cell_col: Mapped[int] = mapped_column(Integer)
    lon: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    polygon: Mapped[dict[str, Any]] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)
    contributions: Mapped[list[Any]] = mapped_column(JSON, default=list)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    run: Mapped[ModelRun] = relationship(back_populates="targets")


class ClaimReport(Base):
    __tablename__ = "claim_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    polygon: Mapped[dict[str, Any]] = mapped_column(JSON)
    run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    pdf_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
