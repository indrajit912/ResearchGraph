import pytest
from app.models import User
from app.extensions import db

def test_user_registration(client, app):
    response = client.post('/auth/register', data={
        'email': 'test@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.check_password('password123')
