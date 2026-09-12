from functools import wraps
from flask import abort
from flask_login import current_user

def requires_role(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.has_role('SUPERADMIN'):
                return f(*args, **kwargs)
            if not any(current_user.has_role(role) for role in role_names):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
