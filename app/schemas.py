from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Prompt Group ──

class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: Optional[str] = None


class GroupOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupListItem(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ── Prompt ──

class PromptCreate(BaseModel):
    name: str
    description: str
    template_text: str
    group_id: Optional[int] = None
    feature_id: Optional[int] = None


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_text: Optional[str] = None
    group_id: Optional[int] = None
    feature_id: Optional[int] = None


class PromptOut(BaseModel):
    id: int
    name: str
    description: str
    template_text: str
    group_id: Optional[int] = None
    feature_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptListItem(BaseModel):
    id: int
    name: str
    description: str
    group_id: Optional[int] = None
    feature_id: Optional[int] = None

    model_config = {"from_attributes": True}


class PromptExportItem(BaseModel):
    name: str
    description: str
    template_text: str


class ImportResult(BaseModel):
    imported: int
    skipped: int
    updated: int
    errors: list[str]


class PromptMoveRequest(BaseModel):
    group_id: Optional[int] = None


class GenerateRequest(BaseModel):
    prompt_id: int
    query: str


# ── API Token ──

class ApiTokenCreate(BaseModel):
    name: str = "Default"
    token_value: str


class ApiTokenUpdate(BaseModel):
    name: Optional[str] = None
    token_value: Optional[str] = None
    is_active: Optional[bool] = None


class ApiTokenOut(BaseModel):
    id: int
    name: str
    token_value: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenListItem(BaseModel):
    id: int
    name: str
    is_active: bool
    token_masked: str

    model_config = {"from_attributes": True}


# ── Feature Description ──

class FeatureCreate(BaseModel):
    name: str
    description_text: str


class FeatureUpdate(BaseModel):
    name: Optional[str] = None
    description_text: Optional[str] = None


class FeatureOut(BaseModel):
    id: int
    name: str
    description_text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeatureListItem(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
