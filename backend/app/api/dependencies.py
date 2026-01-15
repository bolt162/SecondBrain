from uuid import UUID
from typing import Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import User


# For prototype: use a simple header-based "auth"
# In production, this would be proper JWT/session auth

DEFAULT_USER_EMAIL = "demo@secondbrain.app"


async def get_or_create_user(db: AsyncSession, email: str) -> User:
    """Get or create a user by email."""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_current_user_id(
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """
    Get the current user ID from the X-User-Email header.
    For prototype purposes, creates user if not exists.
    """
    email = x_user_email or DEFAULT_USER_EMAIL
    user = await get_or_create_user(db, email)
    return user.id


async def get_current_user(
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current user object."""
    email = x_user_email or DEFAULT_USER_EMAIL
    return await get_or_create_user(db, email)
