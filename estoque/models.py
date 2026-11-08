from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

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
