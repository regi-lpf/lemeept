"""Compilador e validador zero-dependência do widget Elementor (`public/widget-elementor.html`)."""

from __future__ import annotations

import argparse
import gzip
import html
import html.parser
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Optional, Sequence

VOID_HTML_TAGS = {"meta", "link", "br", "hr", "img", "input"}

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "frontend"
DEFAULT_CONFIG_FILENAME = "lemeept.toml"
DEFAULT_OUTPUT_DIRNAME = "public"
ENV_CONFIG_VAR = "LEMEEPT_CONFIG"

DEFAULT_FRONTEND_CONFIG: dict[str, str] = {
    "titulo": "Painel Bibliométrico",
    "titulo_pagina": "",
    "subtitulo": "Explore dissertações e produtos educacionais por tema, autor, orientador, ano, linha e macroprojeto.",
    "eyebrow": "PAINEL BIBLIOMÉTRICO",
    "titulo_graficos": "Panorama da Produção",
    "json_url": "./public/painel-ept-v4.json",
    "json_url_local": "./public/painel-ept-v4.json",
    "widget_url": "",
    "loader_texto": "Carregando painel bibliométrico...",
    "loader_erro_log": "Falha ao carregar widget:",
}


def _derivar_widget_url(json_url: str) -> str:
    url = (json_url or "").strip()
    if not url.lower().startswith(("http://", "https://")) or "/" not in url:
        return ""
    base, arquivo = url.rsplit("/", 1)
    return f"{base}/widget-elementor.html" if arquivo.lower().endswith(".json") else ""


def _localizar_arquivo_config(
    config_path: Optional[Path],
    root: Optional[Path],
) -> Optional[Path]:
    if config_path is not None:
        caminho = Path(config_path)
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho}")
        return caminho

    env_val = (os.getenv(ENV_CONFIG_VAR) or "").strip()
    if env_val:
        caminho_env = Path(env_val)
        if not caminho_env.exists():
            raise FileNotFoundError(
                f"Arquivo configurado em {ENV_CONFIG_VAR} não encontrado: {caminho_env}"
            )
        return caminho_env

    candidato = (root or Path.cwd()).resolve() / DEFAULT_CONFIG_FILENAME
    return candidato if candidato.exists() else None


def carregar_config_frontend(
    config_path: Optional[Path] = None,
    *,
    root: Optional[Path] = None,
    overrides: Optional[dict[str, Optional[str]]] = None,
) -> dict[str, str]:
    """Carrega `[frontend]` de `lemeept.toml` (via stdlib `tomllib`) e aplica overrides."""
    cfg = dict(DEFAULT_FRONTEND_CONFIG)
    caminho_cfg = _localizar_arquivo_config(config_path, root)

    if caminho_cfg is not None:
        dados = tomllib.loads(caminho_cfg.read_text(encoding="utf-8"))
        secao_fe = dados.get("frontend")
        if isinstance(secao_fe, dict):
            for chave in DEFAULT_FRONTEND_CONFIG:
                if secao_fe.get(chave) is not None:
                    cfg[chave] = str(secao_fe[chave])

    for chave, valor in (overrides or {}).items():
        if valor is not None and chave in cfg:
            cfg[chave] = str(valor)

    if not cfg["titulo_pagina"].strip():
        cfg["titulo_pagina"] = cfg["titulo"]
    if not cfg["widget_url"].strip():
        cfg["widget_url"] = _derivar_widget_url(cfg["json_url"])

    return cfg


def _resolver_asset_template(nome: str) -> Path:
    candidato_tpl = TEMPLATES_DIR / nome
    if candidato_tpl.exists():
        return candidato_tpl
    if nome in ("styles.css", "app.js"):
        parents = Path(__file__).resolve().parents
        if len(parents) > 2:
            candidato_repo = parents[2] / "frontend" / nome
            if candidato_repo.exists():
                return candidato_repo
    raise FileNotFoundError(f"Asset de template do frontend não encontrado: {nome}")


def renderizar_index_template(frontend_cfg: dict[str, str]) -> str:
    """Renderiza `index.html` parametrizado a partir do template embutido."""
    tpl = _resolver_asset_template("index.template.html").read_text(encoding="utf-8")
    substituicoes = {
        "{{TITULO_PAGINA}}": html.escape(frontend_cfg.get("titulo_pagina") or frontend_cfg.get("titulo", ""), quote=True),
        "{{JSON_URL}}": html.escape(frontend_cfg.get("json_url", ""), quote=True),
        "{{JSON_URL_LOCAL}}": html.escape(frontend_cfg.get("json_url_local", "./public/painel-ept-v4.json"), quote=True),
        "{{EYEBROW}}": html.escape(frontend_cfg.get("eyebrow", ""), quote=True),
        "{{TITULO}}": html.escape(frontend_cfg.get("titulo", ""), quote=True),
        "{{SUBTITULO}}": html.escape(frontend_cfg.get("subtitulo", ""), quote=True),
        "{{TITULO_GRAFICOS}}": html.escape(frontend_cfg.get("titulo_graficos", ""), quote=True),
    }
    resultado = tpl
    for marcador, valor in substituicoes.items():
        resultado = resultado.replace(marcador, valor)
    return resultado


def renderizar_loader_template(frontend_cfg: dict[str, str]) -> str:
    """Renderiza `public/loader-elementor.html` parametrizado a partir do template embutido."""
    tpl = _resolver_asset_template("loader-elementor.template.html").read_text(encoding="utf-8")
    erro_js = json.dumps(
        frontend_cfg.get("loader_erro_log") or "Falha ao carregar widget:",
        ensure_ascii=False,
    )[1:-1].replace("</", "<\\/")
    substituicoes = {
        "{{WIDGET_URL}}": html.escape(frontend_cfg.get("widget_url", ""), quote=True),
        "{{LOADER_TEXTO}}": html.escape(frontend_cfg.get("loader_texto", ""), quote=True),
        "{{LOADER_ERRO_LOG}}": erro_js,
    }
    resultado = tpl
    for marcador, valor in substituicoes.items():
        resultado = resultado.replace(marcador, valor)
    return resultado


def extrair_secao_raiz(html_doc: str) -> tuple[str, str]:
    """Extrai o fragmento `<section id=\"leme-painel-ept\" ...>...</section>` respeitando secoes aninhadas."""
    m_start = re.search(r'<section\b[^>]*\bid="leme-painel-ept"[^>]*>', html_doc)
    if not m_start:
        raise ValueError('Nao foi possivel localizar `<section id="leme-painel-ept">` em index.html.')

    pos = m_start.end()
    tag_re = re.compile(r"</?section\b[^>]*>", re.I)
    profundidade = 1
    m_end = None
    for m in tag_re.finditer(html_doc, pos):
        token = m.group(0).lower()
        if token.startswith("</section"):
            profundidade -= 1
            if profundidade == 0:
                m_end = m
                break
        else:
            profundidade += 1

    if m_end is None:
        raise ValueError('Tag de fechamento `</section>` correspondente a `#leme-painel-ept` nao encontrada.')

    abertura = m_start.group(0)
    miolo = html_doc[m_start.end() : m_end.start()]
    return abertura, miolo


def compactar_css(css_src: str) -> str:
    """Remove comentarios CSS, indentacao e linhas em branco (wpautop-safe)."""
    sem_com: list[str] = []
    i = 0
    n = len(css_src)
    quote = ""
    while i < n:
        ch = css_src[i]
        if quote:
            sem_com.append(ch)
            if ch == "\\" and i + 1 < n:
                i += 1
                sem_com.append(css_src[i])
            elif ch == quote:
                quote = ""
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            sem_com.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and css_src[i + 1] == "*":
            fim = css_src.find("*/", i + 2)
            if fim == -1:
                raise ValueError("Comentario CSS nao terminado (`/*`).")
            i = fim + 2
            continue
        sem_com.append(ch)
        i += 1
    if quote:
        raise ValueError("String CSS nao terminada.")
    return "\n".join(linha.strip() for linha in "".join(sem_com).splitlines() if linha.strip())


def compactar_html(abertura_sec: str, miolo_html: str) -> tuple[str, str]:
    """Remove indentacao e linhas em branco preservando espacos inline do HTML."""
    abertura_min = " ".join(abertura_sec.split())
    miolo_min = "\n".join(linha.strip() for linha in miolo_html.splitlines() if linha.strip())
    return abertura_min, miolo_min


def compactar_js_seguro(js_src: str) -> str:
    """Remove comentarios de linha inteira, indentacao e linhas em branco (wpautop-safe)."""
    normalizado = js_src.replace("\r\n", "\n").replace("\r", "\n")
    linhas_compactas: list[str] = []
    for linha in normalizado.splitlines():
        s = linha.strip(" \t")
        if s and not s.startswith("//"):
            linhas_compactas.append(s)
    js_compacto = "\n".join(linhas_compactas)
    if re.search(r"</script", js_compacto, re.I):
        raise ValueError("Sequencia `</script` proibida detectada dentro do corpo JS.")
    return js_compacto


def validar_bundle(bundle: str) -> dict[str, int]:
    """Executa validacao rigorosa Elementor/seguranca/CSS/HTML/JS no artefato final."""
    if "\r" in bundle:
        raise AssertionError("Caracter CR (`\\r`) detectado; esperado LF puro.")
    if "\n\n" in bundle:
        raise AssertionError("Linha em branco (`\\n\\n`) detectada no bundle Elementor.")
    if not bundle.endswith("\n"):
        raise AssertionError("Bundle final deve terminar com quebra de linha LF.")

    limpo = bundle.rstrip("\n")
    if not limpo.startswith('<section id="leme-painel-ept"') or not limpo.endswith("</section>"):
        raise AssertionError("Bundle Elementor deve iniciar com `<section id=\"leme-painel-ept\"` e terminar com `</section>`.")

    sm = re.search(r"<style>(.*?)</style>", bundle, re.S)
    jm = re.search(r"<script>(.*?)</script>", bundle, re.S)
    if not sm or not jm:
        raise AssertionError("Tags `<style>` ou `<script>` ausentes no bundle.")

    css = sm.group(1)
    js = jm.group(1)
    html_sem_blocos = (
        bundle[: sm.start()]
        + "<style></style>"
        + bundle[sm.end() : jm.start()]
        + "<script></script>"
        + bundle[jm.end() :]
    )

    for proibido in ("<!doctype", "<html", "<head", "<body"):
        if proibido in html_sem_blocos.lower():
            raise AssertionError(f"Wrapper HTML completo proibido no artefato Elementor: `{proibido}`.")

    if "backdrop-filter" in css:
        raise AssertionError("`backdrop-filter` nao e permitido no widget.")
    if "#leme-painel-ept :focus-visible" not in css:
        raise AssertionError("Seletor descendente `#leme-painel-ept :focus-visible` foi corrompido na compactacao.")
    if css.count("{") != css.count("}"):
        raise AssertionError(f"Chaves CSS desbalanceadas: {css.count('{')} vs {css.count('}')}.")

    unscoped: list[str] = []
    buf: list[str] = []
    quote = ""
    i = 0
    n_css = len(css)
    while i < n_css:
        ch = css[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < n_css:
                i += 1
                buf.append(css[i])
            elif ch == quote:
                quote = ""
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "{":
            hdr = " ".join("".join(buf).split()).strip()
            eh_keyframe = hdr and all(
                p.strip() in ("from", "to") or re.match(r"^\d+%$", p.strip()) for p in hdr.split(",")
            )
            if hdr and not hdr.startswith("@") and not eh_keyframe:
                for sel in hdr.split(","):
                    s = sel.strip()
                    if s and not s.startswith("#leme-painel-ept"):
                        unscoped.append(s)
            buf.clear()
        elif ch == "}":
            buf.clear()
        else:
            buf.append(ch)
        i += 1
    if unscoped:
        raise AssertionError(f"Seletores CSS fora de `#leme-painel-ept`: {unscoped}")

    non_style = bundle[: sm.start()] + bundle[sm.end() :]
    css_classes = set(re.findall(r"\.(leme-[a-zA-Z0-9_-]+)", css))
    unused_css = [c for c in sorted(css_classes) if c not in non_style]
    if unused_css:
        raise AssertionError(f"Classes CSS nao utilizadas: {unused_css}")

    state_classes = set(re.findall(r"\.(is-[a-zA-Z0-9_-]+)", css))
    unused_states = [c for c in sorted(state_classes) if c not in non_style]
    if unused_states:
        raise AssertionError(f"Classes de estado CSS nao utilizadas: {unused_states}")

    pilha: list[str] = []

    class _BalParser(html.parser.HTMLParser):
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag not in VOID_HTML_TAGS:
                pilha.append(tag)

        def handle_endtag(self, tag: str) -> None:
            if tag in VOID_HTML_TAGS:
                return
            if not pilha or pilha[-1] != tag:
                esperado = pilha[-1] if pilha else "vazia"
                raise AssertionError(f"Desequilibrio HTML: esperado `</{esperado}>`, encontrado `</{tag}>`.")
            pilha.pop()

    _BalParser().feed(html_sem_blocos)
    if pilha:
        raise AssertionError(f"Tags HTML nao fechadas: {pilha}")

    for tok in (r'"\u0026amp;"', r'"\u0026lt;"', r'"\u0026gt;"', r'"\u0026quot;"', r'"\u0026#39;"'):
        if tok not in js:
            raise AssertionError(f"Escape Unicode ausente em `HTML_ESCAPE_MAP`: {tok}")
    if "csvEscape" not in js or "sanitizarUrl" not in js:
        raise AssertionError("Helpers de seguranca (`csvEscape` / `sanitizarUrl`) ausentes.")
    if re.search(r"</script", js, re.I):
        raise AssertionError("`</script` detectado dentro do `<script>`.")

    return {
        "css_chaves": css.count("{"),
        "classes_leme": len(css_classes),
        "classes_estado": len(state_classes),
        "linhas_js": len(js.splitlines()),
    }


def gerar_bundle(
    root: Optional[Path] = None,
    *,
    usar_template: bool = False,
    frontend_cfg: Optional[dict[str, str]] = None,
) -> tuple[str, dict[str, int]]:
    """Lê os 3 fontes em `root` (ou renderiza do template), gera e valida o bundle Elementor-safe."""
    base_dir = (root or Path.cwd()).resolve()
    index_html = base_dir / "index.html"
    styles_css = base_dir / "frontend" / "styles.css"
    app_js = base_dir / "frontend" / "app.js"

    fontes_locais_existem = index_html.exists() and styles_css.exists() and app_js.exists()
    if usar_template or not fontes_locais_existem:
        cfg = frontend_cfg if frontend_cfg is not None else carregar_config_frontend(root=base_dir)
        html_doc = renderizar_index_template(cfg)
        css_src = (styles_css if styles_css.exists() else _resolver_asset_template("styles.css")).read_text(encoding="utf-8")
        js_src = (app_js if app_js.exists() else _resolver_asset_template("app.js")).read_text(encoding="utf-8")
    else:
        html_doc = index_html.read_text(encoding="utf-8")
        css_src = styles_css.read_text(encoding="utf-8")
        js_src = app_js.read_text(encoding="utf-8")

    abertura_sec, miolo_html = extrair_secao_raiz(html_doc)
    abertura_min, miolo_min = compactar_html(abertura_sec, miolo_html)
    css_min = compactar_css(css_src)
    js_min = compactar_js_seguro(js_src)

    bundle = f"{abertura_min}\n<style>{css_min}</style>{miolo_min}\n<script>{js_min}</script>\n</section>\n"
    metricas = validar_bundle(bundle)
    return bundle, metricas


def gerar_site_completo(
    root: Path,
    *,
    frontend_cfg: dict[str, str],
    emitir_preview: bool = False,
    emitir_loader: bool = True,
    output_dir: Path = Path(DEFAULT_OUTPUT_DIRNAME),
) -> dict[str, Path]:
    """Gera `public/widget-elementor.html` e opcionalmente `public/loader-elementor.html` e preview (`index.html` + `frontend/`)."""
    base_dir = root.resolve()
    pasta_saida = output_dir if output_dir.is_absolute() else (base_dir / output_dir)
    gerados: dict[str, Path] = {}

    if emitir_preview:
        index_destino = base_dir / "index.html"
        frontend_dir = base_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        index_destino.write_text(renderizar_index_template(frontend_cfg), encoding="utf-8")
        gerados["index"] = index_destino

        for asset_nome in ("styles.css", "app.js"):
            origem = _resolver_asset_template(asset_nome)
            destino = frontend_dir / asset_nome
            if origem.resolve() != destino.resolve():
                shutil.copy2(origem, destino)
            gerados[asset_nome] = destino

    bundle, _ = gerar_bundle(
        root=base_dir,
        usar_template=True,
        frontend_cfg=frontend_cfg,
    )
    out_widget = pasta_saida / "widget-elementor.html"
    out_widget.parent.mkdir(parents=True, exist_ok=True)
    out_widget.write_bytes(bundle.encode("utf-8"))
    gerados["widget"] = out_widget

    if emitir_loader and frontend_cfg.get("widget_url", "").strip():
        out_loader = pasta_saida / "loader-elementor.html"
        out_loader.write_text(renderizar_loader_template(frontend_cfg), encoding="utf-8")
        gerados["loader"] = out_loader

    return gerados


def _rotulo_caminho(caminho: Path, root: Path) -> str:
    try:
        return str(caminho.relative_to(root))
    except ValueError:
        return str(caminho)


def main(
    argv: Optional[Sequence[str]] = None,
    default_root: Optional[Path] = None,
) -> int:
    parser = argparse.ArgumentParser(description="Compila e valida `public/widget-elementor.html` a partir dos fontes ou templates.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Valida os fontes e falha se `public/widget-elementor.html` estiver desatualizado.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root or Path.cwd(),
        help="Diretório raiz contendo index.html, frontend/ e public/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIRNAME),
        help="Diretório de saída relativo a --root (ou absoluto) para widget e loader (padrão: public).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Arquivo de configuração TOML da instância (padrão: <root>/lemeept.toml se existir).",
    )
    parser.add_argument(
        "--from-template",
        action="store_true",
        default=False,
        help="Gera o bundle a partir do template embutido + `[frontend]` mesmo quando index.html local existir.",
    )
    parser.add_argument(
        "--emit-site",
        action="store_true",
        default=False,
        help="Emite também `index.html`, `frontend/{styles.css,app.js}` e `public/loader-elementor.html` no diretório raiz.",
    )
    parser.add_argument(
        "--emit-loader",
        action="store_true",
        default=False,
        help="Emite ou valida também `public/loader-elementor.html` quando `widget_url` estiver definido.",
    )
    parser.add_argument("--titulo", default=None, help="Override para o título principal (<h2>).")
    parser.add_argument("--subtitulo", default=None, help="Override para o subtítulo do cabeçalho.")
    parser.add_argument("--eyebrow", default=None, help="Override para o rótulo superior (eyebrow).")
    parser.add_argument("--titulo-graficos", default=None, help="Override para o título da seção de gráficos.")
    parser.add_argument("--json-url", default=None, help="Override para `data-json-url` em produção.")
    parser.add_argument("--json-url-local", default=None, help="Override para `data-json-url-local`.")
    parser.add_argument("--widget-url", default=None, help="Override para `data-widget-url` do loader Elementor.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    pasta_saida = args.output_dir if args.output_dir.is_absolute() else (root / args.output_dir)
    overrides = {
        "titulo": args.titulo,
        "subtitulo": args.subtitulo,
        "eyebrow": args.eyebrow,
        "titulo_graficos": args.titulo_graficos,
        "json_url": args.json_url,
        "json_url_local": args.json_url_local,
        "widget_url": args.widget_url,
    }
    tem_override = any(v is not None for v in overrides.values())
    usar_template = args.from_template or args.emit_site or tem_override

    frontend_cfg = carregar_config_frontend(args.config, root=root, overrides=overrides)

    index_html = root / "index.html"
    styles_css = root / "frontend" / "styles.css"
    app_js = root / "frontend" / "app.js"
    out_widget = pasta_saida / "widget-elementor.html"
    out_loader = pasta_saida / "loader-elementor.html"

    bundle, metricas = gerar_bundle(
        root=root,
        usar_template=usar_template,
        frontend_cfg=frontend_cfg,
    )
    bundle_bytes = bundle.encode("utf-8")

    if args.check:
        if not out_widget.exists():
            print(f"[ERRO] Artefato ausente: {out_widget}", file=sys.stderr)
            return 1
        atual = out_widget.read_bytes()
        if atual != bundle_bytes:
            print(
                f"[ERRO] {out_widget.name} esta desatualizado em relacao a index.html / frontend/*. "
                "Execute `python3 scripts/build_frontend.py`.",
                file=sys.stderr,
            )
            return 1
        if args.emit_loader and frontend_cfg.get("widget_url", "").strip():
            if not out_loader.exists() or out_loader.read_text(encoding="utf-8") != renderizar_loader_template(frontend_cfg):
                print(f"[ERRO] {out_loader.name} esta ausente ou desatualizado.", file=sys.stderr)
                return 1
        print(f"[OK] {_rotulo_caminho(out_widget, root)} atualizado e validado ({len(bundle_bytes) / 1024:.1f} KB, {len(bundle.splitlines())} linhas).")
        return 0

    if args.emit_site:
        gerados = gerar_site_completo(
            root,
            frontend_cfg=frontend_cfg,
            emitir_preview=True,
            emitir_loader=True,
            output_dir=pasta_saida,
        )
        print(f"Site completo gerado em {root}: {', '.join(_rotulo_caminho(p, root) for p in gerados.values())}")
    else:
        out_widget.parent.mkdir(parents=True, exist_ok=True)
        out_widget.write_bytes(bundle_bytes)
        if args.emit_loader and frontend_cfg.get("widget_url", "").strip():
            out_loader.write_text(renderizar_loader_template(frontend_cfg), encoding="utf-8")

    css_path = styles_css if styles_css.exists() else _resolver_asset_template("styles.css")
    js_path = app_js if app_js.exists() else _resolver_asset_template("app.js")
    idx_txt = index_html.read_text(encoding="utf-8") if index_html.exists() else renderizar_index_template(frontend_cfg)
    fontes_bytes = len(idx_txt.encode("utf-8")) + css_path.stat().st_size + js_path.stat().st_size
    fontes_linhas = len(idx_txt.splitlines()) + len(css_path.read_text(encoding="utf-8").splitlines()) + len(js_path.read_text(encoding="utf-8").splitlines())
    gzip_kb = len(gzip.compress(bundle_bytes)) / 1024

    print(
        f"Fontes (HTML + CSS + JS): {fontes_linhas} linhas | {fontes_bytes / 1024:.1f} KB bruto\n"
        f"Bundle ({_rotulo_caminho(out_widget, root)}): {len(bundle.splitlines())} linhas | "
        f"{len(bundle_bytes) / 1024:.1f} KB bruto | {gzip_kb:.1f} KB gzip\n"
        f"Validacao Elementor OK: css_chaves={metricas['css_chaves']}, "
        f"classes_leme={metricas['classes_leme']}, classes_estado={metricas['classes_estado']}, "
        f"linhas_js={metricas['linhas_js']}, escopo=100%, zero linhas em branco"
    )
    return 0
