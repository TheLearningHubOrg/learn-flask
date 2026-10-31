"""JSON API for tasks, mounted at /api/v1."""

from __future__ import annotations

from flask import abort, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

from ..extensions import db
from ..models import Task
from . import api_bp


def _json_body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="request body must be a JSON object")
    return payload


def _parse_title(payload: dict, required: bool = True) -> str | None:
    title = payload.get("title")
    if title is None and not required:
        return None
    if not isinstance(title, str) or not title.strip():
        abort(400, description="'title' must be a non-empty string")
    if len(title.strip()) > 200:
        abort(400, description="'title' must be at most 200 characters")
    return title.strip()


@api_bp.get("/health")
def health():
    return {"status": "ok"}


@api_bp.get("/tasks")
def list_tasks():
    stmt = db.select(Task).order_by(Task.id)
    done = request.args.get("done")
    if done in {"true", "false"}:
        stmt = stmt.where(Task.done == (done == "true"))
    tasks = db.session.scalars(stmt).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.post("/tasks")
def create_task():
    task = Task(title=_parse_title(_json_body()))
    db.session.add(task)
    db.session.commit()
    headers = {"Location": url_for("api.get_task", task_id=task.id)}
    return task.to_dict(), 201, headers


@api_bp.get("/tasks/<int:task_id>")
def get_task(task_id: int):
    return db.get_or_404(Task, task_id).to_dict()


@api_bp.patch("/tasks/<int:task_id>")
def update_task(task_id: int):
    task = db.get_or_404(Task, task_id)
    payload = _json_body()
    title = _parse_title(payload, required=False)
    if title is not None:
        task.title = title
    if "done" in payload:
        if not isinstance(payload["done"], bool):
            abort(400, description="'done' must be a boolean")
        task.done = payload["done"]
    db.session.commit()
    return task.to_dict()


@api_bp.delete("/tasks/<int:task_id>")
def delete_task(task_id: int):
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return "", 204


@api_bp.errorhandler(HTTPException)
def json_error(err: HTTPException):
    """Return JSON instead of HTML for HTTP errors raised in this blueprint."""
    return {"error": err.name, "message": err.description}, err.code
