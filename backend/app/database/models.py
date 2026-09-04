"""
VERIFY-X 2.0 — SQLAlchemy ORM models for PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class VerificationRequestModel(Base):
    """A user's verification request."""
    __tablename__ = "verification_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type = Column(String(20), nullable=False, default="text")  # text, image
    original_input = Column(Text, nullable=False)
    language = Column(String(20), default="unknown")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processing_ms = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed

    # Relationships
    claim = relationship("ClaimModel", back_populates="verification_request", uselist=False, cascade="all, delete-orphan")
    verdict = relationship("VerdictModel", back_populates="verification_request", uselist=False, cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceModel", back_populates="verification_request", cascade="all, delete-orphan")
    model_predictions = relationship("ModelPredictionModel", back_populates="verification_request", cascade="all, delete-orphan")
    feedback = relationship("FeedbackModel", back_populates="verification_request", cascade="all, delete-orphan")


class ClaimModel(Base):
    """Normalized claim extracted from user input."""
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_request_id = Column(UUID(as_uuid=True), ForeignKey("verification_requests.id"), nullable=False)
    original_claim = Column(Text, nullable=False)
    normalized_claim = Column(Text, nullable=False)
    claim_hash = Column(String(64), index=True)  # For cache lookups
    claim_type = Column(String(50), default="other")
    entities = Column(JSON, default=list)
    dates = Column(JSON, default=list)
    locations = Column(JSON, default=list)
    numbers = Column(JSON, default=list)
    language = Column(String(20), default="unknown")
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequestModel", back_populates="claim")


class EvidenceModel(Base):
    """A piece of evidence retrieved and selected for verification."""
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_request_id = Column(UUID(as_uuid=True), ForeignKey("verification_requests.id"), nullable=False)
    evidence_id = Column(String(20), nullable=False)  # E1, E2, etc.
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)
    title = Column(Text, default="")
    url = Column(Text, default="")
    passage = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)
    relevance_score = Column(Float, default=0.0)
    stance = Column(String(20), default="NEUTRAL")  # SUPPORTS, REFUTES, NEUTRAL
    retriever = Column(String(50), default="")
    language = Column(String(20), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequestModel", back_populates="evidence_items")
    source = relationship("SourceModel", back_populates="evidence_items")


class SourceModel(Base):
    """A news/information source with credibility tier."""
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), default="")
    tier = Column(String(5), default="C")  # A, B, C
    category = Column(String(50), default="unknown")  # news, government, academic, blog, social
    trust_score = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence_items = relationship("EvidenceModel", back_populates="source")


class VerdictModel(Base):
    """Final verification verdict."""
    __tablename__ = "verdicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_request_id = Column(UUID(as_uuid=True), ForeignKey("verification_requests.id"), nullable=False, unique=True)
    verdict = Column(String(30), nullable=False)
    confidence = Column(Float, nullable=False)
    summary = Column(Text, default="")
    reasoning = Column(Text, default="")
    signals = Column(JSON, default=dict)  # VerificationSignals as JSON
    agreement = Column(JSON, default=dict)  # SourceAgreement as JSON
    timeline = Column(JSON, default=list)
    numerical_analysis = Column(JSON, nullable=True)
    image_analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequestModel", back_populates="verdict")


class ModelPredictionModel(Base):
    """Raw model prediction before verdict engine processing."""
    __tablename__ = "model_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_request_id = Column(UUID(as_uuid=True), ForeignKey("verification_requests.id"), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), default="")
    raw_prediction = Column(JSON, nullable=False)
    raw_confidence = Column(Float, default=0.0)
    calibrated_confidence = Column(Float, nullable=True)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequestModel", back_populates="model_predictions")


class FeedbackModel(Base):
    """User feedback on verification results."""
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_request_id = Column(UUID(as_uuid=True), ForeignKey("verification_requests.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    user_verdict = Column(String(30), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequestModel", back_populates="feedback")
