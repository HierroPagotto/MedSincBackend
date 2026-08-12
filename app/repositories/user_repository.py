from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.utils.passwords import hash_password


class UserRepository:
    model = User

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        return (
            db.query(User)
            .filter(func.lower(User.email) == email.strip().lower())
            .first()
        )

    def create(
        self,
        db: Session,
        *,
        email: str,
        password: str,
        role: str,
        commit: bool = True,
        already_hashed: bool = False,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password=password if already_hashed else hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        if commit:
            db.commit()
            db.refresh(user)
        else:
            db.flush()
        return user

    def update_password(
        self, db: Session, user: User, new_password: str, commit: bool = True
    ) -> User:
        user.password = hash_password(new_password)
        if commit:
            db.commit()
            db.refresh(user)
        return user
