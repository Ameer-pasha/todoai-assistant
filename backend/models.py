from pydantic import BaseModel
from typing import Optional
from datetime import date


# ─── Task Models ───

class TaskCreate(BaseModel):
    title: str
    tag: str = "personal"
    due_date: Optional[str] = None
    priority: int = 3


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    tag: Optional[str] = None
    done: Optional[bool] = None
    due_date: Optional[str] = None
    priority: Optional[int] = None


class TaskOut(BaseModel):
    id: int
    title: str
    tag: str
    done: bool
    due_date: Optional[str] = None
    priority: int
    created_at: str


# ─── Chat Models ───

class ChatMessageIn(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessageIn] = []


class ChatResponse(BaseModel):
    type: str                          # "action" or "text"
    action: Optional[str] = None
    message: str
    filter: Optional[str] = None
    refresh: bool = False
