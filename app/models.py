from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, List


class Base(DeclarativeBase):
    pass


class PromptGroup(Base):
    __tablename__ = "prompt_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    prompts: Mapped[List["Prompt"]] = relationship(
        "Prompt", back_populates="group", lazy="selectin"
    )


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("prompt_groups.id", ondelete="SET NULL"), nullable=True
    )
    feature_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("feature_descriptions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    group: Mapped[Optional["PromptGroup"]] = relationship(
        "PromptGroup", back_populates="prompts", lazy="selectin"
    )
    feature: Mapped[Optional["FeatureDescription"]] = relationship(
        "FeatureDescription", back_populates="prompts", lazy="selectin"
    )


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default")
    token_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FeatureDescription(Base):
    __tablename__ = "feature_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    prompts: Mapped[List["Prompt"]] = relationship(
        "Prompt", back_populates="feature", lazy="selectin"
    )
