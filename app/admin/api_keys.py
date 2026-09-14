from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import APIKey
from . import admin_bp
from app.utils.decorators import requires_role
from datetime import datetime, timezone, timedelta

@admin_bp.route('/api-keys')
@login_required
@requires_role('SUPERADMIN')
def manage_api_keys():
    keys = APIKey.query.filter_by(user_id=current_user.id).order_by(APIKey.created_at.desc()).all()
    return render_template('admin/api_keys/index.html', keys=keys)

@admin_bp.route('/api-keys/generate', methods=['GET', 'POST'])
@login_required
@requires_role('SUPERADMIN')
def generate_api_key():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        expiration_days = request.form.get('expiration_days', type=int)
        
        raw_key, prefix, key_hash = APIKey.generate_key()
        
        expires_at = None
        if expiration_days and expiration_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiration_days)
            
        api_key = APIKey(
            user_id=current_user.id,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            expires_at=expires_at
        )
        db.session.add(api_key)
        db.session.commit()
        
        # We must show the raw key only once
        return render_template('admin/api_keys/show_key.html', raw_key=raw_key, api_key=api_key)
        
    return render_template('admin/api_keys/generate.html')

@admin_bp.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@login_required
@requires_role('SUPERADMIN')
def revoke_api_key(key_id):
    api_key = APIKey.query.get_or_404(key_id)
    if api_key.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for('admin.manage_api_keys'))
        
    api_key.is_revoked = True
    db.session.commit()
    flash(f"API Key '{api_key.name or api_key.prefix}' revoked successfully.", "success")
    return redirect(url_for('admin.manage_api_keys'))

@admin_bp.route('/api-docs')
@login_required
@requires_role('SUPERADMIN')
def api_docs():
    return render_template('admin/api_keys/docs.html')
