from flask import request
from flask_restful import Resource
from marshmallow import ValidationError

from extensions import db
from models import Note
from schemas import note_schema, notes_schema
from utils import current_user, handle_errors, json_body, login_required

DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 50


def pagination_args():
    """Read ?page= and ?per_page= from the query string."""
    errors, values = {}, {}
    for name, default in (("page", 1), ("per_page", DEFAULT_PER_PAGE)):
        try:
            value = int(request.args.get(name, default))
        except (TypeError, ValueError):
            errors[name] = ["Must be a whole number."]
            continue
        if value < 1:
            errors[name] = ["Must be at least 1."]
            continue
        values[name] = value
    if errors:
        raise ValidationError(errors)
    return values["page"], min(values["per_page"], MAX_PER_PAGE)


def find_own_note(note_id):
    """Look a note up by id, but only among the logged-in user's notes."""
    return Note.query.filter_by(id=note_id, user_id=current_user().id).first()


NOT_FOUND = ({"error": "Note not found"}, 404)


class NoteList(Resource):
    method_decorators = [handle_errors, login_required]

    def get(self):
        page, per_page = pagination_args()
        pagination = (
            Note.query.filter_by(user_id=current_user().id)
            .order_by(Note.created_at.desc(), Note.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
        return {
            "notes": notes_schema.dump(pagination.items),
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }, 200

    def post(self):
        data = note_schema.load(json_body())
        note = Note(user_id=current_user().id, **data)
        db.session.add(note)
        db.session.commit()
        return note_schema.dump(note), 201


class NoteDetail(Resource):
    method_decorators = [handle_errors, login_required]

    def get(self, note_id):
        note = find_own_note(note_id)
        if note is None:
            return NOT_FOUND
        return note_schema.dump(note), 200

    def patch(self, note_id):
        note = find_own_note(note_id)
        if note is None:
            return NOT_FOUND

        data = note_schema.load(json_body(), partial=True)
        if not data:
            raise ValidationError({"_schema": ["Provide at least one field to update."]})
        for field, value in data.items():
            setattr(note, field, value)
        db.session.commit()
        return note_schema.dump(note), 200

    def delete(self, note_id):
        note = find_own_note(note_id)
        if note is None:
            return NOT_FOUND
        db.session.delete(note)
        db.session.commit()
        return "", 204
    