from django.conf import settings
from django.db import models


class Transaction(models.Model):
    class Status(models.TextChoices):
        CLEAN = 'clean', 'Clean'
        FLAGGED = 'flagged', 'Flagged'
        UNDER_REVIEW = 'under_review', 'Under Review'
        LIEN_PLACED = 'lien_placed', 'Lien Placed'

    class RiskLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    reference_id = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10, default='NGN')
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    originating_bank = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CLEAN)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    raw_api_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.reference_id} - {self.account_name}'


class AMLCheck(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='aml_check')
    matched_name = models.CharField(max_length=255, blank=True)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sanctions_list = models.CharField(max_length=255, blank=True)
    is_pep = models.BooleanField(default=False)
    match_type = models.CharField(max_length=100, blank=True)
    narrative = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='aml_checks'
    )

    def __str__(self):
        return f'AML Check for {self.transaction.reference_id} - score: {self.match_score}'


class LienRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EXECUTED = 'executed', 'Executed'

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='lien_requests')
    aml_check = models.ForeignKey(AMLCheck, on_delete=models.SET_NULL, null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lien_requests_made'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lien_requests_approved'
    )
    notes = models.TextField()
    supervisor_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    interswitch_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'Lien on {self.transaction.reference_id} - {self.status}'


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50, blank=True)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} by {self.user} at {self.timestamp}'
