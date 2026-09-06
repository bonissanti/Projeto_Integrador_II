from django.urls import path
from . import views

urlpatterns = [
    path('whatsapp/webhook', views.webhook, name='whatsapp-webhook'),
]
