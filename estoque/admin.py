from django.contrib import admin
from .models import Lote, Produto

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "unidade")
    search_fields = ("nome",)

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("produto", "codigo", "validade", "saldo")
    search_fields = ("produto__nome", "codigo")
    readonly_fields = ("saldo",)
