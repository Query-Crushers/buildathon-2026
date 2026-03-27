from rest_framework import serializers

from apps.users.models import User
from .models import AMLCheck, AuditLog, LienRequest, Transaction


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role']


class TransactionSerializer(serializers.ModelSerializer):
    has_aml_check = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'reference_id', 'date', 'amount', 'currency',
            'account_name', 'account_number', 'originating_bank',
            'status', 'risk_level', 'created_at', 'updated_at', 'has_aml_check',
        ]

    def get_has_aml_check(self, obj):
        return hasattr(obj, 'aml_check')


class AMLCheckSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer(read_only=True)
    checked_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = AMLCheck
        fields = [
            'id', 'transaction', 'matched_name', 'match_score',
            'sanctions_list', 'is_pep', 'match_type', 'narrative',
            'raw_response', 'checked_at', 'checked_by',
        ]


class LienRequestSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer(read_only=True)
    requested_by = UserBriefSerializer(read_only=True)
    approved_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = LienRequest
        fields = [
            'id', 'transaction', 'requested_by', 'approved_by',
            'notes', 'supervisor_notes', 'status',
            'requested_at', 'resolved_at', 'interswitch_response',
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'entity_type', 'entity_id', 'detail', 'timestamp']
