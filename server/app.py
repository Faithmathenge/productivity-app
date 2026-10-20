import os

from flask import Flask
from flask_restful import Api

from auth import CheckSession, Login, Logout, Signup
from extensions import bcrypt, db, migrate
from notes import NoteDetail, NoteList


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URI", "sqlite:///app.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Signs the session cookie. Set a real value in the SECRET_KEY environment variable.
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    api = Api(app)
    api.add_resource(Signup, "/signup")
    api.add_resource(Login, "/login")
    api.add_resource(Logout, "/logout")
    api.add_resource(CheckSession, "/check_session")
    api.add_resource(NoteList, "/notes")
    api.add_resource(NoteDetail, "/notes/<int:note_id>")
    return app


app = create_app()
