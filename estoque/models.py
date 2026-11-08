from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

class Produto(models.Model):
    class Unidade(models.TextChoices):
        UNIDADE = "un", "Unidade"
        QUILOGRAMA = "kg", "Quilograma"
        LITRO = "l", "Litro"

    nome = models.CharField(max_length=120, unique=True)
    unidade = models.CharField(max_length=2, choices=Unidade.choices, default=Unidade.UNIDADE)

    class Meta:
        ordering = ["nome"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"

    def __str__(self):
        return f"{self.nome} ({self.get_unidade_display()})"


class Lote(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="lotes")
    codigo = models.CharField("código do lote", max_length=60)
    validade = models.DateField("data de validade")
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        ordering = ["validade", "produto__nome", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["produto", "codigo"], name="lote_unico_por_produto"),
            models.CheckConstraint(condition=models.Q(saldo__gte=0), name="lote_saldo_nao_negativo"),
        ]
        verbose_name = "lote"
        verbose_name_plural = "lotes"

    def __str__(self):
        return f"{self.produto.nome} — lote {self.codigo}"

    @property
    def status_validade(self):
        if self.saldo <= 0:
            return "sem_saldo"
        hoje = timezone.localdate()
        if self.validade < hoje:
            return "vencido"
        if self.validade <= hoje + timedelta(days=settings.DIAS_ALERTA_VALIDADE):
            return "proximo"
        return "regular"


class Movimentacao(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"
        DESCARTE = "descarte", "Descarte"

    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="movimentacoes")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    quantidade = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=255, blank=True)
    registrada_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    chave_idempotencia = models.UUIDField(unique=True, editable=False)

    class Meta:
        ordering = ["-registrada_em", "-id"]
        constraints = [models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="mov_quantidade_positiva")]
        verbose_name = "movimentação"
        verbose_name_plural = "movimentações"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.lote} — {self.quantidade}"
