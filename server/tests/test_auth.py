import pytest

from extensions import db
from models import User


def signup(client, username="alice", password="password123", **extra):
    return client.post("/signup", json={"username": username, "password": password, **extra})


# ---------- signup ----------

def test_signup_creates_user_and_logs_in(client):
    response = signup(client)
    assert response.status_code == 201
    body = response.get_json()
    assert body["username"] == "alice"
    assert "id" in body
    assert client.get("/check_session").status_code == 200


def test_signup_never_returns_password_or_hash(client):
    body = signup(client).get_json()
    assert "password" not in body
    assert "password_hash" not in body
    assert "_password_hash" not in body


def test_signup_duplicate_username(client, app):
    signup(client)
    response = signup(app.test_client())
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "password123"},
        {"username": "alice"},
        {"username": "ab", "password": "password123"},
        {"username": "   ", "password": "password123"},
        {"username": "bad name!", "password": "password123"},
        {"username": "alice", "password": "short"},
        {"username": "alice", "password": "x" * 73},
        {"username": "alice", "password": "é" * 40},
        {"username": "alice", "password": "password123", "id": 5},
    ],
)
def test_signup_validation(client, payload):
    assert client.post("/signup", json=payload).status_code == 400


def test_signup_requires_json_object(client):
    assert client.post("/signup", data="nope").status_code == 400
    assert client.post("/signup", json=["a"]).status_code == 400


# ---------- password protection ----------

def test_password_is_stored_hashed(client):
    signup(client)
    user = User.query.filter_by(username="alice").one()
    assert user._password_hash != "password123"
    assert user._password_hash.startswith("$2")
    assert user.authenticate("password123") is True
    assert user.authenticate("wrong-password") is False


def test_password_hash_cannot_be_read(client):
    signup(client)
    user = User.query.filter_by(username="alice").one()
    with pytest.raises(AttributeError):
        user.password_hash


# ---------- login ----------

def test_login_success(client, app):
    signup(client)
    fresh = app.test_client()
    response = fresh.post("/login", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    assert response.get_json()["username"] == "alice"
    assert fresh.get("/check_session").status_code == 200


def test_login_wrong_password(client, app):
    signup(client)
    fresh = app.test_client()
    response = fresh.post("/login", json={"username": "alice", "password": "nope-nope"})
    assert response.status_code == 401
    assert fresh.get("/check_session").status_code == 401


def test_login_unknown_user_gives_same_error(client, app):
    signup(client)
    fresh = app.test_client()
    wrong_pw = fresh.post("/login", json={"username": "alice", "password": "nope-nope"})
    no_user = fresh.post("/login", json={"username": "ghost", "password": "nope-nope"})
    assert no_user.status_code == 401
    assert no_user.get_json() == wrong_pw.get_json()


def test_login_missing_fields(client):
    assert client.post("/login", json={"username": "alice"}).status_code == 400
    assert client.post("/login", json={}).status_code == 400


# ---------- check_session / logout ----------

def test_check_session_when_logged_out(client):
    response = client.get("/check_session")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


def test_check_session_persists_across_requests(logged_in):
    for _ in range(3):
        response = logged_in.get("/check_session")
        assert response.status_code == 200
        assert response.get_json()["username"] == "alice"


def test_logout_ends_session(logged_in):
    assert logged_in.delete("/logout").status_code == 204
    assert logged_in.get("/check_session").status_code == 401


def test_logout_when_not_logged_in(client):
    assert client.delete("/logout").status_code == 204


def test_session_for_deleted_user_is_rejected(logged_in):
    User.query.filter_by(username="alice").delete()
    db.session.commit()
    assert logged_in.get("/check_session").status_code == 401
    