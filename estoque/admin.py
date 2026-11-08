from django.contrib import admin
from .models import Lote, Movimentacao, Produto

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "unidade")
    search_fields = ("nome",)

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("produto", "codigo", "validade", "saldo")
    search_fields = ("produto__nome", "codigo")
    readonly_fields = ("saldo",)


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ("lote", "tipo", "quantidade", "usuario", "registrada_em")
    list_filter = ("tipo",)
    readonly_fields = ("lote", "tipo", "quantidade", "motivo", "usuario", "registrada_em", "chave_idempotencia")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
