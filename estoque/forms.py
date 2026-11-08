import uuid
from decimal import Decimal
from django import forms
from .models import Lote, Movimentacao, Produto

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.is_hidden:
                css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
                field.widget.attrs["class"] = css

class ProdutoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "unidade"]
        labels = {"nome": "Nome do produto", "unidade": "Unidade de medida"}

class LoteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Lote
        fields = ["produto", "codigo", "validade"]
        widgets = {"validade": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class MovimentacaoForm(BootstrapFormMixin, forms.Form):
    lote = forms.ModelChoiceField(queryset=Lote.objects.select_related("produto"), label="Lote")
    tipo = forms.ChoiceField(choices=Movimentacao.Tipo.choices, label="Tipo de movimentação")
    quantidade = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"),
                                    label="Quantidade", widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}))
    motivo = forms.CharField(max_length=255, required=False, label="Motivo do descarte (obrigatório para descarte)")
    chave_idempotencia = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("tipo") == Movimentacao.Tipo.DESCARTE and not cleaned.get("motivo", "").strip():
            self.add_error("motivo", "Informe o motivo do descarte.")
        return cleaned
