from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import LoteForm, MovimentacaoForm, ProdutoForm
from .models import Lote, Movimentacao, Produto
from .services import registrar_movimentacao

@login_required
def inicio(request):
    return render(request, "estoque/inicio.html")

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
    return render(request, "estoque/lotes.html", {"lotes": lotes})

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
    itens = Movimentacao.objects.select_related("lote__produto", "usuario")[:100]
    return render(request, "estoque/movimentacoes.html", {"movimentacoes": itens})

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
    })
