import secrets
import logging
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import CayuOAuthProfile, OAuthState, PendingAuthToken, TOKEN_EXPIRY

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_auth_token(user, poll_id):
    """Generate token and store on the PendingAuthToken entry."""
    token = secrets.token_urlsafe(32)
    PendingAuthToken.objects.filter(poll_id=poll_id).update(token=token, user=user)
    PendingAuthToken.cleanup_expired()
    return token


@api_view(['GET'])
@permission_classes([AllowAny])
@transaction.atomic
def token_login(request):
    """Validate auth token and create session (atomic to prevent race conditions)."""
    token = request.GET.get('token')
    if not token:
        return Response({'error': 'Token required'}, status=400)

    pending = PendingAuthToken.objects.select_for_update().filter(
        token=token,
        created_at__gte=timezone.now() - TOKEN_EXPIRY
    ).first()

    if not pending or not pending.user:
        logger.warning("Invalid or expired auth token")
        return Response({'error': 'Invalid or expired token'}, status=400)

    user = pending.user
    pending.delete()
    login(request, user, backend='apps.accounts.backends.CayuOAuthBackend')
    logger.info(f"User {user.email} logged in via auth token")

    return redirect('/admin/')


def is_safe_redirect_url(url):
    """Validate redirect URL is safe (relative path only, no open redirect)."""
    if not url:
        return False
    parsed = urlparse(url)
    # Only allow relative URLs (no scheme or netloc) that start with /
    return not parsed.scheme and not parsed.netloc and url.startswith('/')


def get_oauth_redirect_uri(request):
    """Build OAuth redirect URI using APP_DOMAIN if available, otherwise use request."""
    if settings.APP_DOMAIN:
        return f"https://{settings.APP_DOMAIN}/accounts/cayu/callback/"
    return request.build_absolute_uri(reverse('cayu_callback'))


@api_view(['GET'])
@permission_classes([AllowAny])
def cayu_authorize(request):
    """
    Initiates OAuth flow by redirecting to Cayu's authorization endpoint.
    """
    # Generate state for CSRF protection and store in database
    state = secrets.token_urlsafe(32)
    next_url = request.GET.get('next', '/admin/')
    if not is_safe_redirect_url(next_url):
        next_url = '/admin/'
    is_popup = request.GET.get('popup') == '1'
    poll_id = request.GET.get('poll_id')

    if poll_id:
        PendingAuthToken.objects.create(poll_id=poll_id)
        PendingAuthToken.cleanup_expired()

    OAuthState.cleanup_expired()

    OAuthState.objects.create(
        state=state, next_url=next_url, is_popup=is_popup, poll_id=poll_id
    )

    params = {
        'response_type': 'code',
        'client_id': settings.CAYU_OAUTH_CLIENT_ID,
        'redirect_uri': get_oauth_redirect_uri(request),
        'scope': 'profile',
        'state': state,
    }

    authorize_url = f"{settings.CAYU_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    logger.info(f"Redirecting to Cayu OAuth: {settings.CAYU_OAUTH_AUTHORIZE_URL}")

    return HttpResponseRedirect(authorize_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def cayu_callback(request):
    """
    Handles OAuth callback from Cayu.
    Exchanges authorization code for access token and creates/updates user.
    """
    # Verify state for CSRF protection (look up in database)
    received_state = request.GET.get('state')
    if not received_state:
        logger.warning("OAuth callback missing state parameter")
        return Response({'error': 'Missing state parameter'}, status=400)

    oauth_state = OAuthState.objects.filter(state=received_state).first()

    if not oauth_state:
        logger.warning("OAuth state not found or invalid")
        return Response({'error': 'Invalid state parameter'}, status=400)

    next_url = oauth_state.next_url
    is_popup = oauth_state.is_popup
    poll_id = oauth_state.poll_id
    oauth_state.delete()  # Clean up after use
    code = request.GET.get('code')

    if not code:
        error = request.GET.get('error', 'Unknown error')
        logger.error(f"OAuth error: {error}")
        return Response({'error': f'OAuth failed: {error}'}, status=400)

    # Exchange authorization code for access token
    try:
        token_response = requests.post(
            settings.CAYU_OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': get_oauth_redirect_uri(request),
                'client_id': settings.CAYU_OAUTH_CLIENT_ID,
                'client_secret': settings.CAYU_OAUTH_CLIENT_SECRET,
            },
            timeout=30
        )
        token_response.raise_for_status()
        tokens = token_response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Token exchange failed: {e}")
        return Response({'error': 'Failed to exchange authorization code'}, status=500)

    # Fetch user info from Cayu
    try:
        userinfo_response = requests.get(
            settings.CAYU_OAUTH_USERINFO_URL,
            headers={'Authorization': f"Bearer {tokens['access_token']}"},
            timeout=30
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Userinfo fetch failed: {e}")
        return Response({'error': 'Failed to fetch user info'}, status=500)

    # Create or update Django user
    user = create_or_update_user(userinfo)

    # If popup mode, store token in DB for polling and close window
    # Skip login() here — the popup session is discarded when the window closes.
    # The parent window will use the token to create its own session via token_login().
    if is_popup and poll_id:
        # Set session cookie in popup (first-party context) so the iframe can use it.
        # Without this, browsers block the cookie when set from the iframe (third-party context).
        login(request, user, backend='apps.accounts.backends.CayuOAuthBackend')
        generate_auth_token(user, poll_id)
        logger.info(f"Stored auth token for poll_id: {poll_id}")

        return HttpResponse('''
            <!DOCTYPE html>
            <html>
            <head><title>Login Complete</title></head>
            <body>
                <p>Login successful! This window will close automatically.</p>
                <script>window.close();</script>
            </body>
            </html>
        ''', content_type='text/html')

    login(request, user, backend='apps.accounts.backends.CayuOAuthBackend')
    logger.info(f"User {user.email} logged in via Cayu OAuth")

    return redirect(next_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def poll_token(request):
    """Poll for auth token after popup OAuth completes."""
    poll_id = request.GET.get('poll_id')
    if not poll_id:
        return Response({'status': 'error', 'message': 'poll_id required'}, status=400)

    pending = PendingAuthToken.objects.filter(
        poll_id=poll_id,
        created_at__gte=timezone.now() - TOKEN_EXPIRY
    ).first()

    if not pending:
        return Response({'status': 'pending'})

    if not pending.token:
        return Response({'status': 'pending'})

    token = pending.token
    logger.info(f"Delivered auth token for poll_id: {poll_id}")
    return Response({'status': 'ready', 'token': token})


def create_or_update_user(userinfo):
    """
    Creates or updates a Django user based on Cayu userinfo.
    Sets permissions based on organization role.
    """
    cayu_user_id = userinfo['sub']
    email = userinfo['email']

    # Try to find existing user by Cayu profile
    try:
        profile = CayuOAuthProfile.objects.select_related('user').get(cayu_user_id=cayu_user_id)
        user = profile.user
        logger.info(f"Found existing user for Cayu ID {cayu_user_id}")
    except CayuOAuthProfile.DoesNotExist:
        # Always create a new user — never match by email to prevent account linking
        user = User.objects.create_user(
            username=f"cayu_{cayu_user_id}",
            email=email
        )
        logger.info(f"Created new user for Cayu ID {cayu_user_id}")

    # Determine permissions based on Cayu organization role
    # Only org admins get full Django admin access
    org_role = userinfo.get('cayu_organization_role', 'member')
    is_org_admin = org_role == 'admin'

    # Update user permissions — promote via OAuth, but never demote
    # (local permission grants in Django admin should be preserved)
    if is_org_admin:
        user.is_superuser = True
        user.is_staff = True
    user.first_name = userinfo.get('given_name', '')
    user.last_name = userinfo.get('family_name', '')
    user.save()

    # Update or create Cayu profile
    CayuOAuthProfile.objects.update_or_create(
        cayu_user_id=cayu_user_id,
        defaults={
            'user': user,
            'cayu_email': email,
            'cayu_organization_id': userinfo.get('cayu_organization_id'),
            'cayu_organization_role': org_role,
            'cayu_is_super_admin': userinfo.get('cayu_is_super_admin', False),
            'last_login_at': timezone.now(),
        }
    )

    return user
