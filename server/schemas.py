from marshmallow import Schema, ValidationError, fields, validate, validates


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=30),
            validate.Regexp(
                r"^[A-Za-z0-9_.-]+$",
                error="Username may only contain letters, numbers, '.', '_' and '-'.",
            ),
        ],
    )
    # load_only: the password is accepted on signup but never returned.
    password = fields.Str(load_only=True, required=True, validate=validate.Length(min=8, max=72))

    @validates("password")
    def validate_password_bytes(self, value):
        # bcrypt only uses the first 72 bytes, so reject anything longer.
        if len(value.encode("utf-8")) > 72:
            raise ValidationError("Password is too long (72 bytes maximum).")


class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class NoteSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    category = fields.Str(validate=validate.Length(min=1, max=30))
    is_pinned = fields.Bool()
    created_at = fields.DateTime(dump_only=True)

    @validates("title")
    def validate_title(self, value):
        if not value.strip():
            raise ValidationError("Title cannot be blank.")

    @validates("content")
    def validate_content(self, value):
        if not value.strip():
            raise ValidationError("Content cannot be blank.")


user_schema = UserSchema()
login_schema = LoginSchema()
note_schema = NoteSchema()
notes_schema = NoteSchema(many=True)
