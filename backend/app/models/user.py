from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """A signed-in ClipForge user.

    id is the Google OAuth `sub` claim (stable, unique per Google account) —
    using it directly as the primary key avoids a separate identity mapping.
    """

    __tablename__ = "users"

    id = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    picture = Column(String(1024), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
