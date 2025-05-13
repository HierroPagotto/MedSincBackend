from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config
from .database import db, init_db

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.url_map.strict_slashes = False

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["http://localhost:8080", "http://127.0.0.1:8080"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "supports_credentials": True,
                "expose_headers": ["Content-Disposition"],
            },
            r"/static/*": {
                "origins": ["http://localhost:8080", "http://127.0.0.1:8080"],
                "methods": ["GET", "OPTIONS"],
                "allow_headers": ["Content-Type"],
                "supports_credentials": True,
            },
        },
    )

    init_db(app)
    migrate.init_app(app, db)

    from app.routes import (
        auth_bp,
        doctor_bp,
        hospital_bp,
        shift_bp,
        payment_bp,
        static_bp,
    )

    app.register_blueprint(static_bp, url_prefix="/static")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(doctor_bp, url_prefix="/api/doctors/")
    app.register_blueprint(hospital_bp, url_prefix="/api/hospitals/")
    app.register_blueprint(shift_bp, url_prefix="/api/shifts/")
    app.register_blueprint(payment_bp, url_prefix="/api/payments/")

    return app
