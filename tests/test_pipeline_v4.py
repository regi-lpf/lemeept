import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai import RateLimitError
from pydantic import BaseModel

from pipeline.llm_provider import (
    PROJECT_ROOT,
    LLMClient,
    _limpar_schema_gemini,
    _resolver_refs_schema,
)
from pipeline.models_v4 import (
    BaseEpistemologicaLLM,
    ContratoDefesaV4,
    ContratoExtracaoDeterministicaV4,
    DissertacaoDeterministica,
    EvidenciaCurtaLLM,
    EvidenciasEduCAPES,
    MetadadosResolvidos,
    PainelEptV4Output,
    RecortesTextuais,
    RespostaInterpretativaLLM,
)
from pipeline.normalizers import (
    formatar_nome_proprio,
    limpar_nome_pessoa,
    limpar_palavras_chave,
    limpar_prefixo_orientador,
    limpar_resumo_publico,
    normalizar_base_epistemologica,
    normalizar_chave_busca,
    normalizar_espacos,
    normalizar_nivel_aplicacao,
    normalizar_nome_orientador,
    normalizar_texto_busca,
    remover_acentos,
)
from pipeline.step1_collect import (
    carregar_mapeamento_ids_existentes,
    extrair_defesas_do_html,
    formatar_nome_proprio,
    limpar_prefixo_orientador,
)
from pipeline.step2_deterministic import (
    classificar_produto_com_fonte,
    coletar_evidencias_educapes,
    detectar_macroprojeto_e_linha,
    extrair_autores_referencias,
    extrair_coorientador,
    extrair_palavras_chave_resumo,
    isolar_secoes_pdf,
)
from pipeline.step3_llm_extract import (
    construir_indice_busca,
    montar_prompt_enxuto,
    montar_registro_final,
    processar_payload,
    ressincronizar_registros_deterministico,
)
from pipeline.step4_compile import aplicar_curadoria_csv, compilar_pipeline_v4


def _make_sample_payload(
    cod: str = "EPT-0901",
    mp: str = "MP1",
    lp: str = "LP1",
    titulo_produto_bruto: str = "Sequência Didática: Ensino Integrado",
    tipo_produto_regex: str = "material_didatico_instrucional",
    fonte_tipo_regex: str = "dissertacao_ficha",
    resumo: str = "[PÁG. 10]\nRESUMO\nTexto do resumo.\nPalavras-chave: EPT; Currículo.",
    autores_ref=None,
) -> ContratoExtracaoDeterministicaV4:
    return ContratoExtracaoDeterministicaV4(
        id=cod,
        metadados_resolvidos=MetadadosResolvidos(
            ano=2025,
            autor="Maria da Silva",
            orientador="João Souza",
            coorientadores=[],
            linha_pesquisa=lp,
            macroprojeto=mp,
        ),
        dissertacao_deterministica=DissertacaoDeterministica(
            titulo="Pesquisa sobre EPT",
            link="https://example.org/dissertacao.pdf",
            palavras_chave=["EPT", "Currículo"],
            autores_referenciados=autores_ref if autores_ref is not None else ["Frigotto", "Saviani"],
        ),
        evidencias_educapes=EvidenciasEduCAPES(
            handle_url="https://educapes.capes.gov.br/handle/capes/999999",
            titulo_produto="Título EduCAPES Limpo",
            titulo_produto_bruto=titulo_produto_bruto,
            data_publicacao="2025-05-01",
            colecao_educapes="ProfEPT",
            dc_type_educapes=["texto"],
            palavras_chave_educapes=["Educação Profissional"],
            tipo_produto_regex=tipo_produto_regex,
            fonte_tipo_regex=fonte_tipo_regex,
        ),
        recortes_textuais=RecortesTextuais(
            resumo=resumo,
            introducao="[PÁG. 15]\nIntrodução com trabalho como princípio educativo.",
        ),
    )


class TestStep1Collect(unittest.TestCase):
    def test_formatacao_e_prefixo_orientador(self):
        self.assertEqual(formatar_nome_proprio("MARIA DA SILVA E SOUZA"), "Maria da Silva e Souza")
        self.assertEqual(
            limpar_prefixo_orientador("Orientadora: Profª. Drª. ANA PAULA DE LIMA"),
            "Ana Paula de Lima",
        )

    def test_parser_html_ul_quebrada_e_fallback_ano_url(self):
        html = """
        <div>
          <li>Acadêmico: JOÃO DA SILVA</li>
          <li>Orientador: Prof. Dr. CARLOS MENDES</li>
          <li>Dissertação: <a href="https://profept.ifc.edu.br/wp-content/uploads/sites/54/2023/08/diss.pdf">Título da Dissertação</a></li>
          <li>Produto Educacional: <a href="https://educapes.capes.gov.br/handle/capes/12345">Podcast – Vozes da EPT</a></li>
        </div>
        <h3>DEFESAS 2024</h3>
        <ul>
          <li>Discente: ANA PEREIRA</li>
          <li>Orientadora: BEATRIZ COSTA</li>
          <li>Trabalho intitulado <a href="https://profept.ifc.edu.br/wp-content/uploads/2024/01/ana.pdf">Título 2</a></li>
          <li>Produto: <a href="https://educapes.capes.gov.br/handle/capes/67890">Cartilha – Guia EPT</a></li>
        </ul>
        """
        fontes = extrair_defesas_do_html(html)
        self.assertEqual(len(fontes), 2)
        self.assertEqual(fontes[0].ano, 2023)
        self.assertEqual(fontes[0].autor_bruto, "João da Silva")
        self.assertEqual(fontes[0].orientador_bruto, "Carlos Mendes")
        self.assertEqual(fontes[0].titulo_produto_bruto, "Podcast – Vozes da EPT")
        self.assertEqual(fontes[0].handle_educapes, "https://educapes.capes.gov.br/handle/capes/12345")
        self.assertEqual(fontes[1].ano, 2024)
        self.assertEqual(fontes[1].campus, "IFC Blumenau")

    def test_carregar_mapeamento_ids_multiplos_arquivos_prioridade(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "manifest.json"
            p2 = Path(tmp) / "v3.json"
            p1.write_text(
                json.dumps(
                    {
                        "registros": [
                            {
                                "id": "EPT-0111",
                                "fonte_profept": {
                                    "autor_bruto": "Autor Novo",
                                    "url_dissertacao": "https://ex.org/111.pdf",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            p2.write_text(
                json.dumps(
                    {
                        "defesas": [
                            {
                                "cod": "EPT-0001",
                                "autor": {"nome": "Autor Novo"},
                                "dissertacao": {"link": "https://ex.org/old.pdf"},
                            },
                            {
                                "cod": "EPT-0002",
                                "autor": {"nome": "Autor Antigo"},
                                "dissertacao": {"link": "https://ex.org/2.pdf"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            mapa, max_num = carregar_mapeamento_ids_existentes([p1, p2])
            self.assertEqual(max_num, 111)
            # Primeiro arquivo na lista de prioridade vence em colisão de autor
            self.assertEqual(mapa["autor novo"], "EPT-0111")
            self.assertEqual(mapa["https://ex.org/111.pdf"], "EPT-0111")
            self.assertEqual(mapa["https://ex.org/2.pdf"], "EPT-0002")


class TestStep2Deterministic(unittest.TestCase):
    def test_detectar_macroprojeto_e_linha(self):
        self.assertEqual(detectar_macroprojeto_e_linha("Macroprojeto IV: História"), ("MP4", "LP2"))
        self.assertEqual(
            detectar_macroprojeto_e_linha("O vídeo foi gravado em formato mp4 de 15 MB."),
            ("MP_INDEFINIDO", "LP_INDEFINIDA"),
        )
        self.assertEqual(
            detectar_macroprojeto_e_linha("MP4 – um padrão de áudio e vídeo"),
            ("MP_INDEFINIDO", "LP_INDEFINIDA"),
        )
        self.assertEqual(
            detectar_macroprojeto_e_linha("Arquivo salvo em aula.mp4 para download."),
            ("MP_INDEFINIDO", "LP_INDEFINIDA"),
        )
        self.assertEqual(
            detectar_macroprojeto_e_linha("Vinculado ao MP4 de história"),
            ("MP4", "LP2"),
        )
        self.assertEqual(
            detectar_macroprojeto_e_linha("OrganizacaoDeEspacosPedagogicos no IFC"),
            ("MP6", "LP2"),
        )
        self.assertEqual(
            detectar_macroprojeto_e_linha("Vinculado à linha Práticas Educativas em EPT."),
            ("MP_INDEFINIDO", "LP1"),
        )

    def test_isolar_secoes_pdf_vazio_retorna_tupla(self):
        recortes, refs = isolar_secoes_pdf([])
        self.assertIsInstance(recortes, RecortesTextuais)
        self.assertEqual(refs, "")

    def test_isolar_secoes_pdf_limpeza_resumo_multipage_e_referencias(self):
        paginas = [
            (1, "Capa IFC Blumenau"),
            (2, "Folha de rosto"),
            (3, "Ficha Catalográfica CDD 370"),
            (4, "RESUMO\u200b\x01\nTexto do resumo sem palavras chave."),
            (5, "Palavras Chave: Educação Profissional; Inclusão; Sequência Didática.\n\nABSTRACT\nEnglish abstract."),
            (6, "SUMÁRIO\n1 INTRODUÇÃO .... 10\n6 REFERÊNCIAS .... 40\n7 ANEXOS .... 50"),
            (7, "1. INTRODUÇÃO\n\nO trabalho como princípio educativo fundamenta esta análise crítica (SAVIANI, 2007)."),
            (8, "2. DESENVOLVIMENTO\n\nTexto com a palavra referências\nisolada em minúsculas no corpo."),
            (9, "Conclusão final.\n\n6. REFERÊNCIAS\nÁVILA, Maria. Educação. 2020.\nESPÍRITO SANTO, Ruy. Trabalho. 2019."),
        ]
        recortes, texto_refs = isolar_secoes_pdf(paginas)
        self.assertIn("Palavras Chave:", recortes.resumo)
        self.assertNotIn("English abstract", recortes.resumo)
        self.assertEqual(
            extrair_palavras_chave_resumo(recortes.resumo),
            ["Educação Profissional", "Inclusão", "Sequência Didática"],
        )
        self.assertIn("6. REFERÊNCIAS", texto_refs)
        self.assertNotIn("isolada em minúsculas", texto_refs)

    def test_extrair_palavras_chave_variantes(self):
        self.assertEqual(
            extrair_palavras_chave_resumo("Texto\nPalavras-chaves: Gênero. Sexualidade. EPT."),
            ["Gênero", "Sexualidade", "EPT"],
        )

    def test_extrair_coorientador_variantes_titulacao_e_falsos_positivos(self):
        texto_ept0004 = (
            "Orientadora: Profª. Drª. Fátima Peres Zago de\nOliveira.\n"
            "Co-orientadora: Profª. Drª. Raquel Cardoso\n"
            "de Faria e Custódio\n"
            "BLUMENAU - SC\n2025"
        )
        self.assertEqual(
            extrair_coorientador(texto_ept0004, orientador_principal="Fátima Peres Zago de Oliveira"),
            ["Raquel Cardoso de Faria e Custódio"],
        )

        texto_ept0033 = (
            "Orientadora: Profa. Dra. Viviane Grimm\n"
            "Coorientadora: Profa. Dra. Ivonete Telles Medeiros\n"
            "Plácido\n"
            "Blumenau\n2024\n"
            "Ponciano, Fabiano Mauricio; orientadora Viviane Grimm; "
            "coorientadora Ivonete Telles Medeiros Plácido. -- Blumenau, 2024."
        )
        self.assertEqual(
            extrair_coorientador(texto_ept0033, orientador_principal="Viviane Grimm"),
            ["Ivonete Telles Medeiros Plácido"],
        )

        texto_quebra_e_titulos = (
            "Coorientação:\nProf. Me. João Carlos da Silva (IFC)\n\n"
            "Coorientador: Profª. Ma. Esp. ANA MARIA DE SOUZA"
        )
        self.assertEqual(
            extrair_coorientador(texto_quebra_e_titulos),
            ["João Carlos da Silva", "Ana Maria de Souza"],
        )

        texto_dedup_orientador = (
            "Coorientadora: Profa. Dra. Fátima Peres Zago de Oliveira\n"
            "Co-orientador: Profa. Dra. Maria Clara\n"
            "Coorientadora: Profa. Dra. Maria Clara dos Santos"
        )
        self.assertEqual(
            extrair_coorientador(texto_dedup_orientador, orientador_principal="Fátima Peres Zago de Oliveira"),
            ["Maria Clara dos Santos"],
        )

        texto_falsos_positivos = (
            "desenvolver material didático orientado pela visualidade\n"
            "acabou se tornando o meu “coorientador” do mestrado\n"
            "Co-orientador: Não se aplica.\n"
            "tive dois orientadores: primeiramente, a Profa. Dra. Bernadete"
        )
        self.assertEqual(extrair_coorientador(texto_falsos_positivos), [])

    def test_extrair_autores_referencias_abnt(self):
        texto = """
        BRASIL. Ministério da Educação. Diretrizes. 2020.
        EDUCAÇÃO, Revista de. Editorial. 2021.
        DE SOUZA JUNIOR, João. Título. 2018.
        ÁVILA, Maria. Título. 2019.
        MÜLLER, Hans. Título. 2017.
        PEÑA, Carlos. Título. 2016.
        ESPÍRITO SANTO, Ruy. Título. 2022.
        SAVIANI, Dermeval. Pedagogia. 2007.
        """
        autores = extrair_autores_referencias(texto)
        self.assertEqual(
            autores,
            ["Espírito Santo", "Müller", "Peña", "Saviani", "Souza", "Ávila"],
        )

    def test_classificar_produto_com_fonte_alinhado(self):
        t1, f1 = classificar_produto_com_fonte("Podcast – Vozes da EPT", "", "", None, [])
        self.assertEqual((t1, f1), ("material_didatico_instrucional", "dissertacao_ficha"))

        t2, f2 = classificar_produto_com_fonte(
            "Uma Sequência Didática envolvendo o aplicativo Telegram", "", "", None, []
        )
        self.assertEqual((t2, f2), ("material_didatico_instrucional", "dissertacao_ficha"))

        t3, f3 = classificar_produto_com_fonte("Título genérico", "", "", None, ["aplicativo móvel"])
        self.assertEqual((t3, f3), ("software_aplicativo", "educapes_dc_type"))

        t4, f4 = classificar_produto_com_fonte("Título genérico", "", "", None, ["portal", "texto"])
        self.assertIsNone(t4)
        self.assertIsNone(f4)

    def test_coletar_evidencias_sem_handle_e_deduplicacao_educapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            # Sem handle: usa sentenca do resumo
            ev_sem = coletar_evidencias_educapes(
                handle_url=None,
                titulo_produto_bruto="Título Neutro",
                resumo_pdf="Como produto educacional foi elaborada uma cartilha digital.",
                descricao_produto_pdf="",
                cache_dir=cache_dir,
            )
            self.assertEqual(ev_sem.tipo_produto_regex, "material_didatico_instrucional")
            self.assertEqual(ev_sem.fonte_tipo_regex, "dissertacao_ficha")

            # Com cache HTML duplicando <meta> e <table>
            html_file = cache_dir / "capes_555.html"
            html_file.write_text(
                """
                <html><head>
                  <meta name="dc.title" content="Formação em Segurança no Trabalho" />
                  <meta name="dc.type" content="curso" />
                  <meta name="dc.creator" content="Silva, Ana" />
                  <meta name="dc.contributor" scheme="advisor" content="Costa, João" />
                </head><body>
                  <table>
                    <tr><td>dc.type</td><td>Curso</td></tr>
                    <tr><td>dc.contributor.advisor</td><td>Costa, João</td></tr>
                    <tr><td>dc.identifier.isbn</td><td>978-00-000</td></tr>
                    <tr><td>dc.identifier.isbn</td><td>978-00-000</td></tr>
                  </table>
                </body></html>
                """,
                encoding="utf-8",
            )
            ev_com = coletar_evidencias_educapes(
                handle_url="https://educapes.capes.gov.br/handle/capes/555",
                titulo_produto_bruto="Título Bruto ProfEPT",
                resumo_pdf="",
                descricao_produto_pdf="",
                cache_dir=cache_dir,
            )
            self.assertEqual(ev_com.dc_type_educapes, ["curso"])
            self.assertEqual(len(ev_com.autores_colaboradores), 2)
            self.assertEqual(len(ev_com.identificadores), 2)  # handle + 1 isbn deduplicado
            self.assertEqual(ev_com.fonte_tipo_regex, "educapes_dc_type")
            self.assertEqual(ev_com.titulo_produto_bruto, "Título Bruto ProfEPT")


class TestLLMProvider(unittest.TestCase):
    def test_project_root_env_e_sanitizacao_schemas(self):
        self.assertTrue((PROJECT_ROOT / "pipeline" / "llm_provider.py").exists())

        class Sub(BaseModel):
            a: str

        class Main(BaseModel):
            sub: Sub

        schema = Main.model_json_schema()
        limpo = _limpar_schema_gemini(schema)
        self.assertNotIn("$defs", limpo)
        self.assertNotIn("additionalProperties", str(limpo))

        estrito = _resolver_refs_schema(schema)
        self.assertNotIn("$defs", estrito)
        self.assertIs(estrito["additionalProperties"], False)
        self.assertIs(estrito["properties"]["sub"]["additionalProperties"], False)


    def test_rate_limit_nao_dorme_na_ultima_tentativa_e_ollama_extra_body(self):
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "ollama", "LLM_NUM_CTX": "8192", "LLM_THINK": "false"},
            clear=True,
        ):
            client = LLMClient()
            resp = SimpleNamespace(request=SimpleNamespace(), status_code=429, headers={})
            err = RateLimitError("rate limited", response=resp, body=None)
            client.openai_client.chat.completions.create = MagicMock(side_effect=err)

            with patch("pipeline.llm_provider.time.sleep") as mock_sleep:
                with self.assertRaises(RateLimitError):
                    client.gerar_estruturado("sys", "usr", RespostaInterpretativaLLM, max_retries=2)
                # Só dorme na tentativa 1; na tentativa 2 (última) levanta direto
                mock_sleep.assert_called_once_with(30)
                _, kwargs = client.openai_client.chat.completions.create.call_args
                self.assertEqual(kwargs["extra_body"], {"options": {"num_ctx": 8192}, "think": False})

class TestNormalizersAndStep3(unittest.TestCase):
    def test_normalizar_base_epistemologica(self):
        self.assertEqual(normalizar_base_epistemologica("pedagogia_historico_critica"), ("Pedagogia Histórico-Crítica", True))
        self.assertEqual(normalizar_base_epistemologica("MHD e Pedagogia Freireana"), ("Materialismo Histórico-Dialético e Educação Libertadora / Freireana", True))
        self.assertEqual(normalizar_base_epistemologica("teoria_criativa"), ("teoria_criativa", False))
        self.assertEqual(normalizar_base_epistemologica(None), (None, False))

    def test_normalizar_nivel_aplicacao_e_resumo(self):
        self.assertEqual(normalizar_nivel_aplicacao("educacional_academico"), "Educação Profissional e Tecnológica")
        self.assertEqual(normalizar_nivel_aplicacao("ensino_superior"), "Educação Superior")
        self.assertEqual(normalizar_nivel_aplicacao("Curso Técnico Integrado ao Ensino Médio"), "Ensino Médio Integrado")
        self.assertEqual(limpar_resumo_publico("[PÁG. 11]\nRESUMO \n\nConteúdo principal."), "Conteúdo principal.")
        self.assertEqual(normalizar_texto_busca("Educação Crítica!"), "educacao critica")
        self.assertEqual(limpar_palavras_chave([" ept ", "EPT", "a"]), ["Ept"])

    def test_normalizacao_texto_e_pessoas_e_aliases(self):
        self.assertEqual(remover_acentos("Educação Profissional e Tecnológica"), "Educacao Profissional e Tecnologica")
        self.assertEqual(normalizar_espacos("Linha\u200b 1\x01  \n\n\n\nLinha 2"), "Linha 1\n\nLinha 2")
        self.assertEqual(normalizar_chave_busca("  Fátima   Zago "), "fatima zago")
        self.assertEqual(formatar_nome_proprio("MARIA DA SILVA,"), "Maria da Silva")

        self.assertEqual(limpar_nome_pessoa("Profa. Dra. ANA MARIA DE SOUZA (IFC),"), "Ana Maria de Souza")
        self.assertEqual(limpar_nome_pessoa("Prof. Me. Esp. João Carlos:"), "João Carlos")
        self.assertEqual(limpar_nome_pessoa("Débora Magna Santos Costa de Souza,"), "Débora Magna Santos Costa de Souza")

        self.assertEqual(limpar_prefixo_orientador(": Viviane Grimm"), "Viviane Grimm")
        self.assertEqual(limpar_prefixo_orientador("Orientadora: Profª. Drª. ANA PAULA DE LIMA"), "Ana Paula de Lima")
        self.assertEqual(limpar_prefixo_orientador("Orientador: Inge R. F. Suhr"), "Inge Renate Frose Suhr")

        self.assertEqual(normalizar_nome_orientador("Fátima Perez Zago de Oliveira."), "Fátima Peres Zago de Oliveira")
        self.assertEqual(normalizar_nome_orientador("Inge R. F. Suhr"), "Inge Renate Frose Suhr")
        self.assertEqual(normalizar_nome_orientador("Eduardo Werneck Ribeiro"), "Eduardo Augusto Werneck Ribeiro")
        self.assertEqual(normalizar_nome_orientador("Leandro Marcos Alves Salgado"), "Leandro Marcos Salgado Alves")
        self.assertEqual(normalizar_nome_orientador("Sonia Regina de Souza Fernandes."), "Sônia Regina de Souza Fernandes")
        self.assertEqual(normalizar_nome_orientador("Carlos Eduardo Monteiro"), "Carlos Eduardo Monteiro")

    def test_prompt_enxuto_e_montar_registro_final_rejeita_nao_canonico(self):
        payload = _make_sample_payload(mp="MP_INDEFINIDO", lp="LP1")
        prompt = montar_prompt_enxuto(payload)
        self.assertIn('"linha_pesquisa_pre_detectada":"LP1"', prompt)

        resp_nao_canon = RespostaInterpretativaLLM(
            macroprojeto="MP1",
            produto_titulo="Título",
            produto_tipo="material_didatico_instrucional",
            produto_publico_alvo=["docentes_professores"],
            produto_nivel_aplicacao="educacional_academico",
            base_epistemologica=BaseEpistemologicaLLM(
                valor="teoria_criativa",
                candidato=None,
                confianca="alta",
                justificativa="Justificativa curta.",
                evidencias=[EvidenciaCurtaLLM(secao="Introdução", pagina=15, trecho_curto="Trecho citado.")],
            ),
        )
        reg = montar_registro_final(payload, resp_nao_canon)
        self.assertIsNone(reg.dissertacao.base_epistemologica.valor)
        self.assertEqual(reg.dissertacao.base_epistemologica.candidato, "teoria_criativa")
        self.assertTrue(reg.dissertacao.base_epistemologica.revisao_pendente)
        self.assertEqual(reg.dissertacao.base_epistemologica.confianca, "media")
        self.assertEqual(reg.produto.nivel_aplicacao, "Educação Profissional e Tecnológica")
        self.assertEqual(reg.dissertacao.resumo, "Texto do resumo.\nPalavras-chave: EPT; Currículo.")
        self.assertEqual(reg.produto.proveniencia.rotulo_original_declarado, "Sequência Didática: Ensino Integrado")

        resp_canon = RespostaInterpretativaLLM(
            macroprojeto="MP1",
            produto_titulo="Título",
            produto_tipo="material_didatico_instrucional",
            produto_publico_alvo=["docentes_professores"],
            produto_nivel_aplicacao="Ensino Médio Integrado",
            base_epistemologica=BaseEpistemologicaLLM(
                valor="pedagogia_historico_critica",
                candidato=None,
                confianca="alta",
                justificativa="Fundamentado em Saviani.",
                evidencias=[EvidenciaCurtaLLM(secao="Introdução", pagina=15, trecho_curto="Prática social e catarse.")],
            ),
        )
        reg_ok = montar_registro_final(payload, resp_canon)
        self.assertEqual(reg_ok.dissertacao.base_epistemologica.valor, "Pedagogia Histórico-Crítica")
        self.assertFalse(reg_ok.dissertacao.base_epistemologica.revisao_pendente)
        self.assertIn("pedagogia historico critica", reg_ok.indice_busca.texto_busca_normalizado)

    def test_protecao_curado_humano_e_ressincronizacao(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            s2_dir = tmp_path / "stage2"
            rec_dir = tmp_path / "records"
            s2_dir.mkdir()
            rec_dir.mkdir()

            payload_s2 = _make_sample_payload(autores_ref=["Ciavatta", "Frigotto", "Saviani"])
            s2_file = s2_dir / "EPT-0901.json"
            s2_file.write_text(payload_s2.model_dump_json(indent=2), encoding="utf-8")

            # Cria registro inicial com autores desatualizados, resumo sujo e curado_humano=True
            rec_inicial = ContratoDefesaV4.model_validate(
                {
                    "schema_version": "4.0",
                    "id": "EPT-0901",
                    "ano": 2025,
                    "autor": "Maria da Silva",
                    "orientador": "João Souza",
                    "coorientadores": [],
                    "instituicao": "Instituto Federal Catarinense (IFC)",
                    "campus": "IFC Blumenau",
                    "linha_pesquisa": "LP1",
                    "macroprojeto": "MP1",
                    "dissertacao": {
                        "titulo": "Pesquisa sobre EPT",
                        "link": "https://example.org/dissertacao.pdf",
                        "resumo": "[PÁG. 10]\nRESUMO\nAntigo.",
                        "palavras_chave": [],
                        "autores_referenciados": [],
                        "base_epistemologica": {
                            "valor": "Educação Libertadora / Freireana",
                            "candidato": None,
                            "confianca": "alta",
                            "revisao_pendente": False,
                            "curado_humano": True,
                            "justificativa": "Aprovado pelo curador.",
                            "evidencias": [],
                        },
                    },
                    "produto": {
                        "titulo": "Antigo",
                        "tipo": "software_aplicativo",
                        "link": "https://educapes.capes.gov.br/handle/capes/999999",
                        "publico_alvo": ["docentes_professores"],
                        "nivel_aplicacao": "educacional_academico",
                        "palavras_chave": [],
                        "data_publicacao": None,
                        "autores_colaboradores": [],
                        "identificadores": [],
                        "proveniencia": {
                            "fonte_tipo_escolhida": "inferencia_llm",
                            "rotulo_original_declarado": None,
                            "colecao_educapes": None,
                            "dc_type_educapes": [],
                        },
                    },
                    "indice_busca": construir_indice_busca({"id": "EPT-0901"}),
                }
            )
            rec_file = rec_dir / "EPT-0901.json"
            rec_file.write_text(rec_inicial.model_dump_json(indent=2), encoding="utf-8")

            # processar_payload com sobrescrever=True protege curado_humano=True
            mock_llm = MagicMock()
            res = processar_payload(
                s2_file, "sys", mock_llm, sobrescrever=True, forcar_curados=False, records_dir=rec_dir
            )
            self.assertIsNone(res)
            mock_llm.gerar_estruturado.assert_not_called()

            # ressincronizar atualiza campos determinísticos mantendo base curada
            stats = ressincronizar_registros_deterministico(stage2_dir=s2_dir, records_dir=rec_dir)
            self.assertEqual(stats["sincronizados"], 1)
            atualizado = ContratoDefesaV4.model_validate_json(rec_file.read_text(encoding="utf-8"))
            self.assertEqual(atualizado.dissertacao.autores_referenciados, ["Ciavatta", "Frigotto", "Saviani"])
            self.assertEqual(atualizado.dissertacao.resumo, "Texto do resumo.\nPalavras-chave: EPT; Currículo.")
            self.assertEqual(atualizado.dissertacao.base_epistemologica.valor, "Educação Libertadora / Freireana")
            self.assertTrue(atualizado.dissertacao.base_epistemologica.curado_humano)
            self.assertEqual(atualizado.produto.tipo, "material_didatico_instrucional")
            self.assertEqual(atualizado.produto.nivel_aplicacao, "Educação Profissional e Tecnológica")
            self.assertIn("educacao libertadora freireana", atualizado.indice_busca.texto_busca_normalizado)


class TestStep4Compile(unittest.TestCase):
    def test_curadoria_csv_e_compilacao_remove_csv_quando_zera(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rec_dir = tmp_path / "records"
            dist_dir = tmp_path / "dist"
            rec_dir.mkdir()
            dist_dir.mkdir()

            payload = _make_sample_payload(cod="EPT-0902")
            resp_pend = RespostaInterpretativaLLM(
                macroprojeto="MP1",
                produto_titulo="Produto Teste",
                produto_tipo="material_didatico_instrucional",
                produto_publico_alvo=["estudantes_alunos"],
                produto_nivel_aplicacao="Ensino Médio Integrado",
                base_epistemologica=BaseEpistemologicaLLM(
                    valor=None,
                    candidato="pedagogia_historico_critica",
                    confianca="media",
                    justificativa="Indícios de Saviani.",
                    evidencias=[EvidenciaCurtaLLM(secao="Introdução", pagina=12, trecho_curto="Prática social.")],
                ),
            )
            reg = montar_registro_final(payload, resp_pend)
            (rec_dir / "EPT-0902.json").write_text(reg.model_dump_json(indent=2), encoding="utf-8")

            # Primeira compilação gera CSV com 1 pendente
            saida1 = compilar_pipeline_v4(records_dir=rec_dir, dist_dir=dist_dir)
            self.assertIsInstance(saida1, PainelEptV4Output)
            self.assertEqual(saida1.total_defesas, 1)
            self.assertEqual(saida1.total_producoes, 2)
            csv_path = dist_dir / "revisao_epistemologica_pendente.csv"
            self.assertTrue(csv_path.exists())

            # Edita CSV preenchendo base_epistemologica_aprovada (testa inferência de APROVADO)
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            rows[0]["base_epistemologica_aprovada"] = "pedagogia_historico_critica"
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
                writer.writeheader()
                writer.writerows(rows)

            atualizados = aplicar_curadoria_csv(records_dir=rec_dir, relatorio_revisao=csv_path)
            self.assertEqual(atualizados, 1)

            # Segunda compilação zera pendências e remove CSV
            saida2 = compilar_pipeline_v4(records_dir=rec_dir, dist_dir=dist_dir)
            self.assertFalse(csv_path.exists())
            rec_final = saida2.defesas[0]
            self.assertEqual(rec_final.dissertacao.base_epistemologica.valor, "Pedagogia Histórico-Crítica")
            self.assertTrue(rec_final.dissertacao.base_epistemologica.curado_humano)
            self.assertFalse(rec_final.dissertacao.base_epistemologica.revisao_pendente)
            self.assertIn("pedagogia historico critica", rec_final.indice_busca.texto_busca_normalizado)


if __name__ == "__main__":
    unittest.main()
