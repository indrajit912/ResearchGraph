from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, login_manager
import os

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure instance folder exists for SQLite local dev
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    from app.extensions import db, migrate, login_manager, csrf
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # login_manager.login_view = 'auth.login'
    
    # Register models so Alembic can detect them
    from app import models

    # Register blueprints
    from app.main import main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    from app.network import network_bp
    app.register_blueprint(network_bp)
    
    from app.api import api_bp
    app.register_blueprint(api_bp)

    # Setup login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))
        
    @app.cli.command("create-superadmin")
    def create_superadmin():
        """Creates the initial superadmin and required roles."""
        from app.models import Role, User
        import click
        
        # Create standard roles
        for role_name in ['USER', 'MODERATOR', 'ADMIN', 'SUPERADMIN']:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name))
        db.session.commit()
        
        email = click.prompt("Superadmin Email", default="indrajitghosh912@gmail.com")
        password = click.prompt("Superadmin Password", hide_input=True, confirmation_prompt=True)
        
        user = User.query.filter_by(email=email).first()
        if user:
            click.echo(f"User {email} already exists. Granting SUPERADMIN role...")
        else:
            user = User(email=email, is_verified=True, is_active=True)
            user.set_password(password)
            db.session.add(user)
            
        superadmin_role = Role.query.filter_by(name='SUPERADMIN').first()
        if superadmin_role not in user.roles:
            user.roles.append(superadmin_role)
            
        db.session.commit()
        click.echo("Superadmin successfully created/updated!")


    # Error Handlers
    from flask import render_template
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    return app
