from app import create_app, db
from app.routes.admin import admin_bp

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.register_blueprint(admin_bp)
    app.run(debug=True)