from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import LoteForm, ProdutoForm
from .models import Lote, Produto

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
