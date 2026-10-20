import pytest

from app import create_app
from extensions import db


@pytest.fixture
def app():
    """A fresh app backed by an in-memory database."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
            "BCRYPT_LOG_ROUNDS": 4,  # fast hashing for tests
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client; it keeps cookies, so it behaves like one browser."""
    return app.test_client()


@pytest.fixture
def logged_in(client):
    """A client that has already signed up (and so is logged in) as 'alice'."""
    client.post("/signup", json={"username": "alice", "password": "password123"})
    return client


@pytest.fixture
def second_client(app):
    """A second browser, for testing that users can't see each other's data."""
    client = app.test_client()
    client.post("/signup", json={"username": "bob", "password": "password123"})
    return client
