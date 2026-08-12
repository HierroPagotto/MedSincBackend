from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)

    with app.app_context():
        from app.utils.auth_bootstrap import ensure_auth_schema

        ensure_auth_schema()
