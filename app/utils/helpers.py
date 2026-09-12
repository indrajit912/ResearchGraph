import re
from app.models import Researcher

def generate_slug(name):
    # Basic slugify
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    
    # Ensure uniqueness
    base_slug = slug
    counter = 1
    while Researcher.query.filter_by(slug=slug).first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug
