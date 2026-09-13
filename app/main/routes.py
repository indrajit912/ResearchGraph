from flask import render_template, request, flash, redirect, url_for
from . import main_bp
from .forms import SearchForm
from app.models import Researcher, ResearcherEmail

from flask_login import current_user

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('network.dashboard') if current_user.researcher_id else url_for('main.welcome'))
    form = SearchForm()
    return render_template('index.html', form=form)

@main_bp.route('/search')
def search():
    form = SearchForm()
    q = request.args.get('q', '').strip()
    results = []
    if q:
        # Search by display name
        name_results = Researcher.query.filter(Researcher.display_name.ilike(f'%{q}%')).all()
        # Search by email
        email_results = [email.researcher for email in ResearcherEmail.query.filter(ResearcherEmail.email.ilike(f'%{q}%')).all()]
        
        # Combine and deduplicate
        results_set = set(name_results + email_results)
        results = list(results_set)
        
    return render_template('search_results.html', form=form, q=q, results=results)


@main_bp.route('/r/<slug>')
def public_network(slug):
    researcher = Researcher.query.filter_by(slug=slug).first_or_404()
    return render_template('public_network.html', researcher=researcher)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/profile/<slug>')
def view_profile(slug):
    researcher = Researcher.query.filter_by(slug=slug).first_or_404()
    return render_template('profile.html', researcher=researcher)

@main_bp.route('/team')
def team():
    from app.models import Role
    superadmin_role = Role.query.filter_by(name='SUPERADMIN').first()
    admin_role = Role.query.filter_by(name='ADMIN').first()
    moderator_role = Role.query.filter_by(name='MODERATOR').first()
    
    superadmins = superadmin_role.users if superadmin_role else []
    admins = admin_role.users if admin_role else []
    moderators = moderator_role.users if moderator_role else []
    
    return render_template('team.html', 
                           superadmins=superadmins, 
                           admins=admins, 
                           moderators=moderators)

@main_bp.route('/global-network')
def global_network():
    return render_template('global_network.html')

@main_bp.route('/welcome')
def welcome():
    form = SearchForm()
    return render_template('welcome.html', form=form)
