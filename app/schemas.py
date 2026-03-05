from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PromptCreate(BaseModel):
    name: str
    description: str
    template_text: str


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_text: Optional[str] = None


class PromptOut(BaseModel):
    id: int
    name: str
    description: str
    template_text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptListItem(BaseModel):
    id: int
    name: str
    description: str

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    prompt_id: int
    query: str
