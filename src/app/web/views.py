"""Server-rendered HTML pages."""

from flask import render_template

from ..extensions import db
from ..models import Task
from . import web_bp


@web_bp.get("/")
def index():
    tasks = db.session.scalars(db.select(Task).order_by(Task.id)).all()
    return render_template("index.html", tasks=tasks)
