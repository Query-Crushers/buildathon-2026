"""
Background task processing for SwitchGuard.
Called after each new transaction is imported to evaluate risk and run AML if needed.
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

HIGH_RISK_AMOUNT = Decimal('5000000')  # 5 million NGN


def process_transaction_data(transaction):
    """
    Evaluate a newly imported transaction against risk rules.
    If flagged, automatically run AML check and send email notification.
    """
    try:
        _evaluate_risk(transaction)
        if transaction.status == 'flagged':
            _auto_aml_check(transaction)
    except Exception as exc:
        logger.error('Error processing transaction %s: %s', transaction.reference_id, exc)


def _evaluate_risk(transaction):
    from .models import Transaction
    risk = Transaction.RiskLevel.LOW
    flagged = False

    if transaction.amount >= HIGH_RISK_AMOUNT:
        risk = Transaction.RiskLevel.HIGH
        flagged = True

    if flagged:
        transaction.status = Transaction.Status.FLAGGED
    transaction.risk_level = risk
    transaction.save(update_fields=['status', 'risk_level'])


def _auto_aml_check(transaction):
    from .models import AMLCheck
    from .interswitch import aml_global_search, parse_aml_response
    from . import email_service

    if hasattr(transaction, 'aml_check'):
        return

    try:
        raw = aml_global_search(transaction.account_name, transaction.reference_id)
    except Exception as exc:
        logger.warning('AML API unavailable for auto-check on %s: %s', transaction.reference_id, exc)
        return

    parsed = parse_aml_response(raw)
    AMLCheck.objects.create(
        transaction=transaction,
        matched_name=parsed['matched_name'],
        match_score=parsed['match_score'],
        sanctions_list=parsed['sanctions_list'],
        is_pep=parsed['is_pep'],
        match_type=parsed['match_type'],
        narrative=parsed['narrative'],
        raw_response=raw,
    )
    email_service.send_transaction_flagged(transaction)
    logger.info('Auto AML check completed for %s — score: %s', transaction.reference_id, parsed['match_score'])
