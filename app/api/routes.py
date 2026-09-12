from flask import jsonify, request
from app.models import Researcher, Collaboration
from . import api_bp

@api_bp.route('/network/<slug>')
def get_network(slug):
    depth = request.args.get('depth', 1, type=int)
    if depth < 1: depth = 1
    if depth > 3: depth = 3
        
    root_researcher = Researcher.query.filter_by(slug=slug).first_or_404()
    
    visited_nodes = {root_researcher.uuid: root_researcher}
    current_level = [root_researcher.uuid]
    
    # BFS up to depth
    for d in range(depth):
        next_level = []
        if not current_level:
            break
            
        collabs = Collaboration.query.filter(
            (Collaboration.researcher_a_id.in_(current_level)) | 
            (Collaboration.researcher_b_id.in_(current_level))
        ).all()
        
        for c in collabs:
            other_id = c.researcher_b_id if c.researcher_a_id in current_level else c.researcher_a_id
            if other_id not in visited_nodes:
                # In production, we'd batch fetch this, but this is fine for now
                other_researcher = Researcher.query.get(other_id)
                visited_nodes[other_id] = other_researcher
                next_level.append(other_id)
                
        current_level = next_level

    # Get ALL edges between visited nodes
    visited_ids = list(visited_nodes.keys())
    final_collabs = Collaboration.query.filter(
        Collaboration.researcher_a_id.in_(visited_ids),
        Collaboration.researcher_b_id.in_(visited_ids)
    ).all()
    
    nodes_data = []
    for r in visited_nodes.values():
        nodes_data.append({
            "id": r.uuid,
            "name": r.display_name,
            "affiliation": r.affiliation,
            "slug": r.slug,
            "is_root": r.uuid == root_researcher.uuid,
            "avatar": r.avatar(128)
        })
        
    links_data = []
    established_count = 0
    ongoing_count = 0
    
    for c in final_collabs:
        links_data.append({
            "source": c.researcher_a_id,
            "target": c.researcher_b_id,
            "status": c.status.name
        })
        if c.researcher_a_id == root_researcher.uuid or c.researcher_b_id == root_researcher.uuid:
            if c.status.name == 'ESTABLISHED':
                established_count += 1
            else:
                ongoing_count += 1
        
    return jsonify({
        "nodes": nodes_data,
        "links": links_data,
        "stats": {
            "total_collaborators": established_count + ongoing_count,
            "established": established_count,
            "ongoing": ongoing_count
        }
    })

@api_bp.route('/network/global')
def get_global_network():
    # Only active researchers
    all_researchers = Researcher.query.filter_by(is_active=True).all()
    researcher_dict = {r.uuid: r for r in all_researchers}
    active_ids = list(researcher_dict.keys())
    
    # Only edges between active researchers
    all_collabs = Collaboration.query.filter(
        Collaboration.researcher_a_id.in_(active_ids),
        Collaboration.researcher_b_id.in_(active_ids)
    ).all()
    
    nodes_data = []
    for r in all_researchers:
        nodes_data.append({
            "id": r.uuid,
            "name": r.display_name,
            "affiliation": r.affiliation,
            "slug": r.slug,
            "is_root": False,
            "avatar": r.avatar(128)
        })
        
    links_data = []
    established_count = 0
    ongoing_count = 0
    
    for c in all_collabs:
        links_data.append({
            "source": c.researcher_a_id,
            "target": c.researcher_b_id,
            "status": c.status.name
        })
        if c.status.name == 'ESTABLISHED':
            established_count += 1
        else:
            ongoing_count += 1
            
    return jsonify({
        "nodes": nodes_data,
        "links": links_data,
        "stats": {
            "total_researchers": len(all_researchers),
            "total_collaborations": len(all_collabs),
            "established": established_count,
            "ongoing": ongoing_count
        }
    })
