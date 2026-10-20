import pytest
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Note, User


def add_user(username="alice"):
    user = User(username=username)
    user.password_hash = "password123"
    db.session.add(user)
    db.session.commit()
    return user


# ---------- model validations ----------

@pytest.mark.parametrize("username", ["", "  ", "ab", "x" * 31, None, 123])
def test_user_rejects_bad_usernames(username):
    with pytest.raises(ValueError):
        User(username=username)


def test_user_strips_username():
    assert User(username="  alice  ").username == "alice"


@pytest.mark.parametrize("field", ["title", "content", "category"])
@pytest.mark.parametrize("value", ["", "   ", None])
def test_note_rejects_blank_text(field, value):
    with pytest.raises(ValueError):
        Note(**{field: value})


def test_note_rejects_too_long_title():
    with pytest.raises(ValueError):
        Note(title="x" * 101)


# ---------- relationships ----------

def test_user_owns_notes(app):
    user = add_user()
    db.session.add_all([
        Note(title="One", content="a", user=user),
        Note(title="Two", content="b", user=user),
    ])
    db.session.commit()
    assert [n.title for n in user.notes] == ["One", "Two"]
    assert user.notes[0].user is user


def test_deleting_user_deletes_their_notes(app):
    user = add_user()
    db.session.add(Note(title="One", content="a", user=user))
    db.session.commit()
    db.session.delete(user)
    db.session.commit()
    assert Note.query.count() == 0


# ---------- table constraints (raw SQL bypasses the model validators) ----------

def test_db_enforces_unique_username(app):
    add_user("alice")
    with pytest.raises(IntegrityError):
        db.session.execute(db.text("INSERT INTO users (username, password_hash) VALUES ('alice', 'x')"))
    db.session.rollback()


def test_db_rejects_short_username(app):
    with pytest.raises(IntegrityError):
        db.session.execute(db.text("INSERT INTO users (username, password_hash) VALUES ('ab', 'x')"))
    db.session.rollback()


def test_db_requires_password_hash(app):
    with pytest.raises(IntegrityError):
        db.session.execute(db.text("INSERT INTO users (username) VALUES ('alice')"))
    db.session.rollback()


def test_db_rejects_blank_note_title(app):
    user = add_user()
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.text(
                "INSERT INTO notes (title, content, category, is_pinned, user_id) "
                f"VALUES ('  ', 'body', 'General', 0, {user.id})"
            )
        )
    db.session.rollback()


def test_db_requires_note_owner(app):
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.text(
                "INSERT INTO notes (title, content, category, is_pinned) "
                "VALUES ('t', 'body', 'General', 0)"
            )
        )
    db.session.rollback()
    