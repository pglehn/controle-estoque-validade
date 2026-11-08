import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .forms import LoteForm, MovimentacaoForm
from .models import Lote, Movimentacao, Produto
from .services import registrar_movimentacao


class EstoqueBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operador", password="senha-forte-142")
        self.produto = Produto.objects.create(nome="Arroz", unidade="kg")
        self.lote = Lote.objects.create(produto=self.produto, codigo="A01", validade=timezone.localdate() + timedelta(days=20))

    def registrar(self, tipo, quantidade, chave=None, motivo=""):
        return registrar_movimentacao(lote_id=self.lote.pk, tipo=tipo, quantidade=Decimal(quantidade),
                                      motivo=motivo, usuario=self.user, chave=chave or uuid.uuid4())


class MovimentacaoTests(EstoqueBase):
    def test_entrada_saida_e_descarte_atualizam_saldo_e_historico(self):
        self.registrar("entrada", "10.00")
        self.registrar("saida", "3.00")
        self.registrar("descarte", "2.00", motivo="Embalagem danificada")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.saldo, Decimal("5.00"))
        self.assertEqual(Movimentacao.objects.count(), 3)

    def test_saldo_insuficiente_nao_cria_movimentacao(self):
        self.registrar("entrada", "2.00")
        with self.assertRaisesMessage(ValueError, "Saldo insuficiente"):
            self.registrar("saida", "3.00")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.saldo, Decimal("2.00"))
        self.assertEqual(Movimentacao.objects.count(), 1)

    def test_quantidade_invalida_e_motivo_obrigatorio(self):
        for quantidade in ("0", "-1", "1.001", "NaN"):
            with self.subTest(quantidade=quantidade), self.assertRaises(ValueError):
                self.registrar("entrada", quantidade)
        with self.assertRaisesMessage(ValueError, "motivo"):
            self.registrar("descarte", "1.00")
        self.assertEqual(Movimentacao.objects.count(), 0)

    def test_mesma_chave_e_mesmo_dado_nao_duplica(self):
        chave = uuid.uuid4()
        primeiro, criado1 = self.registrar("entrada", "4.00", chave=chave)
        segundo, criado2 = self.registrar("entrada", "4.00", chave=chave)
        self.lote.refresh_from_db()
        self.assertEqual(primeiro.pk, segundo.pk)
        self.assertTrue(criado1)
        self.assertFalse(criado2)
        self.assertEqual(self.lote.saldo, Decimal("4.00"))
        self.assertEqual(Movimentacao.objects.count(), 1)

    def test_mesma_chave_com_dados_diferentes_e_recusada(self):
        chave = uuid.uuid4()
        self.registrar("entrada", "4.00", chave=chave)
        with self.assertRaisesMessage(ValueError, "já foi usada"):
            self.registrar("entrada", "5.00", chave=chave)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.saldo, Decimal("4.00"))

    def test_lote_duplicado_por_produto_e_barrado_no_formulario(self):
        form = LoteForm({"produto": self.produto.pk, "codigo": "A01", "validade": "2027-01-01"})
        self.assertFalse(form.is_valid())

    def test_formulario_exige_motivo_para_descarte(self):
        form = MovimentacaoForm({"lote": self.lote.pk, "tipo": "descarte", "quantidade": "1",
                                 "motivo": "", "chave_idempotencia": str(uuid.uuid4())})
        self.assertFalse(form.is_valid())
        self.assertIn("motivo", form.errors)


class PaginasTests(EstoqueBase):
    def test_todas_as_telas_exigem_login(self):
        for nome in ("inicio", "produtos", "novo_produto", "lotes", "novo_lote", "movimentacoes", "nova_movimentacao"):
            with self.subTest(nome=nome):
                response = self.client.get(reverse("estoque:" + nome))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/entrar/", response.url)
        response = self.client.get(reverse("estoque:detalhe_lote_api", args=[self.lote.pk]))
        self.assertEqual(response.status_code, 302)

    def test_fluxo_web_cadastro_movimentacao_e_api(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("estoque:novo_produto"), {"nome": "Feijão", "unidade": "kg"})
        self.assertRedirects(response, reverse("estoque:produtos"))
        produto = Produto.objects.get(nome="Feijão")
        response = self.client.post(reverse("estoque:novo_lote"), {
            "produto": produto.pk, "codigo": "F01", "validade": "2027-01-01",
        })
        self.assertRedirects(response, reverse("estoque:lotes"))
        lote = Lote.objects.get(codigo="F01")
        response = self.client.post(reverse("estoque:nova_movimentacao"), {
            "lote": lote.pk, "tipo": "entrada", "quantidade": "5.50", "motivo": "",
            "chave_idempotencia": str(uuid.uuid4()),
        })
        self.assertRedirects(response, reverse("estoque:movimentacoes"))
        lote.refresh_from_db()
        self.assertEqual(lote.saldo, Decimal("5.50"))
        response = self.client.get(reverse("estoque:detalhe_lote_api", args=[lote.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saldo"], "5.50")
        self.assertEqual(response.json()["unidade"], "kg")
        self.assertEqual(self.client.post(reverse("estoque:detalhe_lote_api", args=[lote.pk])).status_code, 405)

    def test_formularios_vazios_exibem_os_erros_de_validacao(self):
        self.client.force_login(self.user)
        for nome in ("novo_produto", "novo_lote", "nova_movimentacao"):
            with self.subTest(formulario=nome):
                response = self.client.post(reverse("estoque:" + nome), {})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].is_bound)
                self.assertTrue(response.context["form"].errors)
        self.assertEqual(Produto.objects.count(), 1)
        self.assertEqual(Lote.objects.count(), 1)
        self.assertEqual(Movimentacao.objects.count(), 0)

    def test_reenvio_web_idempotente(self):
        self.client.force_login(self.user)
        data = {"lote": self.lote.pk, "tipo": "entrada", "quantidade": "3.00", "motivo": "",
                "chave_idempotencia": str(uuid.uuid4())}
        self.assertEqual(self.client.post(reverse("estoque:nova_movimentacao"), data).status_code, 302)
        self.assertEqual(self.client.post(reverse("estoque:nova_movimentacao"), data).status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.saldo, Decimal("3.00"))
        self.assertEqual(Movimentacao.objects.count(), 1)

    def test_protecao_csrf_nos_formularios(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        self.assertEqual(cliente.post(reverse("estoque:novo_produto"), {"nome": "Teste", "unidade": "un"}).status_code, 403)

    def test_filtro_de_movimentacao(self):
        self.client.force_login(self.user)
        self.registrar("entrada", "3")
        self.registrar("saida", "1")
        response = self.client.get(reverse("estoque:movimentacoes"), {"tipo": "saida"})
        self.assertEqual(len(response.context["movimentacoes"]), 1)
        self.assertEqual(response.context["movimentacoes"][0].tipo, "saida")


class ValidadeTests(EstoqueBase):
    def test_limites_de_validade_e_saldo_zero(self):
        hoje = timezone.localdate()
        cenarios = [
            (-1, Decimal("1"), "vencido"),
            (0, Decimal("1"), "proximo"),
            (7, Decimal("1"), "proximo"),
            (8, Decimal("1"), "regular"),
            (-1, Decimal("0"), "sem_saldo"),
        ]
        for dias, saldo, esperado in cenarios:
            with self.subTest(dias=dias, saldo=saldo):
                self.lote.validade = hoje + timedelta(days=dias)
                self.lote.saldo = saldo
                self.assertEqual(self.lote.status_validade, esperado)

    def test_dashboard_e_filtro_ignoram_lotes_vencidos_sem_saldo(self):
        hoje = timezone.localdate()
        self.lote.validade = hoje - timedelta(days=1)
        self.lote.saldo = Decimal("1")
        self.lote.save()
        Lote.objects.create(produto=self.produto, codigo="SEM", validade=hoje - timedelta(days=5))
        Lote.objects.create(produto=self.produto, codigo="HOJE", validade=hoje, saldo=Decimal("2"))
        self.client.force_login(self.user)
        response = self.client.get(reverse("estoque:inicio"))
        self.assertEqual(response.context["vencidos"], 1)
        self.assertEqual(response.context["proximos"], 1)
        response = self.client.get(reverse("estoque:lotes"), {"status": "vencido"})
        self.assertEqual(list(response.context["lotes"].values_list("codigo", flat=True)), ["A01"])


class ConfiguracaoTests(SimpleTestCase):
    def carregar_configuracao(self, alteracoes, remover=()):
        ambiente = os.environ.copy()
        for chave in remover:
            ambiente.pop(chave, None)
        ambiente.update(alteracoes)
        return subprocess.run(
            [sys.executable, "-c", (
                "import configuracao.settings as s; "
                "print(s.DEBUG, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE)"
            )],
            env=ambiente, capture_output=True, text=True,
        )

    def test_modo_local_aceita_configuracao_de_demonstracao(self):
        resultado = self.carregar_configuracao(
            {"DJANGO_DEBUG": "true", "DB_ENGINE": "sqlite"}, remover=("DJANGO_SECRET_KEY",)
        )
        self.assertEqual(resultado.returncode, 0)
        self.assertEqual(resultado.stdout.strip(), "True False False")

    def test_modo_sem_debug_rejeita_chave_ausente_ou_padrao(self):
        for chave in (None, "", "   ", "somente-desenvolvimento-altere-esta-chave"):
            with self.subTest(chave=chave):
                valores = {"DJANGO_DEBUG": "false", "DB_ENGINE": "sqlite"}
                if chave is not None:
                    valores["DJANGO_SECRET_KEY"] = chave
                resultado = self.carregar_configuracao(valores, remover=("DJANGO_SECRET_KEY",))
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn("DJANGO_SECRET_KEY", resultado.stderr)

    def test_modo_sem_debug_exige_cookies_seguros(self):
        resultado = self.carregar_configuracao({
            "DJANGO_DEBUG": "false", "DB_ENGINE": "sqlite",
            "DJANGO_SECRET_KEY": "exemplo-exclusivamente-para-teste-automático",
        })
        self.assertEqual(resultado.returncode, 0)
        self.assertEqual(resultado.stdout.strip(), "False True True")

    def test_banco_digitado_errado_nao_seleciona_sqlite(self):
        resultado = self.carregar_configuracao({"DJANGO_DEBUG": "true", "DB_ENGINE": "postgress"})
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("DB_ENGINE", resultado.stderr)


@skipUnless(connection.vendor == "postgresql", "Concorrência com bloqueio de linha requer PostgreSQL")
class ConcorrenciaPostgresTests(TransactionTestCase):
    def test_saidas_simultaneas_nao_deixam_saldo_negativo(self):
        usuario = get_user_model().objects.create_user(username="concurrente", password="forte-1234")
        produto = Produto.objects.create(nome="Leite", unidade="l")
        lote = Lote.objects.create(produto=produto, codigo="L01", validade=timezone.localdate(), saldo=Decimal("1"))
        barreira = Barrier(2)

        def retirar():
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=usuario.pk)
                barreira.wait(timeout=10)
                try:
                    registrar_movimentacao(lote_id=lote.pk, tipo="saida", quantidade=Decimal("1"),
                                           motivo="", usuario=user, chave=uuid.uuid4())
                    return "ok"
                except ValueError:
                    return "insuficiente"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: retirar(), range(2)))
        lote.refresh_from_db()
        self.assertCountEqual(resultados, ["ok", "insuficiente"])
        self.assertEqual(lote.saldo, Decimal("0"))
        self.assertEqual(Movimentacao.objects.count(), 1)
