import secrets
import string
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    name = db.Column(db.String(100), nullable=True)
    prefix = db.Column(db.String(8), nullable=False, index=True)
    key_hash = db.Column(db.String(255), nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    is_revoked = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('api_keys', cascade='all, delete-orphan', lazy='dynamic'))
    
    @staticmethod
    def generate_key():
        """Generates a secure API key and its components.
        Returns: (raw_key, prefix, key_hash)
        """
        # Format: rg_{8_char_prefix}_{32_char_secret}
        prefix = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        secret = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        raw_key = f"rg_{prefix}_{secret}"
        
        key_hash = generate_password_hash(raw_key)
        return raw_key, prefix, key_hash

    def check_key(self, raw_key):
        return check_password_hash(self.key_hash, raw_key)
        
    @property
    def is_valid(self):
        if self.is_revoked:
            return False
        if self.expires_at:
            expires_aware = self.expires_at.replace(tzinfo=timezone.utc) if self.expires_at.tzinfo is None else self.expires_at
            if datetime.now(timezone.utc) > expires_aware:
                return False
        return True
