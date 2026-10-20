import pytest


def make_note(client, **overrides):
    payload = {"title": "Groceries", "content": "Milk, eggs, bread"}
    payload.update(overrides)
    return client.post("/notes", json=payload)


# ---------- protected routes ----------

@pytest.mark.parametrize(
    "method, url",
    [
        ("get", "/notes"),
        ("post", "/notes"),
        ("get", "/notes/1"),
        ("patch", "/notes/1"),
        ("delete", "/notes/1"),
    ],
)
def test_routes_require_login(client, method, url):
    response = getattr(client, method)(url, json={"title": "x", "content": "y"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


def test_routes_unavailable_after_logout(logged_in):
    logged_in.delete("/logout")
    assert logged_in.get("/notes").status_code == 401


# ---------- create ----------

def test_create_note(logged_in):
    response = make_note(logged_in)
    assert response.status_code == 201
    note = response.get_json()
    assert note["title"] == "Groceries"
    assert note["category"] == "General"
    assert note["is_pinned"] is False
    assert note["created_at"]
    assert "user_id" not in note


def test_create_note_with_optional_fields(logged_in):
    note = make_note(logged_in, category="Work", is_pinned=True).get_json()
    assert note["category"] == "Work"
    assert note["is_pinned"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"content": "no title"},
        {"title": "no content"},
        {"title": "   ", "content": "blank title"},
        {"title": "blank content", "content": "  "},
        {"title": "x" * 101, "content": "too long title"},
        {"title": "ok", "content": "ok", "is_pinned": "banana"},
        {"title": "ok", "content": "ok", "user_id": 99},
    ],
)
def test_create_note_validation(logged_in, payload):
    assert logged_in.post("/notes", json=payload).status_code == 400


# ---------- read + ownership ----------

def test_get_note(logged_in):
    note_id = make_note(logged_in).get_json()["id"]
    response = logged_in.get(f"/notes/{note_id}")
    assert response.status_code == 200
    assert response.get_json()["title"] == "Groceries"


def test_get_missing_note(logged_in):
    assert logged_in.get("/notes/999").status_code == 404


def test_list_only_returns_own_notes(logged_in, second_client):
    make_note(logged_in, title="Alice note")
    make_note(second_client, title="Bob note")
    titles = [n["title"] for n in logged_in.get("/notes").get_json()["notes"]]
    assert titles == ["Alice note"]


def test_cannot_read_another_users_note(logged_in, second_client):
    bobs_id = make_note(second_client, title="Bob note").get_json()["id"]
    assert logged_in.get(f"/notes/{bobs_id}").status_code == 404


def test_cannot_edit_another_users_note(logged_in, second_client):
    bobs_id = make_note(second_client, title="Bob note").get_json()["id"]
    response = logged_in.patch(f"/notes/{bobs_id}", json={"title": "Hacked"})
    assert response.status_code == 404
    assert second_client.get(f"/notes/{bobs_id}").get_json()["title"] == "Bob note"


def test_cannot_delete_another_users_note(logged_in, second_client):
    bobs_id = make_note(second_client, title="Bob note").get_json()["id"]
    assert logged_in.delete(f"/notes/{bobs_id}").status_code == 404
    assert second_client.get(f"/notes/{bobs_id}").status_code == 200


# ---------- update ----------

def test_patch_updates_only_given_fields(logged_in):
    note_id = make_note(logged_in, category="Work").get_json()["id"]
    response = logged_in.patch(f"/notes/{note_id}", json={"title": "Renamed", "is_pinned": True})
    assert response.status_code == 200
    note = response.get_json()
    assert note["title"] == "Renamed"
    assert note["is_pinned"] is True
    assert note["content"] == "Milk, eggs, bread"
    assert note["category"] == "Work"


def test_patch_missing_note(logged_in):
    assert logged_in.patch("/notes/999", json={"title": "x"}).status_code == 404


@pytest.mark.parametrize("payload", [{}, {"title": "  "}, {"title": "x" * 101}, {"user_id": 2}])
def test_patch_validation(logged_in, payload):
    note_id = make_note(logged_in).get_json()["id"]
    assert logged_in.patch(f"/notes/{note_id}", json=payload).status_code == 400


def test_failed_patch_leaves_note_unchanged(logged_in):
    note_id = make_note(logged_in).get_json()["id"]
    logged_in.patch(f"/notes/{note_id}", json={"title": "  "})
    assert logged_in.get(f"/notes/{note_id}").get_json()["title"] == "Groceries"


# ---------- delete ----------

def test_delete_note(logged_in):
    note_id = make_note(logged_in).get_json()["id"]
    assert logged_in.delete(f"/notes/{note_id}").status_code == 204
    assert logged_in.get(f"/notes/{note_id}").status_code == 404


def test_delete_missing_note(logged_in):
    assert logged_in.delete("/notes/999").status_code == 404


# ---------- pagination ----------

@pytest.fixture
def twenty_five_notes(logged_in):
    for number in range(1, 26):
        make_note(logged_in, title=f"Note {number}")
    return logged_in


def test_list_is_paginated_by_default(twenty_five_notes):
    body = twenty_five_notes.get("/notes").get_json()
    assert len(body["notes"]) == 10
    assert (body["page"], body["per_page"], body["total"], body["pages"]) == (1, 10, 25, 3)


def test_list_newest_first(twenty_five_notes):
    titles = [n["title"] for n in twenty_five_notes.get("/notes").get_json()["notes"]]
    assert titles[0] == "Note 25"
    assert titles[-1] == "Note 16"


def test_last_page_has_remaining_notes(twenty_five_notes):
    body = twenty_five_notes.get("/notes?page=3").get_json()
    assert len(body["notes"]) == 5


def test_custom_per_page(twenty_five_notes):
    body = twenty_five_notes.get("/notes?page=2&per_page=20").get_json()
    assert len(body["notes"]) == 5
    assert body["pages"] == 2


def test_per_page_is_capped(twenty_five_notes):
    body = twenty_five_notes.get("/notes?per_page=500").get_json()
    assert body["per_page"] == 50
    assert len(body["notes"]) == 25


def test_page_past_the_end_is_empty(twenty_five_notes):
    response = twenty_five_notes.get("/notes?page=99")
    assert response.status_code == 200
    assert response.get_json()["notes"] == []


@pytest.mark.parametrize("query", ["page=0", "page=abc", "per_page=0", "per_page=-3", "per_page=x"])
def test_invalid_pagination_params(logged_in, query):
    assert logged_in.get(f"/notes?{query}").status_code == 400


def test_empty_list(logged_in):
    body = logged_in.get("/notes").get_json()
    assert body["notes"] == []
    assert body["total"] == 0
    