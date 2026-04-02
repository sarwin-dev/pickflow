from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    user = User.query.filter_by(email='admin@pickflow.com').first()
    if user:
        user.password = generate_password_hash('Pinga123*')
        db.session.commit()
        print('Password updated successfully.')
    else:
        print('User not found.')
