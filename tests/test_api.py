import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_create_and_list_tasks(client):
    res = client.post("/api/v1/tasks", json={"title": "  Write the guide  "})
    assert res.status_code == 201
    body = res.get_json()
    assert body["title"] == "Write the guide"
    assert body["done"] is False
    assert res.headers["Location"].endswith(f"/api/v1/tasks/{body['id']}")

    listing = client.get("/api/v1/tasks").get_json()
    assert [t["title"] for t in listing] == ["Write the guide"]


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": 42}, {"title": "x" * 201}])
def test_create_rejects_bad_payload(client, payload):
    res = client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bad Request"


def test_non_json_body_is_rejected(client):
    res = client.post("/api/v1/tasks", data="title=x")
    assert res.status_code == 400


def test_missing_task_returns_json_404(client):
    res = client.get("/api/v1/tasks/999")
    assert res.status_code == 404
    assert res.get_json()["error"] == "Not Found"


def test_update_filter_and_delete(client):
    task_id = client.post("/api/v1/tasks", json={"title": "Ship it"}).get_json()["id"]
    client.post("/api/v1/tasks", json={"title": "Still open"})

    res = client.patch(f"/api/v1/tasks/{task_id}", json={"done": True})
    assert res.status_code == 200
    assert res.get_json()["done"] is True

    done = client.get("/api/v1/tasks?done=true").get_json()
    assert [t["id"] for t in done] == [task_id]

    assert client.patch(f"/api/v1/tasks/{task_id}", json={"done": "yes"}).status_code == 400
    assert client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404


def test_index_page_escapes_user_content(client):
    client.post("/api/v1/tasks", json={"title": "<b>escaped</b>"})
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "&lt;b&gt;escaped&lt;/b&gt;" in html
    assert "<b>escaped</b>" not in html


def test_session_transaction_seeds_state(client):
    with client.session_transaction() as sess:
        sess["theme"] = "dark"
    assert client.get("/").status_code == 200


def test_init_db_command(app):
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "Database tables created" in result.output


def test_factory_builds_isolated_apps():
    a = create_app("testing", SECRET_KEY="a")
    b = create_app("testing", SECRET_KEY="b")
    assert a is not b
    assert a.config["SECRET_KEY"] != b.config["SECRET_KEY"]
    assert {"api", "web"} <= set(a.blueprints)


def test_production_refuses_the_dev_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production", SECRET_KEY="dev-only-change-me")
    assert create_app("production", SECRET_KEY="x" * 64).config["SESSION_COOKIE_SECURE"] is True
