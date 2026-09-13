import uuid
from datetime import datetime, timezone
from app.extensions import db

def sha256_hash(raw_text:str):
    """Hash the given text using SHA-256 algorithm.

    Args:
        raw_text (str): The input text to be hashed.

    Returns:
        str: The hexadecimal representation of the hashed value.

    Example:
        >>> sha256_hash('my_secret_password')
        'e5e9fa1ba31ecd1ae84f75caaa474f3a663f05f4'
    """
    import hashlib
    hashed = hashlib.sha256(raw_text.encode()).hexdigest()
    return hashed


class Researcher(db.Model):
    __tablename__ = 'researchers'
    
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(255), nullable=False, index=True)
    
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    affiliation = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(255), nullable=True)
    
    # Location
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # Academic metadata
    research_interests = db.Column(db.Text, nullable=True)
    phd_institute = db.Column(db.String(255), nullable=True)
    phd_year = db.Column(db.Integer, nullable=True)
    
    # Identifiers / Links
    website = db.Column(db.String(255), nullable=True)
    orcid = db.Column(db.String(50), nullable=True)
    arxiv_id = db.Column(db.String(50), nullable=True)
    google_scholar_url = db.Column(db.String(255), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    emails = db.relationship('ResearcherEmail', backref='researcher', cascade='all, delete-orphan')
    

    def avatar(self, size=128):
        """
        Generate Gravatar URL for the user's avatar.

        Args:
            size (int): Size of the avatar image.

        Returns:
            str: URL of the user's Gravatar avatar.
        """
        email_to_hash = None
        for email_record in self.emails:
            if email_record.is_primary:
                email_to_hash = email_record.email
                break
        if not email_to_hash and self.emails:
            email_to_hash = self.emails[0].email
            
        if email_to_hash:
            email_hash = sha256_hash(email_to_hash.lower())
        else:
            email_hash = sha256_hash(self.uuid)
            
        return f"https://gravatar.com/avatar/{email_hash}?d=identicon&s={size}"

    def __repr__(self):

        return f"<Researcher {self.display_name}>"


class ResearcherEmail(db.Model):
    __tablename__ = 'researcher_emails'
    
    id = db.Column(db.Integer, primary_key=True)
    researcher_id = db.Column(db.String(36), db.ForeignKey('researchers.uuid', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_primary = db.Column(db.Boolean, default=False)
    

    def __repr__(self):
        return f"<ResearcherEmail {self.email}>"
