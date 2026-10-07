from django.urls import path
from Agendamento import views

urlpatterns = [
    path('agendamento/', views.agendamento, name='agendamento'),
    path('estoque/', views.estoque_cabelo, name='estoque_cabelo'),
    path('estoque/<int:hair_stock_id>/', views.editar_ou_remover_hair_stock, name='editar_remover_estoque'),
    path('estoque/<int:hair_stock_id>/movimentar/', views.movimentar_estoque, name='movimentar_estoque'),
    path('estoque/<int:hair_stock_id>/historico/', views.historico_movimentacoes, name='historico_movimentacoes'),
]