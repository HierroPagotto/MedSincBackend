from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    
    from app.models import Doctor, Shift, Hospital, Payment
    
    with app.app_context():
        db.create_all()