"""Regras transacionais para lançamentos de estoque."""
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from django.db import IntegrityError, transaction
from .models import Lote, Movimentacao


def _mesmo_lancamento(mov, lote_id, tipo, quantidade, motivo, usuario):
    return (mov.lote_id == lote_id and mov.tipo == tipo and mov.quantidade == quantidade
            and mov.motivo == motivo and mov.usuario_id == usuario.pk)


def registrar_movimentacao(*, lote_id, tipo, quantidade, motivo, usuario, chave):
    """Retorna (movimentação, criada). A mesma chave não pode lançar duas vezes."""
    try:
        quantidade = Decimal(str(quantidade))
        if not quantidade.is_finite() or quantidade <= 0:
            raise ValueError
        DecimalValidator(12, 2)(quantidade)
    except (InvalidOperation, ValueError, ValidationError):
        raise ValueError("Informe uma quantidade positiva com até duas casas decimais.")
    if tipo not in Movimentacao.Tipo.values:
        raise ValueError("Tipo de movimentação inválido.")
    motivo = (motivo or "").strip()
    if tipo == Movimentacao.Tipo.DESCARTE and not motivo:
        raise ValueError("Informe o motivo do descarte.")
    if not usuario or not usuario.is_authenticated:
        raise ValueError("É necessário um usuário autenticado.")

    def verifica_repeticao(mov):
        if not _mesmo_lancamento(mov, lote_id, tipo, quantidade, motivo, usuario):
            raise ValueError("Esta chave já foi usada em outro lançamento.")
        return mov, False

    try:
        with transaction.atomic():
            # No PostgreSQL, serializa alterações no mesmo lote.
            lote = Lote.objects.select_for_update().get(pk=lote_id)
            anterior = Movimentacao.objects.filter(chave_idempotencia=chave).first()
            if anterior:
                return verifica_repeticao(anterior)
            if tipo != Movimentacao.Tipo.ENTRADA and quantidade > lote.saldo:
                raise ValueError("Saldo insuficiente para esta movimentação.")
            novo_saldo = lote.saldo + quantidade if tipo == Movimentacao.Tipo.ENTRADA else lote.saldo - quantidade
            mov = Movimentacao.objects.create(
                lote=lote, tipo=tipo, quantidade=quantidade, motivo=motivo,
                usuario=usuario, chave_idempotencia=chave,
            )
            lote.saldo = novo_saldo
            lote.save(update_fields=["saldo"])
            return mov, True
    except IntegrityError:
        # Lotes diferentes com a mesma chave podem disputar o índice único.
        anterior = Movimentacao.objects.filter(chave_idempotencia=chave).first()
        if anterior:
            return verifica_repeticao(anterior)
        raise
