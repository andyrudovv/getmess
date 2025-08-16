from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from ..models import User
from ..schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserOut)
async def create_user(payload: UserCreate):
    async with get_session() as session:  # type: AsyncSession
        user = User(name=payload.name, email=payload.email)
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            return UserOut(id=user.id, name=user.name, email=user.email)
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    async with get_session() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserOut(id=user.id, name=user.name, email=user.email)
