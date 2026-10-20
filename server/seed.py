from random import choice, randint

from faker import Faker

from app import app
from extensions import db
from models import Note, User

fake = Faker()
CATEGORIES = ["Work", "Personal", "Ideas", "Study"]


def make_user(username, password):
    user = User(username=username)
    user.password_hash = password
    return user


def make_notes(user, count):
    return [
        Note(
            user=user,
            title=fake.sentence(nb_words=4).rstrip("."),
            content=fake.paragraph(nb_sentences=3),
            category=choice(CATEGORIES),
            is_pinned=randint(1, 5) == 1,
        )
        for _ in range(count)
    ]


def seed():
    with app.app_context():
        # Clear existing rows (notes first) so the seed can be re-run safely.
        Note.query.delete()
        User.query.delete()

        # A known login for trying the API: demo / password123
        users = [make_user("demo", "password123")]
        for _ in range(2):
            users.append(make_user(fake.unique.user_name()[:30], "password123"))
        db.session.add_all(users)

        # 12 notes each, so pagination (10 per page) has a second page.
        for user in users:
            db.session.add_all(make_notes(user, 12))

        db.session.commit()
        print(f"Seeded {len(users)} users and {Note.query.count()} notes.")
        print("Log in as 'demo' with password 'password123'.")


if __name__ == "__main__":
    seed()
    
