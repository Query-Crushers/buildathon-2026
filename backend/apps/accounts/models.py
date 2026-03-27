from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

TOKEN_EXPIRY = timedelta(seconds=120)
OAUTH_STATE_EXPIRY = timedelta(seconds=600)


class OAuthState(models.Model):
    """Temporary storage for OAuth state during authorization flow."""
    state = models.CharField(max_length=64, unique=True, db_index=True)
    next_url = models.CharField(max_length=500, default='/admin/')
    is_popup = models.BooleanField(default=False)
    poll_id = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'oauth_states'

    @classmethod
    def cleanup_expired(cls):
        cls.objects.filter(created_at__lt=timezone.now() - OAUTH_STATE_EXPIRY).delete()


class PendingAuthToken(models.Model):
    """
    Handles the full popup OAuth token lifecycle:
    1. Created with poll_id when OAuth starts (token/user empty)
    2. Updated with token + user when OAuth completes
    3. Polled by parent window via poll_id
    4. Consumed by token_login via token to create session
    """
    poll_id = models.CharField(max_length=64, unique=True, db_index=True)
    token = models.CharField(max_length=64, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pending_auth_tokens'

    @classmethod
    def cleanup_expired(cls):
        cls.objects.filter(created_at__lt=timezone.now() - TOKEN_EXPIRY).delete()


class CayuOAuthProfile(models.Model):
    """
    Stores OAuth profile data from Cayu platform.
    Links a Django user to their Cayu account for "Login with Cayu".
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cayu_profile'
    )
    cayu_user_id = models.CharField(max_length=50, unique=True)
    cayu_email = models.EmailField()
    cayu_organization_id = models.CharField(max_length=50, null=True, blank=True)
    cayu_organization_role = models.CharField(max_length=50, null=True, blank=True)
    cayu_is_super_admin = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cayu_oauth_profiles'
        verbose_name = 'Cayu OAuth Profile'
        verbose_name_plural = 'Cayu OAuth Profiles'

    def __str__(self):
        return f"{self.user.email} (Cayu: {self.cayu_email})"
