from django.contrib import admin

from .models import AMLCheck, AuditLog, LienRequest, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference_id', 'account_name', 'amount', 'currency', 'status', 'risk_level', 'date']
    list_filter = ['status', 'risk_level', 'currency']
    search_fields = ['reference_id', 'account_name', 'account_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AMLCheck)
class AMLCheckAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'matched_name', 'match_score', 'is_pep', 'checked_at']
    list_filter = ['is_pep']
    search_fields = ['transaction__reference_id', 'matched_name']


@admin.register(LienRequest)
class LienRequestAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'requested_by', 'approved_by', 'status', 'requested_at']
    list_filter = ['status']
    search_fields = ['transaction__reference_id']
    readonly_fields = ['requested_at', 'resolved_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'entity_type', 'entity_id', 'timestamp']
    list_filter = ['action', 'entity_type']
    readonly_fields = ['timestamp']
