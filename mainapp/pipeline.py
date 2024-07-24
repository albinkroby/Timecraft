# yourapp/pipeline.py
from social_core.exceptions import AuthForbidden


def set_user_role(backend, user, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        user_role = backend.strategy.session_get('user_role')
        if user_role and user:
            user.role = user_role
            user.save()

