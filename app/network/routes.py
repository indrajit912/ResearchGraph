from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Researcher, Collaboration, CollaborationStatus, CollaborationReport, ResearcherCorrectionReport, AuditLog
from app.services.email_service import EmailService
from . import network_bp
from .forms import AddCollaborationForm, ReportCollaborationForm, ReportResearcherForm

@network_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.researcher_id:
        return redirect(url_for('main.welcome'))
        
    me = current_user.researcher
    # Get all collaborations where I am either A or B
    collabs_as_a = Collaboration.query.filter_by(researcher_a_id=me.uuid).all()
    collabs_as_b = Collaboration.query.filter_by(researcher_b_id=me.uuid).all()
    
    collaborations = collabs_as_a + collabs_as_b
    
    return render_template('network/dashboard.html', researcher=me, collaborations=collaborations)

@network_bp.route('/add-edge', methods=['POST'])
@login_required
def add_edge():
    if not current_user.researcher_id:
        flash('You must claim a profile before adding collaborations.', 'warning')
        return redirect(url_for('main.index'))
        
    form = AddCollaborationForm()
    if form.validate_on_submit():
        target_uuid = form.target_researcher_uuid.data
        status_enum = CollaborationStatus[form.status.data]
        
        my_uuid = current_user.researcher_id
        
        if my_uuid == target_uuid:
            flash("You cannot collaborate with yourself.", "danger")
            return redirect(url_for('network.dashboard'))
            
        # Enforce undirected edge constraint A < B
        researcher_a_id = min(my_uuid, target_uuid)
        researcher_b_id = max(my_uuid, target_uuid)
        
        # Check if exists
        existing = Collaboration.query.filter_by(researcher_a_id=researcher_a_id, researcher_b_id=researcher_b_id).first()
        if existing:
            flash("This collaboration already exists in the global graph.", "info")
            return redirect(url_for('network.dashboard'))
            
        collab = Collaboration(
            researcher_a_id=researcher_a_id,
            researcher_b_id=researcher_b_id,
            status=status_enum,
            created_by_id=current_user.id
        )
        
        # Audit Log
        audit = AuditLog(
            user_id=current_user.id,
            action="CREATE_COLLABORATION",
            object_type="Collaboration",
            object_id="NEW", # will update after flush if needed, but uuid is auto-generated
            new_value=f"{researcher_a_id} <-> {researcher_b_id} ({status_enum.name})"
        )
        
        try:
            db.session.add(collab)
            db.session.add(audit)
            db.session.commit()
            
            # update audit object_id
            audit.object_id = collab.id
            db.session.commit()
            
            flash("Collaboration added successfully to the global graph!", "success")
        except IntegrityError:
            db.session.rollback()
            flash("A database error occurred (possible duplicate).", "danger")
            
    return redirect(url_for('network.dashboard'))

@network_bp.route('/report-collaboration', methods=['POST'])
@login_required
def report_collaboration():
    form = ReportCollaborationForm()
    if form.validate_on_submit():
        report = CollaborationReport(
            collaboration_id=form.collaboration_id.data,
            reported_by_id=current_user.id,
            message=form.message.data
        )
        db.session.add(report)
        db.session.commit()
        # TODO: Send email notification to ADMINs via EmailService
        flash("Report submitted successfully. Moderators will review it.", "success")
    return redirect(url_for('network.dashboard'))

@network_bp.route('/report-researcher', methods=['POST'])
@login_required
def report_researcher():
    form = ReportResearcherForm()
    if form.validate_on_submit():
        report = ResearcherCorrectionReport(
            researcher_id=form.researcher_uuid.data,
            reported_by_id=current_user.id,
            message=form.message.data
        )
        db.session.add(report)
        db.session.commit()
        # TODO: Send email notification to ADMINs via EmailService
        flash("Correction request submitted successfully.", "success")
    return redirect(url_for('main.index'))

@network_bp.route('/remove-edge/<string:collab_id>', methods=['POST'])
@login_required
def remove_edge(collab_id):
    if not current_user.researcher_id:
        return redirect(url_for('main.index'))
    
    collab = Collaboration.query.get_or_404(collab_id)
    # Check if the user is part of the collaboration
    if collab.researcher_a_id != current_user.researcher_id and collab.researcher_b_id != current_user.researcher_id:
        flash("You can only remove collaborations you are directly a part of.", "danger")
        return redirect(url_for('network.dashboard'))
        
    audit = AuditLog(
        user_id=current_user.id,
        action="DELETE_COLLABORATION",
        object_type="Collaboration",
        object_id=str(collab.id),
        old_value=f"{collab.researcher_a_id} <-> {collab.researcher_b_id} ({collab.status.name})"
    )
    
    # Delete associated reports manually to avoid SQLAlchemy setting them to NULL
    collab.reports.delete(synchronize_session=False)
    
    db.session.delete(collab)
    db.session.add(audit)
    db.session.commit()
    flash("Collaboration successfully removed from the global graph.", "success")
    return redirect(url_for('network.dashboard'))

from app.network.forms import EditMyProfileForm

@network_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_my_profile():
    if not current_user.researcher_id:
        flash("You must claim a profile before editing it.", "warning")
        return redirect(url_for('main.index'))
        
    researcher = Researcher.query.get_or_404(current_user.researcher_id)
    form = EditMyProfileForm(obj=researcher)
    
    if form.validate_on_submit():
        form.populate_obj(researcher)
        if researcher.website and not researcher.website.startswith('http'):
            researcher.website = 'https://' + researcher.website
        if researcher.google_scholar_url and not researcher.google_scholar_url.startswith('http'):
            researcher.google_scholar_url = 'https://' + researcher.google_scholar_url
        db.session.commit()
        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for('main.view_profile', slug=researcher.slug))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", "danger")
        
    return render_template('network/edit_profile.html', form=form, researcher=researcher)

@network_bp.route('/edit-edge-status/<string:collab_id>', methods=['POST'])
@login_required
def edit_edge_status(collab_id):
    if not current_user.researcher_id:
        return redirect(url_for('main.index'))
    
    collab = Collaboration.query.get_or_404(collab_id)
    
    # Verify the user is part of this collaboration
    if collab.researcher_a_id != current_user.researcher_id and collab.researcher_b_id != current_user.researcher_id:
        flash("You are not authorized to edit this collaboration.", "danger")
        return redirect(url_for('network.dashboard'))
        
    new_status = request.form.get('status')
    if new_status in ['ESTABLISHED', 'ONGOING']:
        old_status_name = collab.status.name
        collab.status = CollaborationStatus[new_status]
        collab.updated_by_id = current_user.id
        
        audit = AuditLog(
            user_id=current_user.id,
            action="UPDATE_COLLABORATION_STATUS",
            object_type="collaboration",
            object_id=collab.id,
            old_value=old_status_name,
            new_value=new_status
        )
        db.session.add(audit)
        db.session.commit()
        flash("Collaboration status updated successfully.", "success")
    else:
        flash("Invalid status value.", "danger")
        
    return redirect(url_for('network.dashboard'))
