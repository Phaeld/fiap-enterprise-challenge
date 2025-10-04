from flask import Blueprint, render_template
from ..extensions import db
from ..models import Leitura

views = Blueprint("views", __name__, template_folder="template", static_folder="static")

@views.get("/")
def home():
    total = db.session.query(Leitura).count()
    return render_template("dashboard.html", total_leituras=total)
