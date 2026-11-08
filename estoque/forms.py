from django import forms
from .models import Lote, Produto

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
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
