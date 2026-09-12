from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User, Researcher
from app.services.email_service import EmailService
from . import auth_bp
from .forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('auth.register'))
            
        new_user = User(email=form.email.data.lower())
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        
        EmailService.send_verification_email(new_user.email)
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('network.dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    email = EmailService.verify_token(token, salt='email-verify-salt')
    if not email:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.register'))
        
    if user.is_verified:
        flash('Account already verified. Please login.', 'info')
    else:
        user.is_verified = True
        db.session.commit()
        flash('Your account has been verified! You can now log in.', 'success')
        
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            EmailService.send_password_reset_email(user.email)
        # Always display this to prevent email enumeration
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_request.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    email = EmailService.verify_token(token, salt='password-reset-salt')
    if not email:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('auth.reset_password_request'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('main.index'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/claim-researcher/<uuid>', methods=['POST'])
@login_required
def claim_researcher(uuid):
    if current_user.researcher_id:
        flash('You are already associated with a researcher profile.', 'warning')
        return redirect(url_for('main.index'))
        
    researcher = Researcher.query.get_or_404(uuid)
    if not researcher.emails:
        flash("This profile doesn't have an email address on record. Please suggest a correction to add your email first.", "danger")
        return redirect(request.referrer or url_for('main.search'))
        
    for email_record in researcher.emails:
        EmailService.send_claim_profile_email(email_record.email, researcher.uuid, current_user.id)
        
    flash(f"Verification sent! Please check the email(s) associated with {researcher.display_name}'s profile to confirm.", "info")
    return redirect(url_for('main.index'))

@auth_bp.route('/verify-claim/<token>')
@login_required
def verify_claim(token):
    if current_user.researcher_id:
        flash('You are already associated with a profile.', 'warning')
        return redirect(url_for('main.index'))
        
    data = EmailService.verify_token(token, salt='claim-salt')
    if not data or data.get('u_id') != current_user.id:
        flash("Invalid or expired claim token, or you are logged into the wrong account.", "danger")
        return redirect(url_for('main.index'))
        
    researcher = Researcher.query.get_or_404(data['r_uuid'])
    current_user.researcher_id = researcher.uuid
    db.session.commit()
    flash(f"Successfully claimed profile: {researcher.display_name}. Welcome to your network dashboard!", "success")
    return redirect(url_for('network.dashboard'))
