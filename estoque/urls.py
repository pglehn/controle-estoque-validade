from django.urls import path
from . import views

app_name = "estoque"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("produtos/", views.produtos, name="produtos"),
    path("produtos/novo/", views.novo_produto, name="novo_produto"),
    path("lotes/", views.lotes, name="lotes"),
    path("lotes/novo/", views.novo_lote, name="novo_lote"),
    path("api/lotes/<int:lote_id>/", views.detalhe_lote_api, name="detalhe_lote_api"),
    path("movimentacoes/", views.movimentacoes, name="movimentacoes"),
    path("movimentacoes/nova/", views.nova_movimentacao, name="nova_movimentacao"),
]
