from django.contrib.auth import get_user_model


class CayuOAuthBackend:
    """
    Custom authentication backend for Cayu OAuth.
    Used to authenticate users via "Login with Cayu".
    """

    def authenticate(self, request, **kwargs):
        # Authentication is handled in the OAuth callback view
        # This backend is used for session management via login()
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
