from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    is_group: bool = False
    participant_ids: List[int]

class ConversationOut(BaseModel):
    id: int
    title: Optional[str]
    is_group: bool
    participants: List[UserOut] | None = None

class MessageCreate(BaseModel):
    sender_id: int
    content: str

class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender_id: int | None
    content: str
    created_at: str
    status: str
