from django.urls import path
from . import views

urlpatterns = [
    path('telegram/webhook', views.webhook, name='telegram-webhook'),
    path('telegram/healthcheck', views.healthcheck, name='telegram-healthcheck'),
]
