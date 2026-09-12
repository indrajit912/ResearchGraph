from datetime import datetime, timezone
import enum
from app.extensions import db

class ReportStatus(enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"

class CollaborationReport(db.Model):
    __tablename__ = 'collaboration_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    collaboration_id = db.Column(db.String(36), db.ForeignKey('collaborations.id', ondelete='CASCADE'), nullable=False, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ReportStatus), default=ReportStatus.OPEN, nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_message = db.Column(db.Text, nullable=True)
    
    # Relationships
    collaboration = db.relationship('Collaboration', backref=db.backref('reports', lazy='dynamic'))
    reported_by = db.relationship('User', foreign_keys=[reported_by_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])

class ResearcherCorrectionReport(db.Model):
    __tablename__ = 'researcher_correction_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    researcher_id = db.Column(db.String(36), db.ForeignKey('researchers.uuid', ondelete='CASCADE'), nullable=False, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ReportStatus), default=ReportStatus.OPEN, nullable=False, index=True)
    is_deletion_request = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_message = db.Column(db.Text, nullable=True)
    
    # Relationships
    researcher = db.relationship('Researcher', backref=db.backref('correction_reports', lazy='dynamic'))
    reported_by = db.relationship('User', foreign_keys=[reported_by_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])
