"""
SendGrid email notifications for SwitchGuard Analytics.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _send(to_emails: list, subject: str, html_content: str):
    api_key = getattr(settings, 'SENDGRID_API_KEY', '')
    if not api_key:
        logger.warning('SENDGRID_API_KEY not set — skipping email: %s', subject)
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@switchguard.com')
        for email in to_emails:
            message = Mail(
                from_email=from_email,
                to_emails=email,
                subject=subject,
                html_content=html_content,
            )
            sg.send(message)
        logger.info('Email sent: %s → %s', subject, to_emails)
    except Exception as exc:
        logger.error('SendGrid error sending "%s": %s', subject, exc)


def _supervisor_emails():
    from apps.users.models import User
    return list(User.objects.filter(role__in=['supervisor', 'admin'], is_active=True).values_list('email', flat=True))


def send_transaction_flagged(transaction):
    emails = _supervisor_emails()
    if not emails:
        return
    subject = f'⚠️ Transaction Flagged for AML Review — {transaction.reference_id}'
    html = f"""
    <h2>Transaction Flagged for AML Review</h2>
    <p>A transaction has been automatically flagged and requires your attention.</p>
    <table>
      <tr><td><b>Reference ID</b></td><td>{transaction.reference_id}</td></tr>
      <tr><td><b>Amount</b></td><td>{transaction.currency} {transaction.amount:,}</td></tr>
      <tr><td><b>Account Name</b></td><td>{transaction.account_name}</td></tr>
      <tr><td><b>Account Number</b></td><td>{transaction.account_number}</td></tr>
      <tr><td><b>Risk Level</b></td><td>{transaction.risk_level.upper()}</td></tr>
      <tr><td><b>Date</b></td><td>{transaction.date}</td></tr>
    </table>
    <p>Please log in to SwitchGuard Analytics to review this transaction.</p>
    """
    _send(emails, subject, html)


def send_lien_requested(lien_request):
    emails = _supervisor_emails()
    if not emails:
        return
    txn = lien_request.transaction
    subject = f'🔴 Lien Approval Required — {txn.reference_id}'
    aml_score = ''
    if hasattr(txn, 'aml_check'):
        aml_score = f'<tr><td><b>AML Match Score</b></td><td>{txn.aml_check.match_score}%</td></tr>'
    html = f"""
    <h2>Lien Placement Request</h2>
    <p>Analyst <b>{lien_request.requested_by.get_full_name() or lien_request.requested_by.email}</b>
       has submitted a lien placement request for your approval.</p>
    <table>
      <tr><td><b>Reference ID</b></td><td>{txn.reference_id}</td></tr>
      <tr><td><b>Amount</b></td><td>{txn.currency} {txn.amount:,}</td></tr>
      <tr><td><b>Account</b></td><td>{txn.account_name} ({txn.account_number})</td></tr>
      {aml_score}
    </table>
    <p><b>Analyst Notes:</b><br>{lien_request.notes}</p>
    <p>Please log in to SwitchGuard Analytics to approve or reject this request.</p>
    """
    _send(emails, subject, html)


def send_lien_executed(lien_request):
    emails = []
    if lien_request.requested_by:
        emails.append(lien_request.requested_by.email)
    compliance = getattr(settings, 'COMPLIANCE_EMAIL', '')
    if compliance:
        emails.append(compliance)
    if not emails:
        return
    txn = lien_request.transaction
    approver = lien_request.approved_by.email if lien_request.approved_by else 'System'
    subject = f'✅ Lien Placed on Account {txn.account_number} — {txn.reference_id}'
    html = f"""
    <h2>Lien Successfully Placed</h2>
    <p>A lien has been placed on account <b>{txn.account_number}</b>.</p>
    <table>
      <tr><td><b>Reference ID</b></td><td>{txn.reference_id}</td></tr>
      <tr><td><b>Account Name</b></td><td>{txn.account_name}</td></tr>
      <tr><td><b>Account Number</b></td><td>{txn.account_number}</td></tr>
      <tr><td><b>Amount</b></td><td>{txn.currency} {txn.amount:,}</td></tr>
      <tr><td><b>Requested by</b></td><td>{lien_request.requested_by.email}</td></tr>
      <tr><td><b>Approved by</b></td><td>{approver}</td></tr>
    </table>
    <p>This action has been logged in the audit trail.</p>
    """
    _send(emails, subject, html)


def send_lien_rejected(lien_request):
    if not lien_request.requested_by:
        return
    txn = lien_request.transaction
    subject = f'Lien Request Rejected — {txn.reference_id}'
    html = f"""
    <h2>Lien Request Rejected</h2>
    <p>Your lien placement request for transaction <b>{txn.reference_id}</b> has been rejected.</p>
    <table>
      <tr><td><b>Account</b></td><td>{txn.account_name} ({txn.account_number})</td></tr>
      <tr><td><b>Approved/Rejected by</b></td><td>{lien_request.approved_by.email if lien_request.approved_by else 'Supervisor'}</td></tr>
    </table>
    {"<p><b>Supervisor Notes:</b><br>" + lien_request.supervisor_notes + "</p>" if lien_request.supervisor_notes else ""}
    """
    _send([lien_request.requested_by.email], subject, html)
