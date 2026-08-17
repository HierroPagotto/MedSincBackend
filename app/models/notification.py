from datetime import datetime as dt

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

TYPE_SHIFT_TOMORROW = "shift_tomorrow"
TYPE_PAYMENT_PENDING = "payment_pending"
TYPE_GOAL_PROGRESS = "goal_progress"
TYPE_SCHEDULE_CONFLICT = "schedule_conflict"
TYPE_APPLICATION_APPROVED = "application_approved"
TYPE_APPLICATION_REJECTED = "application_rejected"
TYPE_NEW_APPLICATION = "new_application"
TYPE_OPPORTUNITY_FILLED = "opportunity_filled"


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "read_at", "created_at"),
        Index("ix_notifications_dedupe", "user_id", "type", "dedupe_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
    dedupe_key = Column(String(191), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "data": self.data or {},
            "dedupe_key": self.dedupe_key,
            "read_at": (
                self.read_at.isoformat()
                if isinstance(self.read_at, dt)
                else self.read_at
            ),
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, dt)
                else self.created_at
            ),
            "is_read": self.read_at is not None,
        }
