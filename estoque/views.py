from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET
from .forms import LoteForm, MovimentacaoForm, ProdutoForm
from .models import Lote, Movimentacao, Produto
from .services import registrar_movimentacao

@login_required
def inicio(request):
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=settings.DIAS_ALERTA_VALIDADE)
    lotes_com_saldo = Lote.objects.filter(saldo__gt=0)
    contexto = {
        "total_produtos": Produto.objects.count(),
        "total_lotes": lotes_com_saldo.count(),
        "vencidos": lotes_com_saldo.filter(validade__lt=hoje).count(),
        "proximos": lotes_com_saldo.filter(validade__range=(hoje, limite)).count(),
        "alertas": lotes_com_saldo.filter(validade__lte=limite).select_related("produto")[:8],
        "dias_alerta": settings.DIAS_ALERTA_VALIDADE,
    }
    return render(request, "estoque/inicio.html", contexto)

@login_required
def produtos(request):
    return render(request, "estoque/produtos.html", {"produtos": Produto.objects.all()})

@login_required
def novo_produto(request):
    form = ProdutoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produto cadastrado com sucesso.")
        return redirect("estoque:produtos")
    return render(request, "estoque/formulario.html", {
        "form": form, "titulo": "Cadastrar produto", "voltar": "estoque:produtos",
    })

@login_required
def lotes(request):
    lotes = Lote.objects.select_related("produto").all()
    filtro = request.GET.get("status", "")
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=settings.DIAS_ALERTA_VALIDADE)
    if filtro == "vencido":
        lotes = lotes.filter(saldo__gt=0, validade__lt=hoje)
    elif filtro == "proximo":
        lotes = lotes.filter(saldo__gt=0, validade__range=(hoje, limite))
    elif filtro == "regular":
        lotes = lotes.filter(saldo__gt=0, validade__gt=limite)
    elif filtro == "sem_saldo":
        lotes = lotes.filter(saldo=0)
    else:
        filtro = ""
    return render(request, "estoque/lotes.html", {"lotes": lotes, "filtro": filtro})

@login_required
def novo_lote(request):
    form = LoteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Lote cadastrado. Registre uma entrada para adicionar saldo.")
        return redirect("estoque:lotes")
    return render(request, "estoque/formulario.html", {
        "form": form, "titulo": "Cadastrar lote", "voltar": "estoque:lotes",
        "ajuda": "O lote começa com saldo zero. Registre uma entrada para adicionar quantidade.",
    })


@login_required
def movimentacoes(request):
    itens = Movimentacao.objects.select_related("lote__produto", "usuario")
    tipo = request.GET.get("tipo", "")
    if tipo in Movimentacao.Tipo.values:
        itens = itens.filter(tipo=tipo)
    else:
        tipo = ""
    return render(request, "estoque/movimentacoes.html", {"movimentacoes": itens[:100], "tipo": tipo,
                                                           "tipos": Movimentacao.Tipo.choices})

@login_required
def nova_movimentacao(request):
    form = MovimentacaoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        try:
            _, criada = registrar_movimentacao(
                lote_id=dados["lote"].pk, tipo=dados["tipo"], quantidade=dados["quantidade"],
                motivo=dados["motivo"], usuario=request.user, chave=dados["chave_idempotencia"],
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            if criada:
                messages.success(request, "Movimentação registrada com sucesso.")
            else:
                messages.info(request, "Este lançamento já havia sido registrado.")
            return redirect("estoque:movimentacoes")
    return render(request, "estoque/formulario.html", {
        "form": form, "titulo": "Registrar movimentação", "voltar": "estoque:movimentacoes",
        "ajuda": "Escolha o lote e informe a quantidade. Para descartes, informe também o motivo.",
        "mostrar_saldo_lote": True,
    })


@login_required
@require_GET
def detalhe_lote_api(request, lote_id):
    lote = get_object_or_404(Lote.objects.select_related("produto"), pk=lote_id)
    return JsonResponse({"saldo": str(lote.saldo), "unidade": lote.produto.unidade,
                         "validade": lote.validade.strftime("%d/%m/%Y"),
                         "status": lote.status_validade})
