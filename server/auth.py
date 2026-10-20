from flask import session
from flask_restful import Resource

from extensions import db
from models import User
from schemas import login_schema, user_schema
from utils import current_user, handle_errors, json_body


class Signup(Resource):
    method_decorators = [handle_errors]

    def post(self):
        data = user_schema.load(json_body())
        user = User(username=data["username"])
        user.password_hash = data["password"]
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        return user_schema.dump(user), 201


class Login(Resource):
    method_decorators = [handle_errors]

    def post(self):
        data = login_schema.load(json_body())
        user = User.query.filter_by(username=data["username"].strip()).first()

        # Same message for unknown user and wrong password, so usernames can't be probed.
        if user is None or not user.authenticate(data["password"]):
            return {"error": "Invalid username or password"}, 401

        session["user_id"] = user.id
        return user_schema.dump(user), 200


class Logout(Resource):
    def delete(self):
        session.pop("user_id", None)
        return "", 204


class CheckSession(Resource):
    def get(self):
        user = current_user()
        if user is None:
            return {"error": "Unauthorized"}, 401
        return user_schema.dump(user), 200
    