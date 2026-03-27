import logging
from datetime import timedelta

from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from .models import AMLCheck, AuditLog, LienRequest, Transaction
from .serializers import (
    AMLCheckSerializer,
    AuditLogSerializer,
    LienRequestSerializer,
    TransactionSerializer,
    UserBriefSerializer,
)

logger = logging.getLogger(__name__)


def _log(user, action, entity_type='', entity_id='', detail=''):
    AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        detail=detail,
    )


def _require_roles(request, *roles):
    if not request.user.is_authenticated:
        raise PermissionDenied('Authentication required.')
    if request.user.role not in roles:
        raise PermissionDenied(f'Requires one of roles: {", ".join(roles)}.')


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([])
def login_view(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '').strip()
    if not email or not password:
        return Response({'detail': 'Email and password required.'}, status=400)

    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials.'}, status=401)
    if not user.is_active:
        return Response({'detail': 'Account disabled.'}, status=403)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserBriefSerializer(user).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserBriefSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    now = timezone.now()
    since = now - timedelta(days=30)
    txns = Transaction.objects.filter(date__gte=since)

    total = txns.count()
    flagged = txns.filter(status__in=['flagged', 'under_review', 'lien_placed']).count()
    aml_hits = AMLCheck.objects.filter(transaction__date__gte=since, match_score__gt=0).count()
    liens = LienRequest.objects.filter(requested_at__gte=since).count()

    # 7-day volume
    volume_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = Transaction.objects.filter(date__gte=day_start, date__lt=day_end).count()
        volume_data.append({
            'date': day_start.strftime('%b %d'),
            'transactions': count,
        })

    # Risk distribution
    risk_dist = {
        'clean': Transaction.objects.filter(status='clean').count(),
        'flagged': Transaction.objects.filter(status='flagged').count(),
        'under_review': Transaction.objects.filter(status='under_review').count(),
        'lien_placed': Transaction.objects.filter(status='lien_placed').count(),
    }

    return Response({
        'kpis': {
            'total_transactions': total,
            'flagged_transactions': flagged,
            'flagged_pct': round(flagged / total * 100, 1) if total else 0,
            'aml_hits': aml_hits,
            'liens_placed': liens,
        },
        'volume_chart': volume_data,
        'risk_distribution': risk_dist,
    })


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class TransactionPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Transaction.objects.all()

        # Filters
        status_filter = request.query_params.get('status')
        risk_filter = request.query_params.get('risk_level')
        search = request.query_params.get('search', '').strip()
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        amount_min = request.query_params.get('amount_min')
        amount_max = request.query_params.get('amount_max')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if risk_filter:
            qs = qs.filter(risk_level=risk_filter)
        if search:
            qs = qs.filter(
                Q(reference_id__icontains=search) |
                Q(account_name__icontains=search) |
                Q(account_number__icontains=search)
            )
        if date_from:
            qs = qs.filter(date__date__gte=date_from)
        if date_to:
            qs = qs.filter(date__date__lte=date_to)
        if amount_min:
            qs = qs.filter(amount__gte=amount_min)
        if amount_max:
            qs = qs.filter(amount__lte=amount_max)

        paginator = TransactionPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = TransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            txn = Transaction.objects.select_related('aml_check').get(pk=pk)
        except Transaction.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        data = TransactionSerializer(txn).data
        if hasattr(txn, 'aml_check'):
            data['aml_check'] = AMLCheckSerializer(txn.aml_check).data
        return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def flag_transaction(request, pk):
    try:
        txn = Transaction.objects.get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    txn.status = Transaction.Status.FLAGGED
    txn.save()
    _log(request.user, 'flag_transaction', 'Transaction', pk)
    return Response(TransactionSerializer(txn).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_transactions(request):
    """Fetch fresh data from Interswitch Transaction Search API."""
    from .interswitch import search_transactions
    from .tasks import process_transaction_data

    params = {
        'merchantCode': request.data.get('merchantCode', ''),
        'terminalId': request.data.get('terminalId', ''),
        'fromDate': request.data.get('fromDate', ''),
        'toDate': request.data.get('toDate', ''),
    }
    try:
        raw = search_transactions(params)
        transactions_data = raw.get('transactions', raw.get('data', []))
        created = 0
        for item in transactions_data:
            ref = item.get('transactionReference', item.get('referenceNumber', ''))
            if not ref:
                continue
            txn, is_new = Transaction.objects.get_or_create(
                reference_id=ref,
                defaults={
                    'date': item.get('transactionDate', timezone.now()),
                    'amount': item.get('amount', 0),
                    'currency': item.get('currency', 'NGN'),
                    'account_name': item.get('accountName', ''),
                    'account_number': item.get('accountNumber', ''),
                    'originating_bank': item.get('bankName', ''),
                    'raw_api_response': item,
                }
            )
            if is_new:
                created += 1
                process_transaction_data(txn)

        _log(request.user, 'sync_transactions', detail=f'{created} new transactions imported')
        return Response({'synced': len(transactions_data), 'created': created})
    except Exception as exc:
        return Response({'detail': f'Sync failed: {exc}'}, status=502)


# ---------------------------------------------------------------------------
# AML Checks
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_aml_check(request, transaction_id):
    try:
        txn = Transaction.objects.get(pk=transaction_id)
    except Transaction.DoesNotExist:
        return Response({'detail': 'Transaction not found.'}, status=404)

    if hasattr(txn, 'aml_check'):
        return Response(AMLCheckSerializer(txn.aml_check).data)

    from .interswitch import aml_global_search, parse_aml_response
    from . import email_service

    try:
        raw = aml_global_search(txn.account_name, txn.reference_id)
    except Exception as exc:
        # Use mock data if API unavailable (demo mode)
        logger.warning('AML API unavailable, using mock data: %s', exc)
        raw = _mock_aml_response(txn.account_name)

    parsed = parse_aml_response(raw)
    check = AMLCheck.objects.create(
        transaction=txn,
        matched_name=parsed['matched_name'],
        match_score=parsed['match_score'],
        sanctions_list=parsed['sanctions_list'],
        is_pep=parsed['is_pep'],
        match_type=parsed['match_type'],
        narrative=parsed['narrative'],
        raw_response=raw,
        checked_by=request.user,
    )

    # Update transaction risk level based on score
    score = float(parsed['match_score'])
    if score >= 80:
        txn.risk_level = Transaction.RiskLevel.CRITICAL
    elif score >= 60:
        txn.risk_level = Transaction.RiskLevel.HIGH
    elif score >= 30:
        txn.risk_level = Transaction.RiskLevel.MEDIUM

    if score > 0:
        txn.status = Transaction.Status.UNDER_REVIEW
        email_service.send_transaction_flagged(txn)

    txn.save()
    _log(request.user, 'run_aml_check', 'Transaction', transaction_id,
         f'Score: {parsed["match_score"]}')
    return Response(AMLCheckSerializer(check).data, status=201)


def _mock_aml_response(name: str) -> dict:
    """Return plausible mock AML data for demo purposes."""
    import hashlib
    # Deterministic score based on name hash
    h = int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % 100
    if h < 40:
        return {'hits': []}
    return {
        'hits': [{
            'name': name,
            'score': h,
            'listName': 'OFAC SDN' if h > 70 else 'EU Consolidated',
            'isPEP': h > 85,
            'matchType': 'EXACT' if h > 90 else 'FUZZY',
        }]
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_aml_checks(request):
    qs = AMLCheck.objects.select_related('transaction', 'checked_by').order_by('-checked_at')
    paginator = TransactionPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(AMLCheckSerializer(page, many=True).data)


# ---------------------------------------------------------------------------
# Lien Requests
# ---------------------------------------------------------------------------

class LienListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LienRequest.objects.select_related(
            'transaction', 'requested_by', 'approved_by'
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = TransactionPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(LienRequestSerializer(page, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_lien(request):
    _require_roles(request, 'analyst', 'supervisor', 'admin')
    transaction_id = request.data.get('transaction_id')
    notes = request.data.get('notes', '').strip()

    if not transaction_id:
        return Response({'detail': 'transaction_id required.'}, status=400)
    if len(notes) < 20:
        return Response({'detail': 'Notes must be at least 20 characters.'}, status=400)

    try:
        txn = Transaction.objects.get(pk=transaction_id)
    except Transaction.DoesNotExist:
        return Response({'detail': 'Transaction not found.'}, status=404)

    aml_check = getattr(txn, 'aml_check', None)
    lien = LienRequest.objects.create(
        transaction=txn,
        aml_check=aml_check,
        requested_by=request.user,
        notes=notes,
        status=LienRequest.Status.PENDING,
    )
    txn.status = Transaction.Status.UNDER_REVIEW
    txn.save()

    from . import email_service
    email_service.send_lien_requested(lien)
    _log(request.user, 'request_lien', 'LienRequest', lien.id, f'Txn: {txn.reference_id}')
    return Response(LienRequestSerializer(lien).data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_lien(request, pk):
    _require_roles(request, 'supervisor', 'admin')
    try:
        lien = LienRequest.objects.select_related('transaction').get(pk=pk)
    except LienRequest.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if lien.status != LienRequest.Status.PENDING:
        return Response({'detail': 'Only pending requests can be approved.'}, status=400)

    lien.status = LienRequest.Status.APPROVED
    lien.approved_by = request.user
    lien.supervisor_notes = request.data.get('supervisor_notes', '')
    lien.save()
    _log(request.user, 'approve_lien', 'LienRequest', pk)
    return Response(LienRequestSerializer(lien).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_lien(request, pk):
    _require_roles(request, 'supervisor', 'admin')
    try:
        lien = LienRequest.objects.select_related('transaction').get(pk=pk)
    except LienRequest.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if lien.status != LienRequest.Status.PENDING:
        return Response({'detail': 'Only pending requests can be rejected.'}, status=400)

    lien.status = LienRequest.Status.REJECTED
    lien.approved_by = request.user
    lien.supervisor_notes = request.data.get('supervisor_notes', '')
    lien.resolved_at = timezone.now()
    lien.save()

    from . import email_service
    email_service.send_lien_rejected(lien)
    _log(request.user, 'reject_lien', 'LienRequest', pk)
    return Response(LienRequestSerializer(lien).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_lien(request, pk):
    _require_roles(request, 'supervisor', 'admin')
    try:
        lien = LienRequest.objects.select_related('transaction').get(pk=pk)
    except LienRequest.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if lien.status not in [LienRequest.Status.PENDING, LienRequest.Status.APPROVED]:
        return Response({'detail': 'Lien must be pending or approved to execute.'}, status=400)

    txn = lien.transaction
    from .interswitch import place_lien
    try:
        resp = place_lien(
            account_number=txn.account_number,
            amount=txn.amount,
            reference=txn.reference_id,
            narration=lien.notes[:200],
        )
        lien.interswitch_response = resp
    except Exception as exc:
        logger.warning('Place Lien API unavailable, recording as executed: %s', exc)
        lien.interswitch_response = {'demo': True, 'note': str(exc)}

    lien.status = LienRequest.Status.EXECUTED
    lien.approved_by = lien.approved_by or request.user
    lien.resolved_at = timezone.now()
    lien.save()

    txn.status = Transaction.Status.LIEN_PLACED
    txn.save()

    from . import email_service
    email_service.send_lien_executed(lien)
    _log(request.user, 'execute_lien', 'LienRequest', pk, f'Account: {txn.account_number}')
    return Response(LienRequestSerializer(lien).data)


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs(request):
    _require_roles(request, 'admin')
    qs = AuditLog.objects.select_related('user').all()
    paginator = TransactionPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(AuditLogSerializer(page, many=True).data)


# ---------------------------------------------------------------------------
# User management (Admin only)
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def users_list(request):
    _require_roles(request, 'admin')
    if request.method == 'GET':
        users = User.objects.all().order_by('email')
        return Response(UserBriefSerializer(users, many=True).data)

    # POST — create user
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '').strip()
    role = request.data.get('role', 'analyst')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not email or not password:
        return Response({'detail': 'email and password required.'}, status=400)
    if role not in [r.value for r in User.Role]:
        return Response({'detail': 'Invalid role.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'detail': 'Email already in use.'}, status=400)

    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
        first_name=first_name,
        last_name=last_name,
    )
    return Response(UserBriefSerializer(user).data, status=201)
