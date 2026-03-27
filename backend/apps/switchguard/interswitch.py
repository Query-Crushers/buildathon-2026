"""
Interswitch API service — handles OAuth token caching, Transaction Search,
Global Search AML, and Place Lien calls.
"""
import base64
import logging
import time
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PASSPORT_TOKEN_URL = 'https://passport.k8.isw.la/passport/oauth/token'
TRANSACTION_SEARCH_URL = 'https://qa.interswitchng.com/collections/api/v1/gettransaction'
AML_GLOBAL_SEARCH_URL = 'https://qa.interswitchng.com/aml/api/v1/globalsearch'
PLACE_LIEN_URL = 'https://qa.interswitchng.com/collections/api/v1/lien'

_token_cache = {
    'access_token': None,
    'expires_at': 0,
}


def _get_auth_header():
    client_id = getattr(settings, 'INTERSWITCH_CLIENT_ID', '')
    secret_key = getattr(settings, 'INTERSWITCH_SECRET_KEY', '')
    credentials = f'{client_id}:{secret_key}'
    encoded = base64.b64encode(credentials.encode()).decode()
    return f'Basic {encoded}'


def get_access_token() -> str:
    """Return a cached access token or fetch a new one."""
    now = time.time()
    if _token_cache['access_token'] and _token_cache['expires_at'] > now + 60:
        return _token_cache['access_token']

    headers = {
        'Authorization': _get_auth_header(),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'client_credentials',
        'scope': 'profile',
    }
    try:
        resp = requests.post(PASSPORT_TOKEN_URL, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        _token_cache['access_token'] = payload['access_token']
        _token_cache['expires_at'] = now + payload.get('expires_in', 3600)
        logger.info('Interswitch OAuth token refreshed')
        return _token_cache['access_token']
    except Exception as exc:
        logger.error('Failed to fetch Interswitch token: %s', exc)
        raise


def _bearer_headers() -> dict:
    token = get_access_token()
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }


def search_transactions(params: dict) -> dict:
    """
    Call the Transaction Search API.
    params keys: merchantCode, terminalId, fromDate, toDate, amount, referenceNumber
    Returns raw API response dict.
    """
    try:
        resp = requests.get(
            TRANSACTION_SEARCH_URL,
            headers=_bearer_headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        logger.error('Transaction Search API error: %s — %s', exc, exc.response.text if exc.response else '')
        raise
    except Exception as exc:
        logger.error('Transaction Search request failed: %s', exc)
        raise


def aml_global_search(name: str, reference: str = '') -> dict:
    """
    Run a name through the Global Search AML API.
    Returns raw response with match score, sanctions list, PEP flag.
    """
    payload = {
        'name': name,
        'reference': reference or name,
        'searchType': 'INDIVIDUAL',
    }
    try:
        resp = requests.post(
            AML_GLOBAL_SEARCH_URL,
            headers=_bearer_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        logger.error('AML Global Search error: %s — %s', exc, exc.response.text if exc.response else '')
        raise
    except Exception as exc:
        logger.error('AML Global Search request failed: %s', exc)
        raise


def place_lien(account_number: str, amount: Decimal, reference: str, narration: str) -> dict:
    """
    Place a lien on an account via the Interswitch API.
    Returns raw response dict.
    """
    payload = {
        'accountNumber': account_number,
        'amount': str(amount),
        'reference': reference,
        'narration': narration,
    }
    try:
        resp = requests.post(
            PLACE_LIEN_URL,
            headers=_bearer_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        logger.error('Place Lien API error: %s — %s', exc, exc.response.text if exc.response else '')
        raise
    except Exception as exc:
        logger.error('Place Lien request failed: %s', exc)
        raise


def parse_aml_response(raw: dict) -> dict:
    """Extract structured AML data from raw API response."""
    hits = raw.get('hits', raw.get('matches', []))
    if not hits:
        return {
            'matched_name': '',
            'match_score': Decimal('0'),
            'sanctions_list': '',
            'is_pep': False,
            'match_type': '',
            'narrative': 'No matches found in global sanctions/PEP database.',
        }

    top = hits[0] if isinstance(hits, list) else hits
    score = Decimal(str(top.get('score', top.get('matchScore', 0))))
    is_pep = bool(top.get('isPEP', top.get('pep', False)))
    sanctions = top.get('listName', top.get('sanctionsList', ''))
    match_type = top.get('matchType', top.get('type', ''))
    matched_name = top.get('name', top.get('matchedName', ''))

    narrative_parts = []
    if score >= 80:
        narrative_parts.append(f'High-confidence match ({score}%) detected in global database.')
    elif score >= 50:
        narrative_parts.append(f'Moderate match ({score}%) found — manual review recommended.')
    else:
        narrative_parts.append(f'Partial match ({score}%) — low risk indicator.')

    if is_pep:
        narrative_parts.append('Subject identified as a Politically Exposed Person (PEP).')
    if sanctions:
        narrative_parts.append(f'Listed on: {sanctions}.')
    if match_type:
        narrative_parts.append(f'Match type: {match_type}.')

    return {
        'matched_name': matched_name,
        'match_score': score,
        'sanctions_list': sanctions,
        'is_pep': is_pep,
        'match_type': match_type,
        'narrative': ' '.join(narrative_parts),
    }
