from functools import wraps

from flask import request, session
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User


def json_body():
    """Return the request's JSON object, or raise a validation error."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError({"_schema": ["Request body must be a JSON object."]})
    return data


def current_user():
    """The logged-in user (from the session cookie), or None."""
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return {"error": "Unauthorized"}, 401
        return view(*args, **kwargs)

    return wrapper


def handle_errors(view):
    """Turn validation/database errors into JSON responses.

    Flask-RESTful handles exceptions raised inside resources itself, so the
    mapping is applied per method instead of with app.errorhandler.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except ValueError as err:  # raised by the @validates methods on the models
            db.session.rollback()
            return {"errors": {"_model": [str(err)]}}, 400
        except IntegrityError as err:
            db.session.rollback()
            if "UNIQUE" in str(err.orig).upper():
                return {"errors": {"_database": ["That record already exists."]}}, 409
            return {"errors": {"_database": ["Database constraint violated."]}}, 400

    return wrapper
