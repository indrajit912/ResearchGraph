import pytest
from app import db
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

def test_rbac_moderator_cannot_change_roles(client, app):
    with app.app_context():
        create_user_with_role('user@test.com', 'testpass')
        create_user_with_role('mod@test.com', 'testpass', 'MODERATOR')
    
    login(client, 'mod@test.com', 'testpass')
    with app.app_context():
        target_uuid = User.query.filter_by(email='user@test.com').first().uuid
        
    response = client.post(f'/admin/users/{target_uuid}/roles', data={'roles': ['ADMIN']})
    assert response.status_code == 403

def test_rbac_admin_promotion_matrix(client, app):
    with app.app_context():
        create_user_with_role('admin@test.com', 'testpass', 'ADMIN')
        create_user_with_role('target_user@test.com', 'testpass')
        create_user_with_role('target_mod@test.com', 'testpass', 'MODERATOR')
        create_user_with_role('target_admin@test.com', 'testpass', 'ADMIN')
        create_user_with_role('target_super@test.com', 'testpass', 'SUPERADMIN')
    
    login(client, 'admin@test.com', 'testpass')
    
    with app.app_context():
        u_uuid = User.query.filter_by(email='target_user@test.com').first().uuid
        m_uuid = User.query.filter_by(email='target_mod@test.com').first().uuid
        a_uuid = User.query.filter_by(email='target_admin@test.com').first().uuid
        s_uuid = User.query.filter_by(email='target_super@test.com').first().uuid
        self_uuid = User.query.filter_by(email='admin@test.com').first().uuid

    # 1. Admin can promote user -> moderator
    resp = client.post(f'/admin/users/{u_uuid}/roles', data={'roles': ['MODERATOR']})
    assert resp.status_code == 302 # Success redirect
    
    # Reset target_user back to basic user
    with app.app_context():
        u = User.query.filter_by(uuid=u_uuid).first()
        u.roles = []
        db.session.commit()
    
    # 2. Admin cannot promote user -> admin
    resp = client.post(f'/admin/users/{u_uuid}/roles', data={'roles': ['ADMIN']})
    assert resp.status_code == 403
    
    # 3. Admin cannot give user -> superadmin
    resp = client.post(f'/admin/users/{u_uuid}/roles', data={'roles': ['SUPERADMIN']})
    assert resp.status_code == 403
    
    # 4. Admin can promote mod -> admin
    resp = client.post(f'/admin/users/{m_uuid}/roles', data={'roles': ['ADMIN']})
    assert resp.status_code == 302
    
    # 5. Admin cannot modify another admin
    resp = client.post(f'/admin/users/{a_uuid}/roles', data={'roles': ['MODERATOR']})
    assert resp.status_code == 403
    
    # 6. Admin cannot modify superadmin
    resp = client.post(f'/admin/users/{s_uuid}/roles', data={'roles': ['USER']})
    assert resp.status_code == 403
    
    # 7. Admin cannot change their own role
    resp = client.post(f'/admin/users/{self_uuid}/roles', data={'roles': ['SUPERADMIN']})
    assert resp.status_code == 403

def test_rbac_superadmin_matrix(client, app):
    with app.app_context():
        create_user_with_role('sup@test.com', 'testpass', 'SUPERADMIN')
        create_user_with_role('target_user@test.com', 'testpass')
            
    login(client, 'sup@test.com', 'testpass')
    
    with app.app_context():
        u_uuid = User.query.filter_by(email='target_user@test.com').first().uuid
        
    # Superadmin can promote to superadmin
    resp = client.post(f'/admin/users/{u_uuid}/roles', data={'roles': ['SUPERADMIN']})
    assert resp.status_code == 302
