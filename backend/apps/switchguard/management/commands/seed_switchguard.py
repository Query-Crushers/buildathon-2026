"""
Seed SwitchGuard Analytics with demo users and transactions.
Usage: python manage.py seed_switchguard
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import User
from apps.switchguard.models import AMLCheck, AuditLog, LienRequest, Transaction


BANKS = [
    'First Bank of Nigeria', 'Zenith Bank', 'GTBank', 'Access Bank',
    'UBA', 'Fidelity Bank', 'Sterling Bank', 'Polaris Bank',
]

NAMES = [
    'Adebayo Johnson', 'Chioma Okafor', 'Emeka Nwosu', 'Fatima Al-Hassan',
    'Gbenga Adeleke', 'Halima Bello', 'Ibrahim Musa', 'Josephine Obi',
    'Kayode Fashola', 'Lola Adeyemi', 'Mohammed Sani', 'Ngozi Ezeh',
    'Olawale Peters', 'Patience Uche', 'Rotimi Alade', 'Seun Bankole',
    'Tunde Afolabi', 'Uche Nnamdi', 'Vivian Eze', 'Wale Osunde',
]

STATUSES = [
    Transaction.Status.CLEAN, Transaction.Status.CLEAN, Transaction.Status.CLEAN,
    Transaction.Status.CLEAN, Transaction.Status.FLAGGED, Transaction.Status.FLAGGED,
    Transaction.Status.UNDER_REVIEW, Transaction.Status.LIEN_PLACED,
]

RISK_LEVELS = [
    Transaction.RiskLevel.LOW, Transaction.RiskLevel.LOW, Transaction.RiskLevel.LOW,
    Transaction.RiskLevel.MEDIUM, Transaction.RiskLevel.MEDIUM,
    Transaction.RiskLevel.HIGH, Transaction.RiskLevel.CRITICAL,
]


class Command(BaseCommand):
    help = 'Seed SwitchGuard Analytics with demo users and transactions'

    def handle(self, *args, **options):
        self._create_users()
        self._create_transactions()
        self.stdout.write(self.style.SUCCESS('SwitchGuard seed data created successfully.'))

    def _create_users(self):
        users = [
            ('admin@switchguard.com', 'SwitchGuard@2024', 'admin', 'Admin', 'User'),
            ('supervisor@switchguard.com', 'SwitchGuard@2024', 'supervisor', 'Jane', 'Supervisor'),
            ('analyst@switchguard.com', 'SwitchGuard@2024', 'analyst', 'John', 'Analyst'),
        ]
        for email, password, role, first, last in users:
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password=password,
                    role=role,
                    first_name=first,
                    last_name=last,
                    is_active=True,
                )
                self.stdout.write(f'  Created user: {email}')
            else:
                self.stdout.write(f'  User exists: {email}')

    def _create_transactions(self):
        if Transaction.objects.count() >= 20:
            self.stdout.write('  Transactions already seeded.')
            return

        analyst = User.objects.filter(role='analyst').first()
        supervisor = User.objects.filter(role='supervisor').first()
        now = timezone.now()

        transactions = []
        for i in range(20):
            name = NAMES[i]
            ref = f'TXN{100000 + i:06d}'
            amount = Decimal(str(random.choice([
                50000, 125000, 250000, 500000, 750000,
                1200000, 2500000, 5000000, 8000000, 10000000,
            ])))
            txn_status = random.choice(STATUSES)
            risk = random.choice(RISK_LEVELS)
            date = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

            txn = Transaction.objects.create(
                reference_id=ref,
                date=date,
                amount=amount,
                currency='NGN',
                account_name=name,
                account_number=f'00{random.randint(10000000, 99999999)}',
                originating_bank=random.choice(BANKS),
                status=txn_status,
                risk_level=risk,
            )
            transactions.append(txn)

        # Add AML checks for flagged/under_review/lien_placed transactions
        for txn in transactions:
            if txn.status in ['flagged', 'under_review', 'lien_placed']:
                score = Decimal(str(random.randint(55, 95)))
                AMLCheck.objects.create(
                    transaction=txn,
                    matched_name=txn.account_name,
                    match_score=score,
                    sanctions_list=random.choice(['OFAC SDN', 'EU Consolidated', 'UN Security Council']),
                    is_pep=score > 80,
                    match_type=random.choice(['EXACT', 'FUZZY', 'PARTIAL']),
                    narrative=f'Match score {score}% detected. Subject may appear on international sanctions list.',
                    checked_by=analyst,
                )

        # Add lien requests for lien_placed transactions
        for txn in transactions:
            if txn.status == 'lien_placed':
                lien = LienRequest.objects.create(
                    transaction=txn,
                    aml_check=getattr(txn, 'aml_check', None),
                    requested_by=analyst,
                    approved_by=supervisor,
                    notes=f'High risk transaction flagged by automated system. AML match confirmed. Lien placed per compliance protocol.',
                    status=LienRequest.Status.EXECUTED,
                    resolved_at=now,
                )

        # Add an open pending lien request
        pending_txn = next((t for t in transactions if t.status == 'under_review'), None)
        if pending_txn and analyst:
            LienRequest.objects.get_or_create(
                transaction=pending_txn,
                defaults=dict(
                    aml_check=getattr(pending_txn, 'aml_check', None),
                    requested_by=analyst,
                    notes='Transaction flagged for sanctions list match. Requesting supervisor approval to place lien.',
                    status=LienRequest.Status.PENDING,
                )
            )

        self.stdout.write(f'  Created 20 transactions with AML checks and lien records.')
