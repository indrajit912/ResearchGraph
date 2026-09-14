import pytest
from app import db
from app.models.researcher import Researcher
from app.models.user import User
from app.models.role import Role

def login(client, email, password):
    return client.post('/auth/login', data=dict(
        email=email,
        password=password
    ), follow_redirects=True)

def create_user_with_role(email, password, role_name=None):
    u = User(email=email, is_verified=True, is_active=True)
    u.set_password(password)
    db.session.add(u)
    if role_name:
        r = Role.query.filter_by(name=role_name).first()
        u.roles.append(r)
    db.session.commit()
    return u

def test_researcher_creation_without_new_fields(client, app):
    with app.app_context():
        create_user_with_role('admin@test.com', 'testpass', 'MODERATOR')
    
    login(client, 'admin@test.com', 'testpass')
    
    # Create researcher WITHOUT new fields
    response = client.post('/admin/researchers/create', data={
        'first_name': 'Test',
        'last_name': 'NoFields',
        'is_active': 'y'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    with app.app_context():
        r = Researcher.query.filter_by(first_name='Test', last_name='NoFields').first()
        assert r is not None
        assert r.mathscinet_id is None
        assert r.math_genealogy_url is None

def test_researcher_creation_with_new_fields(client, app):
    with app.app_context():
        create_user_with_role('admin2@test.com', 'testpass', 'MODERATOR')
    
    login(client, 'admin2@test.com', 'testpass')
    
    # Create researcher WITH new fields
    response = client.post('/admin/researchers/create', data={
        'first_name': 'Test',
        'last_name': 'WithFields',
        'mathscinet_id': '123456',
        'math_genealogy_url': 'https://genealogy.math.ndsu.nodak.edu/id.php?id=12345',
        'is_active': 'y'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    with app.app_context():
        r = Researcher.query.filter_by(first_name='Test', last_name='WithFields').first()
        assert r is not None
        assert r.mathscinet_id == '123456'
        assert r.math_genealogy_url == 'https://genealogy.math.ndsu.nodak.edu/id.php?id=12345'
