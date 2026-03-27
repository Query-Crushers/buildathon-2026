from django.urls import path

from . import views

urlpatterns = [
    path('cayu/authorize/', views.cayu_authorize, name='cayu_authorize'),
    path('cayu/callback/', views.cayu_callback, name='cayu_callback'),
    path('cayu/token-login/', views.token_login, name='cayu_token_login'),
    path('cayu/poll-token/', views.poll_token, name='cayu_poll_token'),
]
