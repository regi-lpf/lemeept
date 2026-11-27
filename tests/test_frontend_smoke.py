import functools
import http.server
import json
import os
import threading
import unittest
from pathlib import Path

from lemeept_extractor.models import PainelEptV4Output

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightError = Exception
    sync_playwright = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOADER_PATH = PROJECT_ROOT / "public" / "loader-elementor.html"
WIDGET_PATH = PROJECT_ROOT / "public" / "widget-elementor.html"
JSON_PATH = PROJECT_ROOT / "public" / "painel-ept-v4.json"
ELEMENTOR_HOST_PATH = "/__elementor_host__.html"


def _make_defense(
    id_: str,
    ano: int,
    autor: str,
    orientador: str,
    titulo: str,
    linha: str,
    macro: str,
    base: str,
    produto: dict | None = None,
) -> dict:
    partes_busca = [id_.lower(), str(ano), autor.lower(), orientador.lower(), titulo.lower(), linha.lower(), macro.lower()]
    termos = ["EPT", "Educação Profissional"]
    if produto:
        partes_busca.append(produto["titulo"].lower())
        partes_busca.append(produto["formato"].lower())
        termos.extend(produto.get("palavras_chave", []))

    return {
        "schema_version": "4.0",
        "id": id_,
        "ano": ano,
        "autor": autor,
        "orientador": orientador,
        "coorientadores": [],
        "instituicao": "Instituto Federal Catarinense (IFC)",
        "campus": "IFC Blumenau",
        "linha_pesquisa": linha,
        "macroprojeto": macro,
        "dissertacao": {
            "titulo": titulo,
            "link": f"https://exemplo.edu.br/pdfs/{id_}.pdf",
            "resumo": f"Resumo da dissertação {id_} voltada à educação profissional e tecnológica.",
            "palavras_chave": ["EPT", "Ensino Médio Integrado"],
            "autores_referenciados": ["Paulo Freire", "Dermeval Saviani"],
            "base_epistemologica": {
                "valor": base,
                "candidato": None,
                "confianca": "alta",
                "revisao_pendente": False,
                "curado_humano": False,
                "justificativa": "Fundamentação explícita na obra.",
                "evidencias": [
                    {
                        "secao": "Metodologia",
                        "pagina": 42,
                        "trecho": "Articulação crítica com o mundo do trabalho.",
                        "referencia_correspondente": "Saviani, 2007",
                    }
                ],
            },
        },
        "produto": produto,
        "indice_busca": {
            "texto_busca_normalizado": " ".join(partes_busca),
            "termos_unificados": termos,
            "tem_produto_vinculado": produto is not None,
            "tem_resumo": True,
        },
    }


def _fixture_mista() -> dict:
    defesas = [
        _make_defense(
            id_="EPT-9001",
            ano=2024,
            autor="Ana Souza",
            orientador="Carlos Lima",
            titulo="Formação Docente Integrada",
            linha="LP1",
            macro="MP3",
            base="Pedagogia Histórico-Crítica",
            produto={
                "titulo": "Cartilha de Formação Docente",
                "tipo": "material_didatico_instrucional",
                "formato": "Cartilha",
                "link": "https://educapes.capes.gov.br/handle/capes/9001",
                "publico_alvo": ["estudantes_alunos"],
                "nivel_aplicacao": "Ensino Médio Integrado",
                "palavras_chave": ["Cartilha", "Docência"],
                "data_publicacao": "2024-11",
                "autores_colaboradores": [],
                "identificadores": [],
                "proveniencia": {
                    "fonte_tipo_escolhida": "dissertacao_ficha",
                    "rotulo_original_declarado": "Cartilha Pedagógica",
                    "colecao_educapes": None,
                    "dc_type_educapes": [],
                },
            },
        ),
        _make_defense(
            id_="EPT-9002",
            ano=2025,
            autor="Bruno Silva",
            orientador="Carlos Lima",
            titulo="Tecnologias Digitais em Laboratório",
            linha="LP2",
            macro="MP1",
            base="Educação Libertadora / Freireana",
            produto={
                "titulo": "Aplicativo de Apoio ao Estágio",
                "tipo": "software_aplicativo",
                "formato": "Aplicativo",
                "link": "https://educapes.capes.gov.br/handle/capes/9002",
                "publico_alvo": ["docentes_professores"],
                "nivel_aplicacao": "Ensino Superior",
                "palavras_chave": ["Aplicativo", "Estágio"],
                "data_publicacao": "2025-03",
                "autores_colaboradores": [],
                "identificadores": [],
                "proveniencia": {
                    "fonte_tipo_escolhida": "dissertacao_ficha",
                    "rotulo_original_declarado": "Aplicativo Educacional",
                    "colecao_educapes": None,
                    "dc_type_educapes": [],
                },
            },
        ),
        _make_defense(
            id_="EPT-9003",
            ano=2025,
            autor="Clara Mendes",
            orientador="Helena Rocha",
            titulo="Memórias e Trabalho na Rede Federal",
            linha="LP2",
            macro="MP4",
            base="Pedagogia Histórico-Crítica",
            produto=None,
        ),
    ]
    payload = {
        "schema_version": "4.0",
        "gerado_em": "2026-11-25T12:00:00+00:00",
        "total_defesas": 3,
        "total_producoes": 5,
        "defesas": defesas,
    }
    PainelEptV4Output.model_validate(payload)
    return payload


def _fixture_somente_dissertacoes() -> dict:
    defesas = [
        _make_defense(
            id_="EPT-9101",
            ano=2024,
            autor="Diego Santos",
            orientador="Marina Alves",
            titulo="História do Ensino Técnico Regional",
            linha="LP2",
            macro="MP4",
            base="Pedagogia Histórico-Crítica",
            produto=None,
        ),
        _make_defense(
            id_="EPT-9102",
            ano=2025,
            autor="Elena Costa",
            orientador="Marina Alves",
            titulo="Currículo Integrado e Prática Social",
            linha="LP1",
            macro="MP3",
            base="Educação Libertadora / Freireana",
            produto=None,
        ),
    ]
    payload = {
        "schema_version": "4.0",
        "gerado_em": "2026-11-25T12:00:00+00:00",
        "total_defesas": 2,
        "total_producoes": 2,
        "defesas": defesas,
    }
    PainelEptV4Output.model_validate(payload)
    return payload


class _SmokeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == ELEMENTOR_HOST_PATH:
            loader_html = LOADER_PATH.read_text(encoding="utf-8")
            html_doc = (
                "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
                "<title>Host WordPress Simulado</title></head><body>"
                "<main id='wp-elementor-container'>"
                f"{loader_html}"
                "</main></body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_doc)))
            self.end_headers()
            self.wfile.write(html_doc)
            return
        super().do_GET()


class TestFrontendSmoke(unittest.TestCase):
    server: http.server.ThreadingHTTPServer | None = None
    server_thread: threading.Thread | None = None
    base_url: str = ""
    playwright_ctx = None
    browser = None

    @classmethod
    def setUpClass(cls) -> None:
        require_smoke = os.environ.get("LEMEEPT_REQUIRE_SMOKE") == "1"
        if sync_playwright is None:
            msg = (
                "Playwright nao instalado no ambiente. "
                "Execute: uv sync --group dev && uv run playwright install chromium"
            )
            if require_smoke:
                raise RuntimeError(msg)
            raise unittest.SkipTest(msg)

        try:
            cls.playwright_ctx = sync_playwright().start()
            cls.browser = cls.playwright_ctx.chromium.launch(headless=True)
        except PlaywrightError as exc:
            if cls.playwright_ctx is not None:
                cls.playwright_ctx.stop()
                cls.playwright_ctx = None
            msg = (
                f"Chromium do Playwright indisponivel ({exc}). "
                "Execute: uv sync --group dev && uv run playwright install chromium"
            )
            if require_smoke:
                raise RuntimeError(msg) from exc
            raise unittest.SkipTest(msg) from exc

        handler = functools.partial(_SmokeHTTPRequestHandler, directory=str(PROJECT_ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.browser is not None:
            cls.browser.close()
            cls.browser = None
        if cls.playwright_ctx is not None:
            cls.playwright_ctx.stop()
            cls.playwright_ctx = None
        if cls.server is not None:
            cls.server.shutdown()
            cls.server.server_close()
            cls.server = None

    def _abrir_pagina(self, rota_map: dict[str, tuple[str, str]] | None = None):
        assert self.browser is not None
        context = self.browser.new_context(viewport={"width": 1366, "height": 900})
        page_errors: list[str] = []
        console_errors: list[str] = []

        def _interceptar(route):
            url = route.request.url
            if rota_map:
                for sufixo, (body, content_type) in rota_map.items():
                    if sufixo in url:
                        route.fulfill(status=200, content_type=content_type, body=body)
                        return
            if url.startswith(self.base_url):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", _interceptar)
        page = context.new_page()
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        return context, page, page_errors, console_errors

    def test_index_acervo_completo_interacoes_principais(self) -> None:
        json_real = JSON_PATH.read_text(encoding="utf-8")
        dados_reais = json.loads(json_real)
        esperado_defesas = str(dados_reais["total_defesas"])
        esperado_producoes = str(dados_reais["total_producoes"])
        context, page, page_errors, console_errors = self._abrir_pagina(
            {"/public/painel-ept-v4.json": (json_real, "application/json; charset=utf-8")}
        )
        try:
            page.goto(f"{self.base_url}/index.html", wait_until="domcontentloaded")
            page.wait_for_function(
                f"document.getElementById('leme-stat-total')?.textContent === {json.dumps(esperado_defesas)}"
            )
            self.assertEqual(page.locator("#leme-stat-producoes").inner_text(), esperado_producoes)
            self.assertTrue(page.locator(".leme-scope-bar").is_visible())
            self.assertEqual(page.locator("#leme-resultados .leme-card").count(), 12)

            page.click("button[data-escopo='dissertacoes']")
            self.assertEqual(page.locator("#leme-chart-ano-title").inner_text(), "Dissertações defendidas por ano")
            self.assertFalse(page.locator(".leme-chart-card[data-chart-scope='todas produtos']").first.is_visible())

            page.click("button[data-escopo='produtos']")
            self.assertIn("is-scope-produtos", page.locator(".leme-charts-grid").get_attribute("class") or "")
            self.assertTrue(page.locator("#leme-chart-formato").is_visible())

            page.click("button[data-escopo='todas']")
            page.click("button[data-tipo-tab='formato_produto']")
            self.assertTrue(page.locator("#leme-expand-tipo-formato").is_visible())
            page.click("#leme-expand-tipo-formato")
            self.assertIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")
            page.click("#leme-modal-close")
            self.assertNotIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")

            page.locator("#leme-chart-ano button.leme-year-col").first.click()
            self.assertGreaterEqual(page.locator("#leme-graficos-filtros .leme-chip").count(), 1)
            page.click("#leme-limpar")
            self.assertEqual(page.locator("#leme-graficos-filtros .leme-chip").count(), 0)

            page.fill("#leme-busca", "Freire")
            page.wait_for_selector("#leme-resultados mark.leme-highlight")
            self.assertGreater(page.locator("#leme-resultados .leme-card").count(), 0)
            page.click("#leme-limpar")
            self.assertEqual(page.locator("#leme-resultados .leme-card").count(), 12)

            page.locator(".leme-card-detail-btn").first.click()
            self.assertIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")
            page.click("#leme-modal-close")
            self.assertNotIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")

            page.click("#leme-view-table")
            self.assertGreater(page.locator("table.leme-table tbody tr").count(), 0)

            self.assertEqual(page_errors, [])
            self.assertEqual(console_errors, [])
        finally:
            context.close()

    def test_index_acervo_misto_contagens_e_filtros(self) -> None:
        mista_json = json.dumps(_fixture_mista(), ensure_ascii=False)
        context, page, page_errors, console_errors = self._abrir_pagina(
            {"/public/painel-ept-v4.json": (mista_json, "application/json; charset=utf-8")}
        )
        try:
            page.goto(f"{self.base_url}/index.html", wait_until="domcontentloaded")
            page.wait_for_function("document.getElementById('leme-stat-total')?.textContent === '3'")
            self.assertEqual(page.locator("#leme-stat-producoes").inner_text(), "5")
            self.assertEqual(page.locator("#leme-insights .leme-insight-card strong").first.inner_text(), "5")

            ano_2024_val = page.locator("#leme-chart-ano button.leme-year-col[data-filter-valor='2024'] .leme-year-value").inner_text()
            ano_2025_val = page.locator("#leme-chart-ano button.leme-year-col[data-filter-valor='2025'] .leme-year-value").inner_text()
            self.assertEqual(ano_2024_val, "2")
            self.assertEqual(ano_2025_val, "3")

            page.click("button[data-escopo='produtos']")
            self.assertEqual(page.locator("#leme-resultados .leme-card").count(), 2)
            ano_2025_prod_val = page.locator(
                "#leme-chart-ano button.leme-year-col[data-filter-valor='2025'] .leme-year-value"
            ).inner_text()
            self.assertEqual(ano_2025_prod_val, "1")
            page.select_option("#leme-filtro-ano", "2025")
            self.assertEqual(page.locator("#leme-resultados .leme-card").count(), 1)
            ano_count_txt = page.locator("#leme-filtro-ano").locator("xpath=..").locator(".leme-field-count").inner_text()
            self.assertIn("1 registro(s) nesta opção", ano_count_txt)
            page.click("#leme-limpar")

            page.click("button[data-escopo='todas']")
            page.click("button[data-tipo-tab='formato_produto']")
            page.click("#leme-expand-tipo-formato")
            page.wait_for_selector("#leme-modal-backdrop.is-open #leme-ranking-status")
            modal_status = page.locator("#leme-ranking-status").text_content() or ""
            self.assertIn("produtos neste formato (% sobre 2)", modal_status)
            page.click("#leme-modal-close")

            page.click("#leme-view-table")
            self.assertIn("Sem produto vinculado", page.locator("table.leme-table").inner_text())

            self.assertEqual(page_errors, [])
            self.assertEqual(console_errors, [])
        finally:
            context.close()

    def test_index_somente_dissertacoes_oculta_controles_produto(self) -> None:
        diss_json = json.dumps(_fixture_somente_dissertacoes(), ensure_ascii=False)
        context, page, page_errors, console_errors = self._abrir_pagina(
            {"/public/painel-ept-v4.json": (diss_json, "application/json; charset=utf-8")}
        )
        try:
            page.goto(f"{self.base_url}/index.html", wait_until="domcontentloaded")
            page.wait_for_function("document.getElementById('leme-stat-total')?.textContent === '2'")
            self.assertEqual(page.locator("#leme-stat-producoes").inner_text(), "2")

            self.assertFalse(page.locator(".leme-scope-bar").is_visible())
            for select_id in ("#leme-filtro-tipo", "#leme-filtro-publico", "#leme-filtro-nivel"):
                self.assertFalse(page.locator(select_id).is_visible())
            for chart_id in ("#leme-chart-tipo", "#leme-chart-publico", "#leme-chart-nivel", "#leme-chart-formato"):
                self.assertFalse(page.locator(chart_id).is_visible())

            self.assertEqual(page.locator("#leme-chart-ano-title").inner_text(), "Dissertações defendidas por ano")
            self.assertEqual(page.locator("#leme-resultados .leme-card").count(), 2)

            self.assertEqual(page_errors, [])
            self.assertEqual(console_errors, [])
        finally:
            context.close()

    def test_fluxo_elementor_loader_e_widget_publicado(self) -> None:
        widget_html = WIDGET_PATH.read_text(encoding="utf-8")
        json_real = JSON_PATH.read_text(encoding="utf-8")
        dados_reais = json.loads(json_real)
        esperado_defesas = str(dados_reais["total_defesas"])
        esperado_producoes = str(dados_reais["total_producoes"])
        context, page, page_errors, console_errors = self._abrir_pagina(
            {
                "/public/widget-elementor.html": (widget_html, "text/html; charset=utf-8"),
                "/public/painel-ept-v4.json": (json_real, "application/json; charset=utf-8"),
            }
        )
        try:
            page.goto(f"{self.base_url}{ELEMENTOR_HOST_PATH}", wait_until="domcontentloaded")
            page.wait_for_selector("#leme-painel-ept")
            self.assertEqual(page.locator("#leme-painel-loader").count(), 0)
            page.wait_for_function(
                f"document.getElementById('leme-stat-total')?.textContent === {json.dumps(esperado_defesas)}"
            )
            self.assertEqual(page.locator("#leme-stat-producoes").inner_text(), esperado_producoes)
            self.assertGreaterEqual(page.locator("#leme-resultados .leme-card").count(), 1)

            page.click("button[data-escopo='produtos']")
            self.assertTrue(page.locator("#leme-chart-formato").is_visible())

            self.assertEqual(page.locator("#leme-controles").get_attribute("tabindex"), "-1")

            page.click("button[data-escopo='todas']")
            page.click("button[data-open-ranking='autor_referenciado']")
            self.assertIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")
            page.fill("#leme-ranking-busca", "Freire")
            page.locator("#leme-ranking-busca").press("Escape")
            self.assertIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")
            self.assertEqual(page.locator("#leme-ranking-busca").input_value(), "")
            page.locator("#leme-ranking-busca").press("Escape")
            self.assertNotIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")

            page.locator("#leme-chart-base button.leme-bar-row.is-clickable").first.click()
            page.wait_for_timeout(400)

            page.locator(".leme-card-detail-btn").first.click()
            self.assertIn("is-open", page.locator("#leme-modal-backdrop").get_attribute("class") or "")
            page.click("#leme-modal-close")

            self.assertEqual(page_errors, [])
            self.assertEqual(console_errors, [])
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
