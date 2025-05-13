from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date


class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: int

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int]


class TaskBase(BaseModel):
    title: str

class TaskCreate(TaskBase):
    due_date: Optional[date] = None

class TaskResponse(TaskBase):
    id: int
    completed: bool
    user_id: int
    create_date: date
    due_date: date
    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    id: int
    action: str
    timestamp: datetime
    model_config = {"from_attributes": True}


class UserDetail(UserResponse):
    tasks: List[TaskResponse] = []
    history: List[HistoryResponse] = []
