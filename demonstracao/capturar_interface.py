"""Gera evidências da aplicação real usando um banco temporário e dados fictícios."""
import os
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import django
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracao.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone


def aguardar_servidor(url):
    for _ in range(60):
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.5)
    raise RuntimeError("O servidor de demonstração não respondeu.")


def main():
    # Banco criado para esta execução do CI, sem dados de pessoas ou parceiros reais.
    call_command("migrate", interactive=False, verbosity=0)
    get_user_model().objects.create_user(
        username="dados_ficticios", password="senha-exclusiva-para-demonstracao-123",
    )
    directory = ROOT / "evidencias"
    directory.mkdir(exist_ok=True)
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "manage.py"), "runserver", "127.0.0.1:8000", "--noreload"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        aguardar_servidor("http://127.0.0.1:8000/entrar/")
        with sync_playwright() as playwright:
            chrome = shutil.which("google-chrome") or shutil.which("chromium")
            if not chrome:
                raise RuntimeError("Chrome ou Chromium não encontrado no ambiente de demonstração.")
            browser = playwright.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            page.goto("http://127.0.0.1:8000/entrar/", wait_until="networkidle")
            page.get_by_label("Usuário").fill("dados_ficticios")
            page.get_by_label("Senha").fill("senha-exclusiva-para-demonstracao-123")
            page.get_by_role("button", name="Entrar").click()
            expect(page.get_by_role("heading", name="Estoque em Dia")).to_be_visible()

            registros = [
                ("Arroz integral", "kg", "Quilograma", "AR-01", 30, "25.00"),
                ("Leite integral", "l", "Litro", "LE-02", 2, "8.00"),
                ("Feijão carioca", "kg", "Quilograma", "FE-03", -1, "6.00"),
            ]
            hoje = timezone.localdate()
            for nome, unidade, unidade_label, codigo, prazo, quantidade in registros:
                page.goto("http://127.0.0.1:8000/produtos/novo/")
                page.locator("#id_nome").fill(nome)
                page.locator("#id_unidade").select_option(unidade)
                page.get_by_role("button", name="Salvar").click()
                expect(page.get_by_text("Produto cadastrado com sucesso.")).to_be_visible()

                page.goto("http://127.0.0.1:8000/lotes/novo/")
                page.locator("#id_produto").select_option(label=f"{nome} ({unidade_label})")
                page.locator("#id_codigo").fill(codigo)
                page.locator("#id_validade").fill((hoje + timedelta(days=prazo)).isoformat())
                page.get_by_role("button", name="Salvar").click()
                expect(page.get_by_text("Lote cadastrado", exact=False)).to_be_visible()

                page.goto("http://127.0.0.1:8000/movimentacoes/nova/")
                page.locator("#id_lote").select_option(label=f"{nome} — lote {codigo}")
                page.locator("#id_tipo").select_option("entrada")
                page.locator("#id_quantidade").fill(quantidade)
                page.get_by_role("button", name="Salvar").click()
                expect(page.get_by_text("Movimentação registrada com sucesso.")).to_be_visible()

            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            expect(page.get_by_text("Leite integral", exact=False)).to_be_visible()
            expect(page.get_by_text("Feijão carioca", exact=False)).to_be_visible()
            page.screenshot(path=str(directory / "01_painel_operacao.jpg"), type="jpeg", quality=82, full_page=True)

            page.goto("http://127.0.0.1:8000/lotes/", wait_until="networkidle")
            expect(page.locator("span.badge").filter(has_text="Próximo")).to_be_visible()
            expect(page.locator("span.badge").filter(has_text="Vencido")).to_be_visible()
            expect(page.locator("span.badge").filter(has_text="Em dia")).to_be_visible()
            page.screenshot(path=str(directory / "02_lotes_e_validade.jpg"), type="jpeg", quality=82, full_page=True)
            browser.close()
            print("Interface real executada com dados fictícios; duas capturas geradas.")
    finally:
        server.terminate()
        server.wait(timeout=15)


if __name__ == "__main__":
    main()
