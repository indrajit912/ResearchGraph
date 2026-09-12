import pytest
from app.models import Researcher, Collaboration, CollaborationStatus
from app.extensions import db
from sqlalchemy.exc import IntegrityError

def test_collaboration_undirected_constraint(app):
    with app.app_context():
        r1 = Researcher(first_name="Alice", last_name="A", display_name="Alice A", slug="alice-a")
        r2 = Researcher(first_name="Bob", last_name="B", display_name="Bob B", slug="bob-b")
        db.session.add(r1)
        db.session.add(r2)
        db.session.commit()
        
        # Must enforce A < B
        a_id = min(r1.uuid, r2.uuid)
        b_id = max(r1.uuid, r2.uuid)
        
        c = Collaboration(researcher_a_id=a_id, researcher_b_id=b_id, status=CollaborationStatus.ESTABLISHED)
        db.session.add(c)
        db.session.commit()
        
        # Test duplicate prevention
        c2 = Collaboration(researcher_a_id=a_id, researcher_b_id=b_id, status=CollaborationStatus.ONGOING)
        db.session.add(c2)
        with pytest.raises(IntegrityError):
            db.session.commit()
