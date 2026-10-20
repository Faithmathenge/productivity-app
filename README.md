# Productivity App: Notes API

A Flask backend with session-based authentication and a user-owned resource (Notes). Users sign up, log in, and manage their own notes. Nobody can view or change another user's notes. Built with Flask, Flask-RESTful, SQLAlchemy, Flask-Migrate, Marshmallow and Flask-Bcrypt.

## Installation

```bash
git clone https://github.com/Faithmathenge/productivity-app.git
cd productivity-app
pipenv install --dev
pipenv shell
cd server
flask db init
flask db migrate -m "Create users and notes"
flask db upgrade
python seed.py
```

## Run

```bash
cd server
flask run -p 5555
```

The API runs at `http://127.0.0.1:5555`. Set a `SECRET_KEY` environment variable in production; the session cookie is signed with it.

After seeding you can log in as `demo` / `password123`.

## Tests

```bash
cd server
pytest
```

## Data model

- **User**: `username` (unique, 3-30 characters), password stored only as a bcrypt hash
- **Note**: `title`, `content`, `category`, `is_pinned`, `created_at`, belongs to a user

A user has many notes. Deleting a user deletes their notes.

## Endpoints

| Method | Route            | Auth | Description                                                                               | Success | Errors        |
| ------ | ---------------- | ---- | ----------------------------------------------------------------------------------------- | ------- | ------------- |
| POST   | `/signup`        | no   | Create an account and log in (`username`, `password`)                                     | 201     | 400, 409      |
| POST   | `/login`         | no   | Log in (`username`, `password`)                                                           | 200     | 400, 401      |
| DELETE | `/logout`        | no   | Log out                                                                                   | 204     |               |
| GET    | `/check_session` | no   | Return the logged-in user                                                                 | 200     | 401           |
| GET    | `/notes`         | yes  | List your notes, newest first. Query: `page` (default 1), `per_page` (default 10, max 50) | 200     | 400, 401      |
| POST   | `/notes`         | yes  | Create a note (`title`, `content`, optional `category`, `is_pinned`)                      | 201     | 400, 401      |
| GET    | `/notes/<id>`    | yes  | Get one of your notes                                                                     | 200     | 401, 404      |
| PATCH  | `/notes/<id>`    | yes  | Update any of the note's fields                                                           | 200     | 400, 401, 404 |
| DELETE | `/notes/<id>`    | yes  | Delete a note                                                                             | 204     | 401, 404      |

The paginated list returns `{"notes": [...], "page": 1, "per_page": 10, "total": 12, "pages": 2}`.

A note that belongs to another user returns `404`, the same as a note that doesn't exist, so other users' notes can't be discovered.

## Security notes

- Passwords are hashed with bcrypt and are never returned by the API.
- Login returns the same error for an unknown username and a wrong password.
- Every note route checks the session and filters notes by the logged-in user.
- Validations live at three levels: table constraints, model `@validates` methods, and Marshmallow schemas.

## Project structure

```
server/
├── app.py         # app factory and routes
├── extensions.py  # db, bcrypt, migrate
├── models.py      # User and Note models
├── schemas.py     # Marshmallow schemas
├── utils.py       # login_required, error handling, helpers
├── auth.py        # signup, login, logout, check_session
├── notes.py       # notes CRUD with pagination
├── seed.py        # example data (Faker)
└── tests/
```
