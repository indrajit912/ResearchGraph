from flask import Blueprint, jsonify, request, current_app, send_file
from functools import wraps
from datetime import datetime, timezone
import os

from app.extensions import db
from app.models import APIKey, Researcher, Collaboration, User

admin_api_bp = Blueprint('admin_api', __name__)

def require_admin_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Missing or invalid Authorization header'}}), 401
            
        raw_key = auth_header.split(' ')[1]
        
        if not raw_key.startswith('rg_') or len(raw_key.split('_')) != 3:
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid API key format'}}), 401
            
        parts = raw_key.split('_')
        prefix = parts[1]
        
        api_key = APIKey.query.filter_by(prefix=prefix).first()
        if not api_key or not api_key.check_key(raw_key):
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid API key'}}), 401
            
        if not api_key.is_valid:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'API key is expired or revoked'}}), 403
            
        if not api_key.user.has_role('SUPERADMIN'):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'API key owner lacks required privileges'}}), 403
            
        # Update last_used_at
        api_key.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Attach user to request for audit logging if needed
        request.api_user = api_key.user
        return f(*args, **kwargs)
        
    return decorated_function

def _serialize_researcher(r):
    return {
        "id": r.uuid,
        "first_name": r.first_name,
        "middle_name": r.middle_name,
        "last_name": r.last_name,
        "display_name": r.display_name,
        "slug": r.slug,
        "affiliation": r.affiliation,
        "department": r.department,
        "address": r.address,
        "city": r.city,
        "state": r.state,
        "country": r.country,
        "phd_institute": r.phd_institute,
        "phd_year": r.phd_year,
        "website": r.website,
        "orcid": r.orcid,
        "arxiv_id": r.arxiv_id,
        "google_scholar_url": r.google_scholar_url,
        "mathscinet_id": r.mathscinet_id,
        "math_genealogy_url": r.math_genealogy_url,
        "research_interests": r.research_interests,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }

@admin_api_bp.route('/network', methods=['GET'])
@require_admin_api_key
def get_complete_network():
    # Complete public research-network graph
    active_researchers = Researcher.query.filter_by(is_active=True).all()
    active_ids = [r.uuid for r in active_researchers]
    
    collabs = Collaboration.query.filter(
        Collaboration.researcher_a_id.in_(active_ids),
        Collaboration.researcher_b_id.in_(active_ids)
    ).all()
    
    nodes = [_serialize_researcher(r) for r in active_researchers]
    links = [{
        "source": c.researcher_a_id,
        "target": c.researcher_b_id,
        "status": c.status.name,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in collabs]
    
    return jsonify({
        "data": {
            "nodes": nodes,
            "links": links
        },
        "meta": {
            "total_nodes": len(nodes),
            "total_links": len(links)
        }
    })

@admin_api_bp.route('/researchers/<slug>/network', methods=['GET'])
@require_admin_api_key
def get_researcher_network(slug):
    root_researcher = Researcher.query.filter_by(slug=slug).first()
    if not root_researcher:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Researcher not found'}}), 404
        
    collabs = Collaboration.query.filter(
        (Collaboration.researcher_a_id == root_researcher.uuid) | 
        (Collaboration.researcher_b_id == root_researcher.uuid)
    ).all()
    
    connected_ids = set([root_researcher.uuid])
    for c in collabs:
        connected_ids.add(c.researcher_a_id)
        connected_ids.add(c.researcher_b_id)
        
    connected_researchers = Researcher.query.filter(Researcher.uuid.in_(connected_ids)).all()
    
    nodes = [_serialize_researcher(r) for r in connected_researchers]
    links = [{
        "source": c.researcher_a_id,
        "target": c.researcher_b_id,
        "status": c.status.name,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in collabs]
    
    return jsonify({
        "data": {
            "root_slug": slug,
            "nodes": nodes,
            "links": links
        }
    })

@admin_api_bp.route('/researchers/<slug>', methods=['GET'])
@require_admin_api_key
def get_researcher(slug):
    r = Researcher.query.filter_by(slug=slug).first()
    if not r:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Researcher not found'}}), 404
        
    return jsonify({"data": _serialize_researcher(r)})

@admin_api_bp.route('/researchers', methods=['GET'])
@require_admin_api_key
def list_researchers():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    if page_size > 100: page_size = 100
    
    query = Researcher.query
    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            (Researcher.first_name.ilike(search_pattern)) |
            (Researcher.last_name.ilike(search_pattern)) |
            (Researcher.display_name.ilike(search_pattern)) |
            (Researcher.affiliation.ilike(search_pattern))
        )
        
    paginated = query.order_by(Researcher.last_name).paginate(page=page, per_page=page_size, error_out=False)
    
    return jsonify({
        "data": [_serialize_researcher(r) for r in paginated.items],
        "meta": {
            "page": paginated.page,
            "page_size": paginated.per_page,
            "total_pages": paginated.pages,
            "total_records": paginated.total
        }
    })

@admin_api_bp.route('/researchers/<slug>', methods=['PATCH'])
@require_admin_api_key
def update_researcher(slug):
    r = Researcher.query.filter_by(slug=slug).first()
    if not r:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Researcher not found'}}), 404
        
    data = request.get_json()
    if not data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'JSON payload required'}}), 400
        
    allowed_fields = [
        'first_name', 'middle_name', 'last_name', 'affiliation', 'department',
        'address', 'city', 'state', 'country', 'phd_institute', 'phd_year',
        'website', 'orcid', 'arxiv_id', 'google_scholar_url', 'mathscinet_id',
        'math_genealogy_url', 'research_interests', 'is_active'
    ]
    
    for field in allowed_fields:
        if field in data:
            setattr(r, field, data[field])
            
    # Auto-generate display name if names changed
    if any(k in data for k in ('first_name', 'middle_name', 'last_name')):
        display_name = f"{r.first_name} {r.last_name}"
        if r.middle_name:
            display_name = f"{r.first_name} {r.middle_name} {r.last_name}"
        r.display_name = display_name
            
    db.session.commit()
    return jsonify({"data": _serialize_researcher(r)})

@admin_api_bp.route('/researchers/<slug>', methods=['DELETE'])
@require_admin_api_key
def delete_researcher(slug):
    r = Researcher.query.filter_by(slug=slug).first()
    if not r:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Researcher not found'}}), 404
        
    # Same deletion logic as the admin dashboard to prevent orphaned references
    from app.models.report import CollaborationReport, ResearcherCorrectionReport
    
    collabs = Collaboration.query.filter(
        (Collaboration.researcher_a_id == r.uuid) | (Collaboration.researcher_b_id == r.uuid)
    ).all()
    collab_ids = [c.id for c in collabs]
    if collab_ids:
        CollaborationReport.query.filter(CollaborationReport.collaboration_id.in_(collab_ids)).delete(synchronize_session=False)
        Collaboration.query.filter(Collaboration.id.in_(collab_ids)).delete(synchronize_session=False)
    
    ResearcherCorrectionReport.query.filter_by(researcher_id=r.uuid).delete(synchronize_session=False)
    
    db.session.delete(r)
    db.session.commit()
    
    return jsonify({}), 204

@admin_api_bp.route('/users', methods=['GET'])
@require_admin_api_key
def list_users():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    if page_size > 100: page_size = 100
    
    paginated = User.query.order_by(User.id).paginate(page=page, per_page=page_size, error_out=False)
    
    users_data = []
    for u in paginated.items:
        users_data.append({
            "id": u.id,
            "uuid": u.uuid,
            "email": u.email,
            "roles": [r.name for r in u.roles],
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "researcher_slug": u.researcher.slug if u.researcher else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
        
    return jsonify({
        "data": users_data,
        "meta": {
            "page": paginated.page,
            "page_size": paginated.per_page,
            "total_pages": paginated.pages,
            "total_records": paginated.total
        }
    })

@admin_api_bp.route('/backup', methods=['POST'])
@require_admin_api_key
def api_backup_database():
    db_path = os.path.join(current_app.instance_path, 'researchgraph.db')
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True, download_name='researchgraph_backup.db')
    return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Database file not found'}}), 404

@admin_api_bp.route('/restore', methods=['POST'])
@require_admin_api_key
def api_restore_database():
    if request.headers.get('X-Confirm-Restore') != 'true':
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Missing X-Confirm-Restore: true header. This operation is highly destructive.'}}), 400
        
    if 'db_file' not in request.files:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'No db_file provided'}}), 400
        
    file = request.files['db_file']
    if not file.filename.endswith('.db'):
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Invalid file format. Must be .db'}}), 400
        
    try:
        if not current_app.config.get('TESTING'):
            db.engine.dispose()
        db_path = os.path.join(current_app.instance_path, 'researchgraph.db')
        file.save(db_path)
        return jsonify({"meta": {"message": "Database restored successfully"}})
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
