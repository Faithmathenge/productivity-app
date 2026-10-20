from sqlalchemy import CheckConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

from extensions import bcrypt, db


def _require_text(value, label, max_length):
    """Strip a string and make sure it is non-blank and not too long."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{label} must be at most {max_length} characters.")
    return value


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(username)) >= 3", name="ck_users_username_min_length"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    _password_hash = db.Column("password_hash", db.String(128), nullable=False)

    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan")

    @hybrid_property
    def password_hash(self):
        raise AttributeError("Password hashes may not be viewed.")

    @password_hash.setter
    def password_hash(self, password):
        self._password_hash = bcrypt.generate_password_hash(password.encode("utf-8")).decode("utf-8")

    def authenticate(self, password):
        return bcrypt.check_password_hash(self._password_hash, password.encode("utf-8"))

    @validates("username")
    def validate_username(self, key, value):
        value = _require_text(value, "Username", 30)
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters.")
        return value

    def __repr__(self):
        return f"<User {self.id} {self.username}>"


class Note(db.Model):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_notes_title_not_blank"),
        CheckConstraint("length(trim(content)) > 0", name="ck_notes_content_not_blank"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="General")
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="notes")

    @validates("title")
    def validate_title(self, key, value):
        return _require_text(value, "Title", 100)

    @validates("content")
    def validate_content(self, key, value):
        return _require_text(value, "Content", 5000)

    @validates("category")
    def validate_category(self, key, value):
        return _require_text(value, "Category", 30)

    def __repr__(self):
        return f"<Note {self.id} {self.title}>"
    