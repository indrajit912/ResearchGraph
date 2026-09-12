import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import CheckConstraint, UniqueConstraint
from app.extensions import db

class CollaborationStatus(enum.Enum):
    ESTABLISHED = "ESTABLISHED"
    ONGOING = "ONGOING"

class Collaboration(db.Model):
    __tablename__ = 'collaborations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    researcher_a_id = db.Column(db.String(36), db.ForeignKey('researchers.uuid', ondelete='CASCADE'), nullable=False, index=True)
    researcher_b_id = db.Column(db.String(36), db.ForeignKey('researchers.uuid', ondelete='CASCADE'), nullable=False, index=True)
    
    status = db.Column(db.Enum(CollaborationStatus), default=CollaborationStatus.ESTABLISHED, nullable=False)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Ensure undirected graph edge uniqueness: a < b
        CheckConstraint('researcher_a_id < researcher_b_id', name='check_undirected_edge'),
        # Prevent A-B from being added twice
        UniqueConstraint('researcher_a_id', 'researcher_b_id', name='uq_collaboration_edge'),
    )

    # Relationships
    researcher_a = db.relationship('Researcher', foreign_keys=[researcher_a_id], backref=db.backref('collaborations_as_a', lazy='dynamic'))
    researcher_b = db.relationship('Researcher', foreign_keys=[researcher_b_id], backref=db.backref('collaborations_as_b', lazy='dynamic'))
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    def __repr__(self):
        return f"<Collaboration {self.researcher_a_id} - {self.researcher_b_id}>"
