from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Auth
    path('auth/login/', views.login_view, name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.me_view, name='me'),

    # Dashboard
    path('sg-dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),

    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/sync/', views.sync_transactions, name='sync_transactions'),
    path('transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<int:pk>/flag/', views.flag_transaction, name='flag_transaction'),

    # AML
    path('aml/check/<int:transaction_id>/', views.run_aml_check, name='run_aml_check'),
    path('aml/checks/', views.list_aml_checks, name='list_aml_checks'),

    # Liens
    path('liens/', views.LienListView.as_view(), name='lien_list'),
    path('liens/request/', views.request_lien, name='request_lien'),
    path('liens/<int:pk>/approve/', views.approve_lien, name='approve_lien'),
    path('liens/<int:pk>/reject/', views.reject_lien, name='reject_lien'),
    path('liens/<int:pk>/execute/', views.execute_lien, name='execute_lien'),

    # Audit logs
    path('audit-logs/', views.audit_logs, name='audit_logs'),

    # Users
    path('users/', views.users_list, name='users_list'),
]
