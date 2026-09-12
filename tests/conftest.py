import pytest
from app import create_app
from app.extensions import db
from app.models import Role, User

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Seed Roles
        for r in ['USER', 'MODERATOR', 'ADMIN', 'SUPERADMIN']:
            db.session.add(Role(name=r))
        db.session.commit()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def init_database(app):
    # Setup some test data
    pass
