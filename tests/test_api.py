import pytest
import io
import json
from app import db
from app.models import User, Role, APIKey, Researcher, Collaboration

def create_superadmin_with_key(app):
    with app.app_context():
        u = User(email=f'super_{User.query.count()}@api.com', is_verified=True, is_active=True)
        u.set_password('pass')
        r = Role.query.filter_by(name='SUPERADMIN').first()
        if not r:
            r = Role(name='SUPERADMIN')
        u.roles.append(r)
        db.session.add(u)
        db.session.commit()
        
        raw_key, prefix, key_hash = APIKey.generate_key()
        ak = APIKey(user_id=u.id, name="Test Key", prefix=prefix, key_hash=key_hash)
        db.session.add(ak)
        db.session.commit()
        
        return raw_key

def test_api_auth_missing(client):
    resp = client.get('/api/v1/admin/network')
    assert resp.status_code == 401

def test_api_auth_invalid(client):
    resp = client.get('/api/v1/admin/network', headers={'Authorization': 'Bearer rg_invalid_key'})
    assert resp.status_code == 401

def test_api_graph_endpoints(client, app):
    raw_key = create_superadmin_with_key(app)
    headers = {'Authorization': f'Bearer {raw_key}'}
    
    with app.app_context():
        r = Researcher(first_name='Albert', last_name='Einstein', display_name='Albert Einstein', slug='albert-einstein')
        db.session.add(r)
        db.session.commit()
    
    # Complete Network
    resp = client.get('/api/v1/admin/network', headers=headers)
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['meta']['total_nodes'] == 1
    
    # Individual Network
    resp = client.get('/api/v1/admin/researchers/albert-einstein/network', headers=headers)
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['data']['root_slug'] == 'albert-einstein'

def test_api_researcher_endpoints(client, app):
    raw_key = create_superadmin_with_key(app)
    headers = {'Authorization': f'Bearer {raw_key}'}
    
    with app.app_context():
        r = Researcher(first_name='Marie', last_name='Curie', display_name='Marie Curie', slug='marie-curie')
        db.session.add(r)
        db.session.commit()
        
    # Get researcher
    resp = client.get('/api/v1/admin/researchers/marie-curie', headers=headers)
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['data']['first_name'] == 'Marie'
    
    # Patch researcher
    resp = client.patch(
        '/api/v1/admin/researchers/marie-curie',
        headers=headers,
        json={'department': 'Physics'}
    )
    assert resp.status_code == 200
    assert json.loads(resp.data)['data']['department'] == 'Physics'
    
    # Search researchers
    resp = client.get('/api/v1/admin/researchers?q=Marie', headers=headers)
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data['data']) == 1
    
    # Delete researcher
    resp = client.delete('/api/v1/admin/researchers/marie-curie', headers=headers)
    assert resp.status_code == 204
    
    # Verify deleted
    resp = client.get('/api/v1/admin/researchers/marie-curie', headers=headers)
    assert resp.status_code == 404

def test_api_backup_restore(client, app):
    raw_key = create_superadmin_with_key(app)
    headers = {'Authorization': f'Bearer {raw_key}'}
    
    # Backup
    resp = client.post('/api/v1/admin/backup', headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get('Content-Disposition').startswith('attachment;')
    
    db_content = resp.data
    
    # Restore without header (fail)
    resp = client.post('/api/v1/admin/restore', headers=headers)
    assert resp.status_code == 400
    
    # Restore with header
    headers['X-Confirm-Restore'] = 'true'
    data = {
        'db_file': (io.BytesIO(db_content), 'test.db')
    }
    resp = client.post(
        '/api/v1/admin/restore',
        headers=headers,
        data=data,
        content_type='multipart/form-data'
    )
    assert resp.status_code == 200
