from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Researcher, ResearcherEmail, User
from app.utils.decorators import requires_role
from app.utils.helpers import generate_slug
from . import admin_bp
from .forms import ResearcherForm, ResearcherEmailForm

@admin_bp.context_processor
def inject_moderation_count():
    from flask_login import current_user
    if current_user.is_authenticated and any(current_user.has_role(r) for r in ['ADMIN', 'MODERATOR', 'SUPERADMIN']):
        from app.models import CollaborationReport, ResearcherCorrectionReport, ReportStatus
        c_count = CollaborationReport.query.filter_by(status=ReportStatus.OPEN).count()
        if current_user.has_role('ADMIN') or current_user.has_role('SUPERADMIN'):
            r_count = ResearcherCorrectionReport.query.filter_by(status=ReportStatus.OPEN).count()
        else:
            r_count = 0
        return {'open_reports_count': c_count + r_count}
    return {'open_reports_count': 0}


@admin_bp.route('/')
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/researchers')
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def list_researchers():
    q = request.args.get('q', '')
    if q:
        from app.models import ResearcherEmail
        name_results = Researcher.query.filter(Researcher.display_name.ilike(f'%{q}%')).all()
        email_results = [email.researcher for email in ResearcherEmail.query.filter(ResearcherEmail.email.ilike(f'%{q}%')).all()]
        researchers = list(set(name_results + email_results))
    else:
        researchers = Researcher.query.limit(50).all()
    return render_template('admin/researchers/list.html', researchers=researchers, q=q)

@admin_bp.route('/researchers/create', methods=['GET', 'POST'])
@login_required
@requires_role('MODERATOR', 'SUPERADMIN')
def create_researcher():
    form = ResearcherForm()
    if form.validate_on_submit():
        display_name = f"{form.first_name.data} {form.last_name.data}"
        if form.middle_name.data:
            display_name = f"{form.first_name.data} {form.middle_name.data} {form.last_name.data}"
            
        slug = generate_slug(display_name)
        
        researcher = Researcher(
            first_name=form.first_name.data,
            middle_name=form.middle_name.data,
            last_name=form.last_name.data,
            display_name=display_name,
            slug=slug,
            affiliation=form.affiliation.data,
            department=form.department.data,
            address=form.address.data,
            city=form.city.data,
            state=form.state.data,
            country=form.country.data,
            phd_institute=form.phd_institute.data,
            phd_year=form.phd_year.data,
            website=form.website.data,
            orcid=form.orcid.data,
            arxiv_id=form.arxiv_id.data,
            google_scholar_url=form.google_scholar_url.data,
            mathscinet_id=form.mathscinet_id.data,
            math_genealogy_url=form.math_genealogy_url.data,
            is_active=form.is_active.data
        )
        db.session.add(researcher)
        db.session.flush()
        
        from app.models import ResearcherEmail
        email_list = []
        if form.emails.data:
            email_list = [e.strip().lower() for e in form.emails.data.split(',') if e.strip()]
            
            # Check for existing emails
            for email_addr in email_list:
                existing = ResearcherEmail.query.filter_by(email=email_addr).first()
                if existing:
                    db.session.rollback()
                    flash(f'Error: The email {email_addr} is already associated with researcher "{existing.researcher.display_name}".', 'danger')
                    return render_template('admin/researchers/create.html', form=form)
        
        db.session.add(researcher)
        db.session.flush()
        
        for idx, email_addr in enumerate(email_list):
            email_record = ResearcherEmail(
                researcher_id=researcher.uuid,
                email=email_addr,
                is_primary=(idx == 0)
            )
            db.session.add(email_record)
                
        db.session.commit()
        flash('Researcher created successfully.', 'success')
        return redirect(url_for('admin.view_researcher', uuid=researcher.uuid))
        
    return render_template('admin/researchers/create.html', form=form)

@admin_bp.route('/researchers/<uuid>')
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def view_researcher(uuid):
    researcher = Researcher.query.get_or_404(uuid)
    form = ResearcherForm(obj=researcher)
    form.emails.data = ", ".join([e.email for e in researcher.emails])
    email_form = ResearcherEmailForm()
    return render_template('admin/researchers/view.html', researcher=researcher, form=form, email_form=email_form)

@admin_bp.route('/researchers/<uuid>/edit', methods=['GET', 'POST'])
@login_required
@requires_role('MODERATOR', 'SUPERADMIN')
def edit_researcher(uuid):
    researcher = Researcher.query.get_or_404(uuid)
    form = ResearcherForm(obj=researcher)
    
    if request.method == 'GET':
        form.emails.data = ", ".join([e.email for e in researcher.emails])
        
    if form.validate_on_submit():
        # Prevent WTForms from trying to populate the emails relationship as a string
        emails_field = form._fields.pop('emails', None)
        form.populate_obj(researcher)
        if emails_field:
            form._fields['emails'] = emails_field
        display_name = f"{researcher.first_name} {researcher.last_name}"
        if researcher.middle_name:
            display_name = f"{researcher.first_name} {researcher.middle_name} {researcher.last_name}"
        researcher.display_name = display_name
        
        # Handle emails
        from app.models import ResearcherEmail
        email_list = []
        if form.emails.data:
            email_list = [e.strip().lower() for e in form.emails.data.split(',') if e.strip()]
            
        # Check for existing emails belonging to OTHER researchers
        for email_addr in email_list:
            existing = ResearcherEmail.query.filter_by(email=email_addr).first()
            if existing and existing.researcher_id != researcher.uuid:
                db.session.rollback()
                flash(f'Error: The email {email_addr} is already associated with another researcher "{existing.researcher.display_name}".', 'danger')
                return render_template('admin/researchers/edit.html', form=form, researcher=researcher)
                
        # Sync emails
        current_emails = ResearcherEmail.query.filter_by(researcher_id=researcher.uuid).all()
        current_email_dict = {e.email: e for e in current_emails}
        
        # Remove emails not in the new list
        for email_addr, e_record in current_email_dict.items():
            if email_addr not in email_list:
                db.session.delete(e_record)
                
        # Update or add emails
        for idx, email_addr in enumerate(email_list):
            is_primary = (idx == 0)
            if email_addr in current_email_dict:
                current_email_dict[email_addr].is_primary = is_primary
            else:
                email_record = ResearcherEmail(
                    researcher_id=researcher.uuid,
                    email=email_addr,
                    is_primary=is_primary
                )
                db.session.add(email_record)
                    
        db.session.commit()
        flash('Researcher updated successfully.', 'success')
        return redirect(url_for('admin.view_researcher', uuid=researcher.uuid))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", "danger")
        
    return render_template('admin/researchers/edit.html', form=form, researcher=researcher)

@admin_bp.route('/researchers/<uuid>/emails', methods=['POST'])
@login_required
@requires_role('MODERATOR', 'SUPERADMIN')
def add_email(uuid):
    researcher = Researcher.query.get_or_404(uuid)
    form = ResearcherEmailForm()
    if form.validate_on_submit():
        existing = ResearcherEmail.query.filter_by(email=form.email.data.lower()).first()
        if existing:
            flash(f"Email {form.email.data} is already associated with a researcher.", "danger")
        else:
            email_record = ResearcherEmail(
                researcher_id=researcher.uuid,
                email=form.email.data.lower(),
                is_primary=form.is_primary.data
            )
            db.session.add(email_record)
            db.session.commit()
            flash('Email added successfully.', 'success')
            
    return redirect(url_for('admin.view_researcher', uuid=uuid))

from app.models import Role, AuditLog, ReportStatus, CollaborationReport, ResearcherCorrectionReport, Collaboration

@admin_bp.route('/users')
@login_required
@requires_role('ADMIN', 'SUPERADMIN')
def list_users():
    users = User.query.all()
    return render_template('admin/users/list.html', users=users)

@admin_bp.route('/users/<uuid>/roles', methods=['GET', 'POST'])
@login_required
@requires_role('ADMIN', 'SUPERADMIN')
def manage_roles(uuid):
    from flask import abort
    target_user = User.query.filter_by(uuid=uuid).first_or_404()
    
    # Evaluate Actor Roles (highest)
    actor_is_superadmin = current_user.has_role('SUPERADMIN')
    actor_is_admin = current_user.has_role('ADMIN') and not actor_is_superadmin
    
    # Evaluate Target Roles (highest)
    target_is_superadmin = target_user.has_role('SUPERADMIN')
    target_is_admin = target_user.has_role('ADMIN') and not target_is_superadmin
    target_is_moderator = target_user.has_role('MODERATOR') and not (target_is_admin or target_is_superadmin)
    target_is_user = not (target_is_superadmin or target_is_admin or target_is_moderator)
    
    # 1. Block Admin Self-Modification
    if actor_is_admin and target_user.id == current_user.id:
        abort(403)
        
    # 2. Block Admin from modifying equals or superiors
    if actor_is_admin and (target_is_admin or target_is_superadmin):
        abort(403)
        
    all_roles = Role.query.filter(Role.name != 'USER').all()
    allowed_roles_for_ui = []
    
    if actor_is_superadmin:
        allowed_roles_for_ui = [r for r in all_roles]
    elif actor_is_admin:
        if target_is_user:
            allowed_roles_for_ui = [r for r in all_roles if r.name == 'MODERATOR']
        elif target_is_moderator:
            allowed_roles_for_ui = [r for r in all_roles if r.name == 'ADMIN']
            
    if request.method == 'POST':
        selected_roles = request.form.getlist('roles')
        
        if actor_is_admin:
            if 'SUPERADMIN' in selected_roles or 'USER' in selected_roles:
                abort(403)
            # Admin can only transition User->Moderator or Moderator->Admin
            if target_is_user and set(selected_roles) != {'MODERATOR'}:
                abort(403)
            elif target_is_moderator and set(selected_roles) != {'ADMIN'}:
                abort(403)
            elif not target_is_user and not target_is_moderator:
                abort(403)
                
        target_user.roles = []
        for role_name in selected_roles:
            r = Role.query.filter_by(name=role_name).first()
            if r:
                target_user.roles.append(r)
                
        db.session.commit()
        flash("Roles updated successfully.", "success")
        return redirect(url_for('admin.list_users'))
        
    return render_template('admin/users/roles.html', target_user=target_user, allowed_roles=allowed_roles_for_ui)

@admin_bp.route('/moderation')
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def moderation_dashboard():
    # Fetch open reports
    collab_reports = CollaborationReport.query.filter_by(status=ReportStatus.OPEN).all()
    
    if current_user.has_role('ADMIN') or current_user.has_role('SUPERADMIN'):
        researcher_reports = ResearcherCorrectionReport.query.filter_by(status=ReportStatus.OPEN).all()
    else:
        # Moderators don't handle Vertex Reports at all anymore
        researcher_reports = []
        
    return render_template('admin/moderation/dashboard.html', collab_reports=collab_reports, researcher_reports=researcher_reports)

@admin_bp.route('/moderation/collab/<int:report_id>/resolve', methods=['POST'])
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def resolve_collab_report(report_id):
    report = CollaborationReport.query.get_or_404(report_id)
    action = request.form.get('action') # RESOLVED or REJECTED
    message = request.form.get('resolution_message')
    
    if action in [ReportStatus.RESOLVED.name, ReportStatus.REJECTED.name]:
        report.status = ReportStatus[action]
        report.resolution_message = message
        report.resolved_by_id = current_user.id
        from datetime import datetime, timezone
        report.resolved_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"Report marked as {action}.", "success")
        
    return redirect(url_for('admin.moderation_dashboard'))

@admin_bp.route('/audit')
@login_required
@requires_role('ADMIN', 'SUPERADMIN')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit/list.html', logs=logs)

@admin_bp.route('/researchers/<uuid>/delete', methods=['POST'])
@login_required
@requires_role('ADMIN', 'SUPERADMIN')
def delete_researcher(uuid):
    researcher = Researcher.query.get_or_404(uuid)
    display_name = researcher.display_name
    
    # We must manually delete reports to prevent IntegrityError
    collabs = Collaboration.query.filter(
        (Collaboration.researcher_a_id == uuid) | (Collaboration.researcher_b_id == uuid)
    ).all()
    collab_ids = [c.id for c in collabs]
    if collab_ids:
        CollaborationReport.query.filter(CollaborationReport.collaboration_id.in_(collab_ids)).delete(synchronize_session=False)
        Collaboration.query.filter(Collaboration.id.in_(collab_ids)).delete(synchronize_session=False)
    
    ResearcherCorrectionReport.query.filter_by(researcher_id=uuid).delete(synchronize_session=False)
    
    db.session.delete(researcher)
    db.session.commit()
    flash(f'Vertex {display_name} deleted successfully.', 'success')
    return redirect(url_for('admin.list_researchers'))

@admin_bp.route('/researchers/<uuid>/request-delete', methods=['POST'])
@login_required
@requires_role('MODERATOR')
def request_delete_researcher(uuid):
    researcher = Researcher.query.get_or_404(uuid)
    
    existing = ResearcherCorrectionReport.query.filter_by(
        researcher_id=uuid, 
        is_deletion_request=True, 
        status=ReportStatus.OPEN
    ).first()
    
    if existing:
        flash('A deletion request is already pending for this vertex.', 'warning')
    else:
        report = ResearcherCorrectionReport(
            researcher_id=uuid,
            reported_by_id=current_user.id,
            message="Moderator requested deletion of this vertex.",
            is_deletion_request=True
        )
        db.session.add(report)
        db.session.commit()
        flash('Deletion request raised successfully. An admin will review it.', 'info')
        
    return redirect(url_for('admin.view_researcher', uuid=uuid))

@admin_bp.route('/moderation/researcher/<int:report_id>/resolve', methods=['POST'])
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def resolve_researcher_report(report_id):
    report = ResearcherCorrectionReport.query.get_or_404(report_id)
    action = request.form.get('action')
    message = request.form.get('resolution_message', '')
    
    if action == 'APPROVE_DELETION' and (current_user.has_role('ADMIN') or current_user.has_role('SUPERADMIN')):
        researcher = report.researcher
        if researcher:
            display_name = researcher.display_name
            collabs = Collaboration.query.filter(
                (Collaboration.researcher_a_id == researcher.uuid) | (Collaboration.researcher_b_id == researcher.uuid)
            ).all()
            collab_ids = [c.id for c in collabs]
            if collab_ids:
                CollaborationReport.query.filter(CollaborationReport.collaboration_id.in_(collab_ids)).delete(synchronize_session=False)
                Collaboration.query.filter(Collaboration.id.in_(collab_ids)).delete(synchronize_session=False)
            
            ResearcherCorrectionReport.query.filter(
                ResearcherCorrectionReport.researcher_id == researcher.uuid,
                ResearcherCorrectionReport.id != report.id
            ).delete(synchronize_session=False)
            
            db.session.delete(researcher)
            report.status = ReportStatus.RESOLVED
            report.resolution_message = "Vertex deleted successfully."
            report.resolved_by_id = current_user.id
            from datetime import datetime, timezone
            report.resolved_at = datetime.now(timezone.utc)
            db.session.commit()
            flash(f"Vertex {display_name} deleted and request resolved.", "success")
        else:
            flash("Vertex already deleted.", "warning")
            report.status = ReportStatus.RESOLVED
            db.session.commit()
            
    elif action in [ReportStatus.RESOLVED.name, ReportStatus.REJECTED.name]:
        report.status = ReportStatus[action]
        report.resolution_message = message
        report.resolved_by_id = current_user.id
        from datetime import datetime, timezone
        report.resolved_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"Report marked as {action}.", "success")
        
    return redirect(url_for('admin.moderation_dashboard'))


from .forms import EdgeForm, SlugEdgeForm

@admin_bp.route('/edges/create', methods=['GET', 'POST'])
@login_required
@requires_role('ADMIN', 'MODERATOR', 'SUPERADMIN')
def create_edge():
    form = EdgeForm()
    slug_form = SlugEdgeForm()
    
    # Populate choices for standard form
    researchers = Researcher.query.filter_by(is_active=True).order_by(Researcher.display_name).all()
    choices = [(r.uuid, f"{r.display_name} ({r.affiliation or 'Independent'}) [Slug: {r.slug}]") for r in researchers]
    form.researcher_a.choices = choices
    form.researcher_b.choices = choices
    
    # Check which form was submitted based on the submit button name
    if 'submit' in request.form and form.validate_on_submit():
        uuid_a = form.researcher_a.data
        uuid_b = form.researcher_b.data
        status_data = form.status.data
        return process_edge_creation(uuid_a, uuid_b, status_data)
        
    if 'submit_slug' in request.form and slug_form.validate_on_submit():
        # Look up researchers by slug
        slug_a = slug_form.slug_a.data.strip()
        slug_b = slug_form.slug_b.data.strip()
        
        res_a = Researcher.query.filter_by(slug=slug_a).first()
        res_b = Researcher.query.filter_by(slug=slug_b).first()
        
        if not res_a:
            flash(f"Could not find vertex with slug: {slug_a}", "danger")
            return redirect(url_for('admin.create_edge'))
        if not res_b:
            flash(f"Could not find vertex with slug: {slug_b}", "danger")
            return redirect(url_for('admin.create_edge'))
            
        return process_edge_creation(res_a.uuid, res_b.uuid, slug_form.status_slug.data)
        
    return render_template('admin/edges/create.html', form=form, slug_form=slug_form)

def process_edge_creation(uuid_a, uuid_b, status):
    if uuid_a == uuid_b:
        flash("Cannot create an edge between a vertex and itself.", "danger")
        return redirect(url_for('admin.create_edge'))
        
    # Undirected graph logic
    r_a_id = min(uuid_a, uuid_b)
    r_b_id = max(uuid_a, uuid_b)
    
    existing = Collaboration.query.filter_by(researcher_a_id=r_a_id, researcher_b_id=r_b_id).first()
    if existing:
        flash("An edge already exists between these two vertices.", "warning")
        return redirect(url_for('admin.create_edge'))
        
    from app.models import CollaborationStatus
    collab = Collaboration(
        researcher_a_id=r_a_id,
        researcher_b_id=r_b_id,
        status=CollaborationStatus[status],
        created_by_id=current_user.id
    )
    db.session.add(collab)
    db.session.commit()
    flash("Edge successfully created!", "success")
    return redirect(url_for('admin.create_edge'))


import os
from flask import send_file, current_app
from werkzeug.utils import secure_filename

@admin_bp.route('/database/backup')
@login_required
@requires_role('SUPERADMIN')
def backup_database():
    db_path = os.path.join(current_app.instance_path, 'researchgraph.db')
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True, download_name='researchgraph_backup.db')
    else:
        flash("Database file not found.", "danger")
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/database/restore', methods=['POST'])
@login_required
@requires_role('SUPERADMIN')
def restore_database():
    if 'db_file' not in request.files:
        flash("No file provided.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    file = request.files['db_file']
    if file.filename == '':
        flash("No file selected.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    if not file.filename.endswith('.db'):
        flash("Invalid file format. Please upload a .db file.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    try:
        # Close all active DB connections before replacing
        db.engine.dispose()
        
        db_path = os.path.join(current_app.instance_path, 'researchgraph.db')
        file.save(db_path)
        flash("Database successfully restored from backup!", "success")
    except Exception as e:
        flash(f"Error restoring database: {str(e)}", "danger")
        
    return redirect(url_for('admin.dashboard'))
