import csv
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai import RateLimitError
from pydantic import BaseModel

from lemeept_extractor.llm_provider import (
    PROJECT_ROOT,
    LLMClient,
    _limpar_schema_gemini,
    _resolver_refs_schema,
)
from lemeept_extractor.models import (
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
from lemeept_extractor.normalizers import (
    formatar_nome_proprio,
    limpar_nome_pessoa,
    limpar_palavras_chave,
    limpar_prefixo_orientador,
    limpar_resumo_publico,
    normalizar_base_epistemologica,
    normalizar_chave_busca,
    normalizar_espacos,
    normalizar_formato_produto,
    normalizar_nivel_aplicacao,
    normalizar_nome_orientador,
    normalizar_texto_busca,
    remover_acentos,
)
from lemeept_extractor.references import (
    extrair_autores_referencias as extrair_autores_ref_direto,
    normalizar_autor_referencia,
    reconciliar_autores_referenciados,
)
from lemeept_extractor.stages.extract import (
    classificar_formato_produto_com_fonte,
    classificar_produto_com_fonte,
    coletar_evidencias_educapes,
    detectar_macroprojeto_e_linha,
    extrair_autores_referencias,
    extrair_coorientador,
    extrair_palavras_chave_resumo,
    isolar_secoes_pdf,
)
from lemeept_extractor.stages.llm import (
    SKILL_PATH,
    construir_indice_busca,
    montar_prompt_enxuto,
    montar_registro_final,
    processar_payload,
    ressincronizar_registros_deterministico,
)
from lemeept_extractor.stages.compile import aplicar_curadoria_csv, compilar_pipeline_v4

from collectors.ifc_blumenau import (
    carregar_mapeamento_ids_existentes,
    extrair_defesas_do_html,
)


def _make_sample_payload(
    cod: str = "EPT-0901",
    mp: str = "MP1",
    lp: str = "LP1",
    titulo_produto_bruto: str = "Sequência Didática: Ensino Integrado",
    tipo_produto_regex: str = "material_didatico_instrucional",
    fonte_tipo_regex: str = "dissertacao_ficha",
    formato_produto_regex: str = "Sequência Didática",
    fonte_formato_regex: str = "dissertacao_ficha",
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
            formato_produto_regex=formato_produto_regex,
            fonte_formato_regex=fonte_formato_regex,
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

    def test_isolar_secoes_pdf_corta_apendices_e_aceita_multiplas_secoes_refs(self):
        paginas = [
            (1, "Capa IFC Blumenau"),
            (2, "Folha de rosto"),
            (3, "RESUMO\nResumo do estudo."),
            (4, "SUMÁRIO\n1 INTRODUÇÃO .... 5\n5 REFERÊNCIAS .... 8"),
            (5, "REFERÊNCIAS\nAPÊNDICE A\nANEXO B\n10"),  # continuação de sumário sem pontilhado
            (6, "1. INTRODUÇÃO\nTexto introdutório da pesquisa."),
            (7, "2. DESENVOLVIMENTO\nCorpo do artigo 1."),
            (8, "REFERÊNCIAS\nSAVIANI, Dermeval. Pedagogia. São Paulo: Autores Associados, 2007."),
            (9, "GUIA DIDÁTICO DO PRODUTO\nTexto corrido do produto educacional sem referências bibliográficas ao longo de toda a página para testar o corte automático por mudança de seção."),
            (10, "3. ARTIGO 2\nREFERÊNCIAS\nKAPLÚN,\nGabriel. Materiales educativos. Montevideo, 2003."),
            (11, "APÊNDICE A – QUESTIONÁRIO\nQUESTIONÁRIO APLICADO, Questionário 1. 2024.\nTERMO DE AUTORIZAÇÃO, Consentimento livre. 2024."),
        ]
        _, texto_refs = isolar_secoes_pdf(paginas)
        self.assertIn("SAVIANI, Dermeval", texto_refs)
        self.assertIn("KAPLÚN,", texto_refs)
        self.assertNotIn("GUIA DIDÁTICO DO PRODUTO", texto_refs)
        self.assertNotIn("QUESTIONÁRIO APLICADO", texto_refs)
        self.assertNotIn("TERMO DE AUTORIZAÇÃO", texto_refs)
        autores = extrair_autores_referencias(texto_refs)
        self.assertEqual(autores, ["Dermeval Saviani", "Gabriel Kaplún"])

    def test_extrair_palavras_chave_variantes(self):
        self.assertEqual(
            extrair_palavras_chave_resumo("Texto\nPalavras-chaves: Gênero. Sexualidade. EPT."),
            ["Gênero", "Sexualidade", "EPT"],
        )

    def test_extrair_coorientador_variantes_titulacao_e_falsos_positivos(self):
        from lemeept_extractor.config import usar_config

        with usar_config(Path(__file__).resolve().parent.parent / "lemeept.toml"):
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
        from lemeept_extractor.config import usar_config

        texto = """
        BRASIL. Ministério da Educação. Diretrizes. 2020.
        EDUCAÇÃO, Revista de. Editorial. 2021.
        INSTITUTO FEDERAL CATARINENSE. Plano de Desenvolvimento. 2022.
        FATORES EXPLICATIVOS, Dados Gerais do Formulário. 2024.
        QUESTIONÁRIO APLICADO, Respostas de Estudantes. 2023.
        TERMO DE AUTORIZAÇÃO, Participação em Pesquisa. 2024.
        COMPONENTE CURRICULAR, Organização Escolar. 2022.
        GEÓGRAFOS, 7., 2014, Vitória. Anais [...]. 2014.
        MOODLE, nesse contexto, opera como ambiente virtual em 2023.
        BRIQUET DE LEMOS, Antonio A. Bibliotecas. Brasília, 1998.
        PLÁCIDO, Reginaldo Leandro Plácido. Políticas de EPT. 2020.
        DE SOUZA JUNIOR, João. Título da obra. 2018.
        ÁVILA, Maria. Título da obra. 2019.
        MÜLLER, Hans. Título da obra. 2017.
        PEÑA, Carlos. Título da obra. 2016.
        ESPÍRITO SANTO, Ruy. Título da obra. 2022.
        SAVIANI, Dermeval. Pedagogia histórico-crítica. 2007.
        FRIGOTTO, Gaudêncio; CIAVATTA, Maria; RAMOS, Marise Nogueira (Orgs.). Ensino Médio Integrado. 2005.
        LÜDKE, M. & ANDRÉ, Marli E. D. A. de. Pesquisa em educação. 1986.
        FREIRE, Paulo e SHOR, Ira. Medo e ousadia. 1986.
        ABRAMO, H.W. Espaços de juventude. In: FREITAS, M.V. de; PAPA, F. de C. (Org.). Juventude. 2008.
        KAPLÚN,
        Gabriel. Aprender y enseñar. 2003.
        """
        with usar_config(Path(__file__).resolve().parent.parent / "lemeept.toml"):
            autores = extrair_autores_referencias(texto)
        self.assertEqual(
            autores,
            [
                "Antonio A. Briquet de Lemos",
                "Carlos Peña",
                "Dermeval Saviani",
                "Gabriel Kaplún",
                "Gaudêncio Frigotto",
                "H. W. Abramo",
                "Hans Müller",
                "Ira Shor",
                "João de Souza Junior",
                "Maria Ávila",
                "Maria Ciavatta",
                "Marise Nogueira Ramos",
                "Marli André",
                "Menga Lüdke",
                "Paulo Freire",
                "Reginaldo Leandro Plácido",
                "Ruy Espírito Santo",
            ],
        )
        # In: organizadores não entram como autores principais e ruídos são descartados
        self.assertNotIn("M. V. de Freitas", autores)
        self.assertNotIn("F. de C. Papa", autores)

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

    def test_classificar_formato_produto_com_fonte(self):
        # Resumo ancorado prevalece sobre prefixo ruidoso ou título enganoso
        fmt1, src1 = classificar_formato_produto_com_fonte(
            resumo_pdf="Construímos um produto educacional em formato de e-book sobre ensino de línguas.",
            descricao_produto_pdf="",
            titulo_produto_bruto="Vídeos – GAMIFYING ENGLISH",
            titulo_capes=None,
            dc_types=["outro"],
        )
        self.assertEqual((fmt1, src1), ("E-book / Livro Digital", "dissertacao_ficha"))

        fmt2, src2 = classificar_formato_produto_com_fonte(
            resumo_pdf="Foi desenvolvido um Produto Educacional no formato de folder, intitulado: Um guia para estudantes.",
            descricao_produto_pdf="",
            titulo_produto_bruto="NAVEGANDO: UM GUIA PARA ESTUDANTES",
            titulo_capes=None,
            dc_types=["texto"],
        )
        self.assertEqual((fmt2, src2), ("Folder / Panfleto", "dissertacao_ficha"))

        # Ignora mídia citada como conteúdo e ferramenta externa ('software IRAMUTEQ')
        fmt3, src3 = classificar_formato_produto_com_fonte(
            resumo_pdf="Fotografias, vídeos e jornais possibilitaram a elaboração do produto educacional na forma de site.",
            descricao_produto_pdf="",
            titulo_produto_bruto="Texto – MEMORIAL",
            titulo_capes=None,
            dc_types=["vídeo", "texto"],
        )
        self.assertEqual((fmt3, src3), ("Site / Portal", "dissertacao_ficha"))

        fmt4, src4 = classificar_formato_produto_com_fonte(
            resumo_pdf="Desenvolveu-se um produto educacional para apoiar gestores.",
            descricao_produto_pdf="O produto educacional foi elaborado a partir da utilização do software IRAMUTEQ.",
            titulo_produto_bruto="Apresentação – IRAMUTEQ: MATERIAL DE APOIO",
            titulo_capes=None,
            dc_types=["apresentação"],
        )
        self.assertEqual((fmt4, src4), ("Palestra / Apresentação", "dissertacao_ficha"))

        fmt5, src5 = classificar_formato_produto_com_fonte(
            resumo_pdf="",
            descricao_produto_pdf="",
            titulo_produto_bruto="Curso – PRODUÇÃO AUDIOVISUAL",
            titulo_capes=None,
            dc_types=[],
        )
        self.assertEqual((fmt5, src5), ("Curso", "dissertacao_ficha"))

        # Plural 'produtos educacionais' + sentença imediatamente seguinte
        fmt6, src6 = classificar_formato_produto_com_fonte(
            resumo_pdf="Entre os produtos educacionais, destaca-se a proposta. O recurso, em formato de narrativa audiovisual, sintetiza os achados.",
            descricao_produto_pdf="",
            titulo_produto_bruto="ORALITURA REFLEXIVA",
            titulo_capes=None,
            dc_types=["vídeo"],
        )
        self.assertEqual((fmt6, src6), ("Vídeo / Audiovisual", "dissertacao_ficha"))

        # Fallback menos prioritário via dc_type do eduCAPES
        fmt7, src7 = classificar_formato_produto_com_fonte(
            resumo_pdf="Estudo concluído sem detalhamento de formato.",
            descricao_produto_pdf="",
            titulo_produto_bruto="TÍTULO NEUTRO",
            titulo_capes=None,
            dc_types=["livro digital"],
        )
        self.assertEqual((fmt7, src7), ("E-book / Livro Digital", "educapes_dc_type"))

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
        self.assertTrue((PROJECT_ROOT / "src" / "lemeept_extractor" / "llm_provider.py").exists())

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

            with patch("lemeept_extractor.llm_provider.time.sleep") as mock_sleep:
                with self.assertRaises(RateLimitError):
                    client.gerar_estruturado("sys", "usr", RespostaInterpretativaLLM, max_retries=2)
                # Só dorme na tentativa 1; na tentativa 2 (última) levanta direto
                mock_sleep.assert_called_once_with(30)
                _, kwargs = client.openai_client.chat.completions.create.call_args
                self.assertEqual(kwargs["extra_body"], {"options": {"num_ctx": 8192}, "think": False})

    def test_chamar_gemini_constroi_generate_content_config_com_thinking_budget(self):
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "fake-key", "LLM_THINKING_BUDGET": "0"},
            clear=False,
        ):
            with patch("lemeept_extractor.llm_provider.genai.Client") as mock_genai_client:
                mock_models = mock_genai_client.return_value.models
                mock_models.generate_content.return_value = SimpleNamespace(text='{"macroprojeto":"MP1"}')

                client = LLMClient()
                saida = client.gerar_estruturado(
                    system_prompt="sys",
                    user_prompt="usr",
                    response_model=RespostaInterpretativaLLM,
                )

                self.assertEqual(saida, '{"macroprojeto":"MP1"}')
                cfg = mock_models.generate_content.call_args.kwargs["config"]
                self.assertEqual(cfg.temperature, 0.0)
                self.assertEqual(cfg.response_mime_type, "application/json")
                self.assertEqual(cfg.thinking_config.thinking_budget, 0)

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
        self.assertEqual(normalizar_formato_produto("livro_digital"), "E-book / Livro Digital")
        self.assertIsNone(normalizar_formato_produto("formato_desconhecido"))
        self.assertEqual(normalizar_formato_produto("ebook"), "E-book / Livro Digital")
        self.assertEqual(normalizar_formato_produto("  Sequência Didática. "), "Sequência Didática")
        self.assertEqual(limpar_resumo_publico("[PÁG. 11]\nRESUMO \n\nConteúdo principal."), "Conteúdo principal.")
        self.assertEqual(normalizar_texto_busca("Educação Crítica!"), "educacao critica")
        self.assertEqual(limpar_palavras_chave([" ept ", "EPT", "a"]), ["Ept"])

    def test_normalizacao_texto_e_pessoas_e_aliases(self):
        from lemeept_extractor.config import usar_config

        self.assertEqual(remover_acentos("Educação Profissional e Tecnológica"), "Educacao Profissional e Tecnologica")
        self.assertEqual(normalizar_espacos("Linha\u200b 1\x01  \n\n\n\nLinha 2"), "Linha 1\n\nLinha 2")
        self.assertEqual(normalizar_chave_busca("  Fátima   Zago "), "fatima zago")
        self.assertEqual(formatar_nome_proprio("MARIA DA SILVA,"), "Maria da Silva")

        self.assertEqual(limpar_nome_pessoa("Profa. Dra. ANA MARIA DE SOUZA (IFC),"), "Ana Maria de Souza")
        self.assertEqual(limpar_nome_pessoa("Prof. Me. Esp. João Carlos:"), "João Carlos")
        self.assertEqual(normalizar_nome_orientador("Dr.Reginaldo Leandro Plácido"), "Reginaldo Leandro Plácido")
        self.assertEqual(normalizar_nome_orientador("Dra.: Juliene Marques Bogo"), "Juliene Marques Bogo")
        self.assertEqual(limpar_nome_pessoa("Débora Magna Santos Costa de Souza,"), "Débora Magna Santos Costa de Souza")

        self.assertEqual(limpar_prefixo_orientador(": Viviane Grimm"), "Viviane Grimm")
        self.assertEqual(limpar_prefixo_orientador("Orientadora: Profª. Drª. ANA PAULA DE LIMA"), "Ana Paula de Lima")

        with usar_config(Path(__file__).resolve().parent.parent / "lemeept.toml"):
            self.assertEqual(limpar_prefixo_orientador("Orientador: Inge R. F. Suhr"), "Inge Renate Frose Suhr")
            self.assertEqual(normalizar_nome_orientador("Fátima Perez Zago de Oliveira."), "Fátima Peres Zago de Oliveira")
            self.assertEqual(normalizar_nome_orientador("Inge R. F. Suhr"), "Inge Renate Frose Suhr")
            self.assertEqual(normalizar_nome_orientador("Eduardo Werneck Ribeiro"), "Eduardo Augusto Werneck Ribeiro")
            self.assertEqual(normalizar_nome_orientador("Leandro Marcos Alves Salgado"), "Leandro Marcos Salgado Alves")
            self.assertEqual(normalizar_nome_orientador("Sonia Regina de Souza Fernandes."), "Sônia Regina de Souza Fernandes")
            self.assertEqual(normalizar_nome_orientador("Carlos Eduardo Monteiro"), "Carlos Eduardo Monteiro")

    def test_normalizacao_e_reconciliacao_autores_referenciados(self):
        from lemeept_extractor.config import usar_config

        self.assertEqual(normalizar_autor_referencia("Demerval Saviani."), "Dermeval Saviani")
        self.assertEqual(normalizar_autor_referencia("H.W. Abramo,"), "H. W. Abramo")
        self.assertEqual(normalizar_autor_referencia("Lev Vigotski"), "Lev Vygotsky")
        self.assertEqual(normalizar_autor_referencia("trivinos"), "trivinos")

        with usar_config(Path(__file__).resolve().parent.parent / "lemeept.toml"):
            reconciliado = reconciliar_autores_referenciados(
                {
                    "EPT-0001": [
                        "Kaplun",  # sobrenome isolado raro mantido como está se não bater
                        "Gabriel Káplun",
                        "Placido",
                        "R. L. Placido",
                        "Augusto Nibaldo Silva Trivinos",
                        "Demerval Saviani",
                        "M. Silva",
                    ],
                    "EPT-0002": [
                        "Gabriel Kaplún",
                        "Reginaldo L. Plácido",
                        "Augusto Nibaldo Silva Triviños",
                        "D. Saviani",
                        "Marise Ramos",
                        "D. L. Lima Filho",
                        "Maria Silva",
                    ],
                    "EPT-0003": [
                        "Marise Nogueira Ramos",
                        "Reginaldo Leandro Plácido",
                        "Domingos Leite Lima Filho",
                        "Marcos Silva",
                        "Acacia Zeneida Kuenzer",
                    ],
                }
            )
        # Regra 1 & aliases: Gabriel Kaplún, Triviños, Saviani, Plácido e Domingos Leite Lima Filho
        self.assertIn("Gabriel Kaplún", reconciliado["EPT-0001"])
        self.assertIn("Augusto Nibaldo Silva Triviños", reconciliado["EPT-0001"])
        self.assertIn("Dermeval Saviani", reconciliado["EPT-0001"])
        self.assertIn("Reginaldo Leandro Plácido", reconciliado["EPT-0001"])
        self.assertIn("Dermeval Saviani", reconciliado["EPT-0002"])
        self.assertIn("Marise Nogueira Ramos", reconciliado["EPT-0002"])
        self.assertIn("Domingos Leite Lima Filho", reconciliado["EPT-0002"])
        # Homônimo ambíguo ('M. Silva' com Maria Silva e Marcos Silva) NÃO é fundido indevidamente
        self.assertIn("M. Silva", reconciliado["EPT-0001"])
        self.assertIn("Maria Silva", reconciliado["EPT-0002"])
        self.assertIn("Marcos Silva", reconciliado["EPT-0003"])

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
            self.assertEqual(atualizado.produto.formato, "Sequência Didática")
            self.assertEqual(atualizado.produto.nivel_aplicacao, "Educação Profissional e Tecnológica")
            self.assertIn("sequencia didatica", atualizado.indice_busca.texto_busca_normalizado)
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
            saida1 = compilar_pipeline_v4(records_dir=rec_dir, output_dir=dist_dir)
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
            saida2 = compilar_pipeline_v4(records_dir=rec_dir, output_dir=dist_dir)
            self.assertFalse(csv_path.exists())
            rec_final = saida2.defesas[0]
            self.assertEqual(rec_final.dissertacao.base_epistemologica.valor, "Pedagogia Histórico-Crítica")
            self.assertTrue(rec_final.dissertacao.base_epistemologica.curado_humano)
            self.assertFalse(rec_final.dissertacao.base_epistemologica.revisao_pendente)
            self.assertIn("pedagogia historico critica", rec_final.indice_busca.texto_busca_normalizado)

    def test_compilar_reconcilia_autores_entre_registros_e_eh_idempotente(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rec_dir = tmp_path / "records"
            dist_dir = tmp_path / "dist"
            rec_dir.mkdir()
            dist_dir.mkdir()

            resp_ok = RespostaInterpretativaLLM(
                macroprojeto="MP1",
                produto_titulo="Produto Teste",
                produto_tipo="material_didatico_instrucional",
                produto_publico_alvo=["docentes_professores"],
                produto_nivel_aplicacao="Ensino Médio Integrado",
                base_epistemologica=BaseEpistemologicaLLM(
                    valor="pedagogia_historico_critica",
                    candidato=None,
                    confianca="alta",
                    justificativa="Fundamentado em Saviani.",
                    evidencias=[EvidenciaCurtaLLM(secao="Introdução", pagina=12, trecho_curto="Prática social.")],
                ),
            )
            p1 = _make_sample_payload(cod="EPT-0903", autores_ref=["Gabriel Kaplun", "D. H. Moura"])
            p2 = _make_sample_payload(cod="EPT-0904", autores_ref=["Gabriel Kaplún", "Dante Henrique Moura"])
            (rec_dir / "EPT-0903.json").write_text(montar_registro_final(p1, resp_ok).model_dump_json(indent=2), encoding="utf-8")
            (rec_dir / "EPT-0904.json").write_text(montar_registro_final(p2, resp_ok).model_dump_json(indent=2), encoding="utf-8")

            saida1 = compilar_pipeline_v4(records_dir=rec_dir, output_dir=dist_dir)
            r1 = next(d for d in saida1.defesas if d.id == "EPT-0903")
            self.assertEqual(r1.dissertacao.autores_referenciados, ["Dante Henrique Moura", "Gabriel Kaplún"])
            self.assertIn("dante henrique moura", r1.indice_busca.texto_busca_normalizado)

            # Arquivo individual também foi atualizado e segunda compilação é idempotente
            gravado = ContratoDefesaV4.model_validate_json((rec_dir / "EPT-0903.json").read_text(encoding="utf-8"))
            self.assertEqual(gravado.dissertacao.autores_referenciados, ["Dante Henrique Moura", "Gabriel Kaplún"])
            with self.assertLogs("lemeept_extractor.stages.compile", level="INFO") as logs:
                compilar_pipeline_v4(records_dir=rec_dir, output_dir=dist_dir)
            self.assertFalse(any("reconciliados em" in m for m in logs.output))


class TestCatalogsAndModularity(unittest.TestCase):
    def test_resources_json_e_catalogs_sem_duplicacao(self):
        from lemeept_extractor import catalogs
        from lemeept_extractor.extractors import (
            classifiers,
            educapes,
            metadata,
            pdf_sections,
        )

        self.assertEqual(catalogs.MP_PARA_LP["MP1"], "LP1")
        self.assertEqual(catalogs.MP_PARA_LP["MP6"], "LP2")
        self.assertIn("E-book / Livro Digital", catalogs.FORMATOS_PRODUTO_CANONICOS)
        self.assertEqual(catalogs.ALIASES_FORMATO_PRODUTO["hq"], "História em Quadrinhos (HQ)")

        raw_ref = json.loads((catalogs.RESOURCES_DIR / "referencias.json").read_text(encoding="utf-8"))
        raw_pes = json.loads((catalogs.RESOURCES_DIR / "pessoas.json").read_text(encoding="utf-8"))
        self.assertEqual(raw_pes["aliases_docentes"], {})
        self.assertNotIn("blumenau", raw_pes["stopwords_continuacao_nome"])
        self.assertNotIn("blumenau", raw_ref["stopwords_token_nao_pessoa"])
        self.assertNotIn("r l placido", raw_ref["aliases_autores_referencia"])
        self.assertEqual(
            set(raw_ref["stopwords_entidade"]) & set(raw_ref["stopwords_token_nao_pessoa"]),
            set(),
        )
        self.assertTrue({"capes", "brasil"}.issubset(catalogs.STOPWORDS_TOKEN_NAO_PESSOA))

        for k, v in catalogs.ALIASES_DOCENTES.items():
            self.assertEqual(catalogs.ALIASES_AUTORES_REFERENCIA.get(k), v)

        # Garante que step2_deterministic reexporta os módulos especializados sem reescrita
        self.assertIs(extrair_autores_referencias, extrair_autores_ref_direto)
        self.assertIs(detectar_macroprojeto_e_linha, classifiers.detectar_macroprojeto_e_linha)
        self.assertIs(classificar_formato_produto_com_fonte, classifiers.classificar_formato_produto_com_fonte)
        self.assertIs(extrair_coorientador, metadata.extrair_coorientador)
        self.assertIs(isolar_secoes_pdf, pdf_sections.isolar_secoes_pdf)
        self.assertIs(coletar_evidencias_educapes, educapes.coletar_evidencias_educapes)


class TestUniversalIngestionAndPackaging(unittest.TestCase):
    @staticmethod
    def _criar_pdf_teste(destino: Path, paginas_texto: list[str]) -> Path:
        import pymupdf

        destino.parent.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open()
        for texto in paginas_texto:
            page = doc.new_page()
            page.insert_text((72, 72), texto)
        doc.save(destino)
        doc.close()
        return destino

    def test_ingestao_csv_local_e_preservacao_ids(self):
        from lemeept_extractor.models import Stage1ManifestV4
        from lemeept_extractor.stages.ingest import ingerir_de_csv

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            origem_dir = tmp_path / "origem"
            pdfs_dest = tmp_path / "pdfs_dest"
            manifest_path = tmp_path / "stage1_manifest.json"
            ref_path = tmp_path / "ref_manifest.json"

            pdf_ok = self._criar_pdf_teste(
                origem_dir / "dissertacao_ana.pdf",
                ["INSTITUTO FEDERAL DE SANTA CATARINA\nAna Paula Costa\nEnsino Integrado\n2024"],
            )
            pdf_corrompido = origem_dir / "corrompido.pdf"
            origem_dir.mkdir(parents=True, exist_ok=True)
            pdf_corrompido.write_text("nao eh pdf", encoding="utf-8")

            ref_manifest = Stage1ManifestV4(
                total_registros=1,
                registros=[
                    {
                        "id": "EPT-0042",
                        "fonte_profept": {
                            "titulo_bruto": "Ensino Integrado",
                            "autor_bruto": "Ana Paula Costa",
                            "ano": 2024,
                            "campus": "Florianópolis",
                            "url_dissertacao": "",
                        },
                        "arquivos": {
                            "pdf_dissertacao_path": "pdf/dissertacoes/EPT-0042.pdf",
                            "sha256_dissertacao": "abc",
                            "status_download": "OK",
                        },
                    }
                ],
            )
            ref_path.write_text(ref_manifest.model_dump_json(), encoding="utf-8")

            csv_path = tmp_path / "acervo.csv"
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["titulo", "autor", "orientador", "ano", "pdf", "instituicao", "campus", "sem_produto"])
                writer.writerow([
                    "Ensino Integrado",
                    "ANA PAULA COSTA",
                    "Prof. Dr. Carlos Lima",
                    "2024",
                    str(pdf_ok),
                    "IFSC",
                    "Florianópolis",
                    "sim",
                ])
                writer.writerow([
                    "Arquivo Invalido",
                    "Pedro Alves",
                    "",
                    "2025",
                    str(pdf_corrompido),
                    "IFSC",
                    "Joinville",
                    "nao",
                ])

            manifesto = ingerir_de_csv(
                csv_path=csv_path,
                caminho_manifesto_saida=manifest_path,
                diretorio_pdfs=pdfs_dest,
                caminho_referencia_ids=[ref_path],
            )

            self.assertEqual(manifesto.total_registros, 2)
            reg_ana = next(r for r in manifesto.registros if r.id == "EPT-0042")
            reg_pedro = next(r for r in manifesto.registros if r.id == "EPT-0043")
            self.assertEqual(reg_ana.arquivos.status_download, "OK")
            self.assertEqual(len(reg_ana.arquivos.sha256_dissertacao), 64)
            self.assertTrue((pdfs_dest / "EPT-0042.pdf").exists())
            self.assertEqual(reg_ana.fonte_profept.instituicao, "IFSC")
            self.assertTrue(reg_ana.fonte_profept.sem_produto)
            self.assertEqual(reg_pedro.arquivos.status_download, "CORROMPIDO")
            self.assertEqual(reg_pedro.arquivos.sha256_dissertacao, "")

    def test_ingestao_diretorio_pdfs_e_fluxo_somente_dissertacoes(self):
        from lemeept_extractor.models import RespostaInterpretativaDissertacaoLLM
        from lemeept_extractor.stages.extract import executar_etapa2
        from lemeept_extractor.stages.ingest import ingerir_de_diretorio_pdfs

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdfs_dir = tmp_path / "pdfs_locais"
            manifest_path = tmp_path / "stage1_manifest.json"
            stage2_dir = tmp_path / "stage2"
            records_dir = tmp_path / "records"
            dist_dir = tmp_path / "dist"

            self._criar_pdf_teste(
                pdfs_dir / "EPT-0777.pdf",
                [
                    "INSTITUTO FEDERAL DO PARANA\nCAMPUS CURITIBA\n"
                    "Maria Eduarda Nunes\n"
                    "Praticas Integradoras na EPT\n"
                    "Orientador: Prof. Dr. Joao Mendes\n"
                    "2024",
                    "FICHA CATALOGRÁFICA\nNunes, Maria Eduarda.\n"
                    "Práticas integradoras na EPT / Maria Eduarda Nunes. - Curitiba, 2024.",
                    "RESUMO\nPesquisa no âmbito do MP1 sobre currículo integrado.\n"
                    "Palavras-chave: EPT; Currículo Integrado.",
                    "INTRODUÇÃO\nO trabalho como princípio educativo fundamenta esta investigação (SAVIANI, 2019).",
                    "REFERÊNCIAS\nSAVIANI, Dermeval. Pedagogia histórico-crítica. Campinas: Autores Associados, 2019.",
                ],
            )

            manifesto = ingerir_de_diretorio_pdfs(
                origem_pdfs_dir=pdfs_dir,
                caminho_manifesto_saida=manifest_path,
                instituicao_padrao="IFPR",
                somente_dissertacoes=True,
            )
            self.assertEqual(manifesto.total_registros, 1)
            item = manifesto.registros[0]
            self.assertEqual(item.id, "EPT-0777")
            self.assertEqual(item.fonte_profept.ano, 2024)
            self.assertEqual(item.fonte_profept.instituicao, "IFPR")
            self.assertTrue(item.fonte_profept.sem_produto)
            self.assertEqual(item.arquivos.status_download, "OK")

            executar_etapa2(
                manifest_path=manifest_path,
                output_dir=stage2_dir,
                cache_dir=tmp_path / "cache",
            )
            payload_file = stage2_dir / "EPT-0777.json"
            self.assertTrue(payload_file.exists())
            payload = ContratoExtracaoDeterministicaV4.model_validate_json(
                payload_file.read_text(encoding="utf-8")
            )
            self.assertEqual(payload.metadados_resolvidos.instituicao, "IFPR")
            self.assertEqual(payload.metadados_resolvidos.campus, "Curitiba")
            self.assertTrue(payload.metadados_resolvidos.sem_produto)
            self.assertIsNone(payload.evidencias_educapes.tipo_produto_regex)

            prompt = montar_prompt_enxuto(payload)
            self.assertNotIn("evidencias_produto", prompt)

            mock_llm = MagicMock()
            mock_llm.gerar_estruturado.return_value = RespostaInterpretativaDissertacaoLLM(
                macroprojeto="MP1",
                base_epistemologica=BaseEpistemologicaLLM(
                    valor="pedagogia_historico_critica",
                    candidato=None,
                    confianca="alta",
                    justificativa="Declara Saviani na introdução.",
                    evidencias=[
                        EvidenciaCurtaLLM(
                            secao="Introdução",
                            pagina=4,
                            trecho_curto="O trabalho como princípio educativo fundamenta esta investigação.",
                        )
                    ],
                ),
            ).model_dump_json()

            registro = processar_payload(
                payload_file,
                SKILL_PATH.read_text(encoding="utf-8"),
                mock_llm,
                records_dir=records_dir,
            )
            self.assertIsNotNone(registro)
            self.assertIsNone(registro.produto)
            self.assertFalse(registro.indice_busca.tem_produto_vinculado)

            stats = ressincronizar_registros_deterministico(stage2_dir=stage2_dir, records_dir=records_dir)
            self.assertEqual(stats["sincronizados"], 1)

            saida = compilar_pipeline_v4(records_dir=records_dir, output_dir=dist_dir)
            self.assertEqual(saida.total_defesas, 1)
            self.assertEqual(saida.total_producoes, 1)
            self.assertIsNone(saida.defesas[0].produto)

    def test_ingestao_diretorio_pdfs_sem_arquivo_orfao_ao_reutilizar_id(self):
        from lemeept_extractor.models import Stage1ManifestV4
        from lemeept_extractor.stages.ingest import ingerir_de_diretorio_pdfs

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            origem = tmp_path / "origem"
            destino = tmp_path / "destino"
            manifest_path = tmp_path / "stage1.json"
            ref_path = tmp_path / "ref.json"

            self._criar_pdf_teste(
                origem / "trabalho_avulso.pdf",
                ["INSTITUTO FEDERAL\nAna Paula Costa\nPesquisa EPT\n2025"],
            )
            ref_manifest = Stage1ManifestV4(
                total_registros=1,
                registros=[
                    {
                        "id": "EPT-0088",
                        "fonte_profept": {
                            "titulo_bruto": "Pesquisa EPT",
                            "autor_bruto": "Ana Paula Costa",
                            "ano": 2025,
                            "campus": "",
                            "url_dissertacao": "",
                        },
                        "arquivos": {
                            "pdf_dissertacao_path": "pdf/dissertacoes/EPT-0088.pdf",
                            "sha256_dissertacao": "abc",
                            "status_download": "OK",
                        },
                    }
                ],
            )
            ref_path.write_text(ref_manifest.model_dump_json(), encoding="utf-8")

            manifesto = ingerir_de_diretorio_pdfs(
                origem_pdfs_dir=origem,
                caminho_manifesto_saida=manifest_path,
                diretorio_pdfs=destino,
                caminho_referencia_ids=[ref_path],
                copiar_pdfs=True,
            )
            self.assertEqual(manifesto.registros[0].id, "EPT-0088")
            self.assertEqual(
                sorted(p.name for p in destino.glob("*.pdf")),
                ["EPT-0088.pdf"],
            )

    def test_cli_skill_path_e_frontend_builder(self):
        import io
        from contextlib import redirect_stdout
        from lemeept_extractor import __version__, cli, frontend_builder

        self.assertTrue(SKILL_PATH.exists())
        self.assertEqual(SKILL_PATH.parent, Path(__file__).resolve().parent.parent / "src" / "lemeept_extractor")
        comandos = cli.available_subcommands()
        self.assertEqual(set(comandos.keys()), {"ingest", "extract", "llm", "compile", "build-frontend"})
        self.assertNotIn("collect", comandos)

        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(__version__, buf.getvalue())

        bundle, metricas = frontend_builder.gerar_bundle(Path(__file__).resolve().parent.parent)
        self.assertNotIn("\n\n", bundle)
        self.assertGreater(metricas["css_chaves"], 0)


class TestConfigAndOverlays(unittest.TestCase):
    def test_catalogos_base_puros_sem_contexto_ifc(self):
        from lemeept_extractor import catalogs

        catalogs.resetar_catalogos()
        self.assertEqual(catalogs.ALIASES_DOCENTES, {})
        self.assertNotIn("blumenau", catalogs.STOPWORDS_CONTINUACAO_NOME)
        self.assertNotIn("blumenau", catalogs.STOPWORDS_TOKEN_NAO_PESSOA)
        meta = MetadadosResolvidos(
            ano=2025,
            autor="Autor",
            orientador="Orientador",
            linha_pesquisa="LP1",
            macroprojeto="MP1",
        )
        self.assertEqual(meta.instituicao, "")
        self.assertEqual(meta.campus, "")

    def test_overlay_customizado_outro_campus_e_reset(self):
        from lemeept_extractor import catalogs
        from lemeept_extractor.config import carregar_config, usar_config

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            overlay_json = tmp_path / "overlay_ifsc.json"
            overlay_json.write_text(
                json.dumps(
                    {
                        "aliases_docentes": {"ana p silva": "Ana Paula Silva"},
                        "aliases_autores_referencia": {"j m santos": "João Marcos Santos"},
                        "stopwords_continuacao_nome": ["florianopolis"],
                        "bases_epistemologicas_canonicas": ["Pedagogia Social"],
                    }
                ),
                encoding="utf-8",
            )
            skill_custom = tmp_path / "SKILL_custom.md"
            skill_custom.write_text("# Skill customizada", encoding="utf-8")

            toml_path = tmp_path / "lemeept.toml"
            toml_path.write_text(
                '[instituicao]\n'
                'nome = "Instituto Federal de Santa Catarina (IFSC)"\n'
                'campus = "Florianópolis"\n'
                'sigla = "IFSC"\n'
                'somente_dissertacoes = true\n\n'
                '[catalogos]\n'
                'overlay_json = "overlay_ifsc.json"\n\n'
                '[llm]\n'
                'skill_path = "SKILL_custom.md"\n',
                encoding="utf-8",
            )

            cfg = carregar_config(toml_path)
            self.assertEqual(cfg.instituicao.nome, "Instituto Federal de Santa Catarina (IFSC)")
            self.assertEqual(cfg.instituicao.campus, "Florianópolis")
            self.assertTrue(cfg.instituicao.somente_dissertacoes)
            self.assertEqual(cfg.llm.skill_path, skill_custom.resolve())

            with usar_config(cfg):
                self.assertEqual(normalizar_nome_orientador("Ana P. Silva"), "Ana Paula Silva")
                self.assertEqual(normalizar_autor_referencia("J. M. Santos"), "João Marcos Santos")
                self.assertIn("florianopolis", catalogs.STOPWORDS_CONTINUACAO_NOME)
                val, eh_canon = normalizar_base_epistemologica("pedagogia social")
                self.assertEqual(val, "Pedagogia Social")
                self.assertTrue(eh_canon)

            # Ao sair do context manager, o catálogo volta ao estado base puro
            self.assertEqual(catalogs.ALIASES_DOCENTES, {})
            self.assertNotIn("florianopolis", catalogs.STOPWORDS_CONTINUACAO_NOME)

    def test_paridade_perfil_ifc_blumenau(self):
        from lemeept_extractor.config import carregar_config, usar_config

        repo_root = Path(__file__).resolve().parent.parent
        toml_path = repo_root / "lemeept.toml"
        self.assertTrue(toml_path.exists())

        cfg = carregar_config(toml_path)
        self.assertEqual(cfg.instituicao.nome, "Instituto Federal Catarinense (IFC)")
        self.assertEqual(cfg.instituicao.campus, "Blumenau")

        with usar_config(cfg):
            self.assertEqual(
                normalizar_nome_orientador("Fátima Perez Zago de Oliveira."),
                "Fátima Peres Zago de Oliveira",
            )
            self.assertEqual(
                normalizar_nome_orientador("Sonia Regina de Souza Fernandes."),
                "Sônia Regina de Souza Fernandes",
            )
            self.assertEqual(normalizar_autor_referencia("R. L. Placido"), "Reginaldo Leandro Plácido")

    def test_cli_flag_global_config(self):
        import io
        from contextlib import redirect_stdout
        from lemeept_extractor import cli
        from lemeept_extractor.config import ENV_CONFIG_VAR

        with tempfile.TemporaryDirectory() as tmp:
            toml_path = Path(tmp) / "custom.toml"
            toml_path.write_text('[instituicao]\nnome = "Teste"\n', encoding="utf-8")

            antigo = os.environ.get(ENV_CONFIG_VAR)
            buf = io.StringIO()
            try:
                with redirect_stdout(buf), self.assertRaises(SystemExit) as cm:
                    cli.main(["--config", str(toml_path), "ingest", "--help"])
                self.assertEqual(cm.exception.code, 0)
                self.assertEqual(os.environ.get(ENV_CONFIG_VAR), antigo)
            finally:
                if antigo is None:
                    os.environ.pop(ENV_CONFIG_VAR, None)
                else:
                    os.environ[ENV_CONFIG_VAR] = antigo


class TestUniversalFrontendBuilder(unittest.TestCase):
    def test_paridade_template_ifc_blumenau_contra_artefatos_publicados(self):
        from lemeept_extractor import frontend_builder

        repo_root = Path(__file__).resolve().parent.parent
        cfg = frontend_builder.carregar_config_frontend(repo_root / "lemeept.toml", root=repo_root)
        bundle, _ = frontend_builder.gerar_bundle(
            root=repo_root,
            usar_template=True,
            frontend_cfg=cfg,
        )
        widget_atual = (repo_root / "public" / "widget-elementor.html").read_text(encoding="utf-8")
        self.assertEqual(bundle, widget_atual)

        loader_renderizado = frontend_builder.renderizar_loader_template(cfg)
        loader_atual = (repo_root / "public" / "loader-elementor.html").read_text(encoding="utf-8")
        self.assertEqual(loader_renderizado.rstrip("\n"), loader_atual.rstrip("\n"))

    def test_gerar_site_completo_outro_campus_em_diretorio_vazio(self):
        from lemeept_extractor import frontend_builder

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "lemeept.toml").write_text(
                '[frontend]\n'
                'titulo = "Painel ProfEPT – IFSC Florianópolis"\n'
                'subtitulo = "Acervo do campus."\n'
                'eyebrow = "IFSC FLORIANÓPOLIS"\n'
                'titulo_graficos = "Panorama IFSC"\n'
                'json_url = "https://ifsc.github.io/painel/public/painel-ept-v4.json"\n',
                encoding="utf-8",
            )

            rc = frontend_builder.main(["--root", str(tmp_path), "--emit-site"])
            self.assertEqual(rc, 0)

            index_gerado = (tmp_path / "index.html").read_text(encoding="utf-8")
            self.assertIn("Painel ProfEPT – IFSC Florianópolis", index_gerado)
            self.assertIn("IFSC FLORIANÓPOLIS", index_gerado)
            self.assertIn("https://ifsc.github.io/painel/public/painel-ept-v4.json", index_gerado)
            self.assertNotIn("regi-lpf", index_gerado)
            self.assertNotIn("Bússola LEME", index_gerado)

            self.assertTrue((tmp_path / "frontend" / "styles.css").exists())
            self.assertTrue((tmp_path / "frontend" / "app.js").exists())

            widget_gerado = (tmp_path / "public" / "widget-elementor.html").read_text(encoding="utf-8")
            self.assertNotIn("\n\n", widget_gerado)
            self.assertIn("https://ifsc.github.io/painel/public/painel-ept-v4.json", widget_gerado)
            frontend_builder.validar_bundle(widget_gerado)

            loader_gerado = (tmp_path / "public" / "loader-elementor.html").read_text(encoding="utf-8")
            self.assertIn('data-widget-url="https://ifsc.github.io/painel/public/widget-elementor.html"', loader_gerado)

            rc_check = frontend_builder.main(["--root", str(tmp_path), "--check", "--emit-loader"])
            self.assertEqual(rc_check, 0)

    def test_escape_html_e_overrides_cli_frontend_builder(self):
        from lemeept_extractor import frontend_builder

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rc = frontend_builder.main(
                [
                    "--root",
                    str(tmp_path),
                    "--from-template",
                    "--titulo",
                    'Painel <Teste> & "Campus"',
                    "--subtitulo",
                    "Subtítulo <seguro>",
                    "--json-url",
                    "https://exemplo.edu.br/painel/public/painel-ept-v4.json",
                ]
            )
            self.assertEqual(rc, 0)
            widget = (tmp_path / "public" / "widget-elementor.html").read_text(encoding="utf-8")
            self.assertIn("Painel &lt;Teste&gt; &amp; &quot;Campus&quot;", widget)
            self.assertIn("Subtítulo &lt;seguro&gt;", widget)

    def test_integridade_simbolos_js_e_higiene_frontend(self):
        app_js_path = PROJECT_ROOT / "frontend" / "app.js"
        styles_css_path = PROJECT_ROOT / "frontend" / "styles.css"
        widget_path = PROJECT_ROOT / "public" / "widget-elementor.html"
        loader_tpl_path = (
            PROJECT_ROOT
            / "src"
            / "lemeept_extractor"
            / "templates"
            / "frontend"
            / "loader-elementor.template.html"
        )
        loader_pub_path = PROJECT_ROOT / "public" / "loader-elementor.html"

        for arquivo in (app_js_path, styles_css_path, widget_path, loader_tpl_path, loader_pub_path):
            raw = arquivo.read_bytes()
            self.assertEqual(raw.count(b"\r"), 0, f"CR encontrado em {arquivo}")
            self.assertTrue(raw.endswith(b"\n"), f"Sem LF final em {arquivo}")

        css_text = styles_css_path.read_text(encoding="utf-8")
        self.assertIn("#leme-painel-ept .leme-scope-bar.is-hidden", css_text)
        self.assertIn("#leme-painel-ept .leme-field.is-hidden", css_text)

        js_text = app_js_path.read_text(encoding="utf-8")
        widget_text = widget_path.read_text(encoding="utf-8")

        for proibido in ("multiplicadorEscopo", "lista.length * 2", "Falha ao carregar o painel ProfEPT v4"):
            self.assertNotIn(proibido, js_text)
            self.assertNotIn(proibido, widget_text)

        for obrigatorio in ("pesoProducaoItem", "contarProducoesLista", "atualizarModoAcervo"):
            self.assertIn(obrigatorio, js_text)
            self.assertIn(obrigatorio, widget_text)

        # Lexer JS que preserva estrutura sintatica removendo comentarios, strings e regexes
        def extrair_codigo_sem_literais(src: str) -> str:
            out = []
            i = 0
            n = len(src)
            prev_token = ""
            regex_prefixes = set("=(:,!&|?[{;+-*/%^~<>")
            while i < n:
                ch = src[i]
                nxt = src[i + 1] if i + 1 < n else ""
                if ch == "/" and nxt == "/":
                    i += 2
                    while i < n and src[i] != "\n":
                        i += 1
                    continue
                if ch == "/" and nxt == "*":
                    i += 2
                    while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                        if src[i] == "\n":
                            out.append("\n")
                        i += 1
                    i += 2
                    continue
                if ch in ("'", '"', "`"):
                    quote = ch
                    out.append(quote)
                    i += 1
                    while i < n and src[i] != quote:
                        if src[i] == "\\":
                            i += 2
                            continue
                        if src[i] == "\n":
                            out.append("\n")
                        i += 1
                    out.append(quote)
                    i += 1
                    prev_token = quote
                    continue
                if ch == "/" and (not prev_token or prev_token in regex_prefixes or prev_token == "return"):
                    in_class = False
                    i += 1
                    while i < n:
                        c = src[i]
                        if c == "\\":
                            i += 2
                            continue
                        if c == "[":
                            in_class = True
                        elif c == "]" and in_class:
                            in_class = False
                        elif c == "/" and not in_class:
                            i += 1
                            while i < n and src[i].isalpha():
                                i += 1
                            break
                        i += 1
                    out.append(" REGEX ")
                    prev_token = "REGEX"
                    continue
                out.append(ch)
                if ch.isalnum() or ch in "_$":
                    m = re.match(r"[A-Za-z0-9_$]+", src[i:])
                    if m:
                        tok = m.group(0)
                        out.pop()
                        out.append(tok)
                        i += len(tok)
                        prev_token = tok
                        continue
                elif not ch.isspace():
                    prev_token = ch
                i += 1
            return "".join(out)

        codigo_limpo = extrair_codigo_sem_literais(js_text)
        funcoes_declaradas = set(re.findall(r"\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", codigo_limpo))
        vars_declaradas = set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\b", codigo_limpo))
        params_declarados = set()
        for params_raw in re.findall(r"\bfunction(?:\s+[A-Za-z_$][A-Za-z0-9_$]*)?\s*\(([^)]*)\)", codigo_limpo):
            for p in params_raw.split(","):
                p_clean = p.strip().lstrip(".").split("=")[0].strip()
                if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", p_clean):
                    params_declarados.add(p_clean)
        palavras_js = {
            "if", "for", "while", "switch", "catch", "function", "return", "typeof",
            "void", "delete", "new", "await", "throw", "else", "in", "of",
            "Array", "Boolean", "Date", "Error", "Function", "Intl", "JSON", "Map",
            "Math", "Number", "Object", "Promise", "RegExp", "Set", "String", "URL",
            "Blob", "fetch", "setTimeout", "clearTimeout", "encodeURIComponent",
            "decodeURIComponent", "isNaN", "parseInt", "parseFloat",
            "requestAnimationFrame", "document", "window", "console",
        }
        chamadas_livres = set(re.findall(r"(?<![.\w$])([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", codigo_limpo))
        conhecidos = funcoes_declaradas | vars_declaradas | params_declarados | palavras_js
        nao_definidos = sorted(chamadas_livres - conhecidos)
        self.assertEqual(nao_definidos, [], f"Chamadas JS indefinidas em app.js: {nao_definidos}")

        funcoes_orfas = [
            fn for fn in sorted(funcoes_declaradas)
            if len(re.findall(rf"\b{re.escape(fn)}\b", codigo_limpo)) < 2
        ]
        self.assertEqual(funcoes_orfas, [], f"Funcoes JS declaradas sem uso em app.js: {funcoes_orfas}")


class TestAuditWave1SecurityAndIO(unittest.TestCase):
    def test_escrever_atomico_e_download_parcial_nao_deixam_pdf_corrompido(self):
        from requests import RequestException

        from lemeept_extractor.io_utils import baixar_pdf_com_validacao, escrever_texto_atomico

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alvo = root / "sub" / "dado.json"
            escrever_texto_atomico(alvo, '{"ok": true}')
            self.assertEqual(alvo.read_text(encoding="utf-8"), '{"ok": true}')

            pdf_dest = root / "EPT-0001.pdf"

            class _RespParcial:
                status_code = 200

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def iter_content(self, chunk_size=65536):
                    yield b"%PDF-1.4\n" + (b"0" * 1500)
                    raise RequestException("queda no meio do download")

            with patch("lemeept_extractor.io_utils.requests.get", return_value=_RespParcial()):
                sha, status = baixar_pdf_com_validacao("https://exemplo.edu.br/a.pdf", pdf_dest)

            self.assertEqual(status, "ERRO_HTTP")
            self.assertEqual(sha, "")
            self.assertFalse(pdf_dest.exists())
            self.assertFalse(pdf_dest.with_name(f".{pdf_dest.name}.tmp").exists())

    def test_resolver_id_estavel_evita_colisao_no_mesmo_lote(self):
        from lemeept_extractor.io_utils import resolver_id_estavel

        mapa = {"https://ex/a.pdf": "EPT-0001"}
        usados = set()
        id1, max1, novo1 = resolver_id_estavel(mapa, 1, id_explicito="EPT-0001", ids_usados=usados)
        id2, max2, novo2 = resolver_id_estavel(mapa, max1, url="https://ex/a.pdf", ids_usados=usados)
        self.assertEqual(id1, "EPT-0001")
        self.assertFalse(novo1)
        self.assertEqual(id2, "EPT-0002")
        self.assertEqual(max2, 2)
        self.assertTrue(novo2)

    def test_curadoria_csv_virgula_cabecalho_invalido_traversal_e_formula_injection(self):
        from lemeept_extractor.models import (
            BaseEpistemologicaV4,
            ContratoDefesaV4,
            DissertacaoFinalV4,
            IndiceBuscaV4,
        )
        from lemeept_extractor.stages.compile import aplicar_curadoria_csv, compilar_pipeline_v4

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records_dir = root / "records"
            out_dir = root / "public"
            records_dir.mkdir()
            out_dir.mkdir()

            reg = ContratoDefesaV4(
                id="EPT-0010",
                ano=2025,
                autor="Maria Silva",
                orientador="Joao Lima",
                instituicao="IFC",
                campus="Blumenau",
                linha_pesquisa="LP1",
                macroprojeto="MP1",
                dissertacao=DissertacaoFinalV4(
                    titulo="=SUM(1,2) Dissertacao Teste",
                    link="https://exemplo.edu.br/10.pdf",
                    resumo="Resumo",
                    base_epistemologica=BaseEpistemologicaV4(
                        valor=None,
                        candidato="Pedagogia Histórico-Crítica",
                        confianca="baixa",
                        revisao_pendente=True,
                        justificativa="=cmd|'/C calc'!A0",
                    ),
                ),
                indice_busca=IndiceBuscaV4(
                    texto_busca_normalizado="ept 0010",
                    termos_unificados=[],
                    tem_produto_vinculado=False,
                    tem_resumo=True,
                ),
            )
            (records_dir / "EPT-0010.json").write_text(reg.model_dump_json(indent=2), encoding="utf-8")

            # Compila para gerar CSV sanitizado contra formula injection
            compilar_pipeline_v4(records_dir=records_dir, output_dir=out_dir)
            csv_path = out_dir / "revisao_epistemologica_pendente.csv"
            csv_raw = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("'=SUM(1,2)", csv_raw)
            self.assertIn("'=cmd|", csv_raw)

            # Cabeçalho inválido não pode ser sobrescrito silenciosamente
            csv_invalido = out_dir / "invalido.csv"
            csv_invalido.write_text("col_errada;outra\n1;2\n", encoding="utf-8-sig")
            with self.assertRaises(ValueError):
                aplicar_curadoria_csv(records_dir=records_dir, relatorio_revisao=csv_invalido)
            self.assertIn("col_errada", csv_invalido.read_text(encoding="utf-8-sig"))

            # CSV com vírgula + tentativa de path traversal no id
            csv_virgula = out_dir / "virgula.csv"
            csv_virgula.write_text(
                "id,status_curadoria,base_epistemologica_aprovada\n"
                "../evil,APROVADO,Teoria Crítica\n"
                "EPT-0010,APROVADO,Teoria Crítica\n",
                encoding="utf-8-sig",
            )
            atualizados = aplicar_curadoria_csv(records_dir=records_dir, relatorio_revisao=csv_virgula)
            self.assertEqual(atualizados, 1)
            salvo = json.loads((records_dir / "EPT-0010.json").read_text(encoding="utf-8"))
            self.assertEqual(salvo["dissertacao"]["base_epistemologica"]["valor"], "Teoria Crítica")
            self.assertTrue(salvo["dissertacao"]["base_epistemologica"]["curado_humano"])

    def test_loader_escapa_fechamento_script_e_extract_retorna_codigo_erro(self):
        from lemeept_extractor.frontend_builder import DEFAULT_FRONTEND_CONFIG, renderizar_loader_template
        from lemeept_extractor.stages.extract import main as extract_main

        cfg = {**DEFAULT_FRONTEND_CONFIG, "loader_erro_log": "Erro </script><script>alert(1)</script>"}
        loader = renderizar_loader_template(cfg)
        self.assertNotIn("Erro </script>", loader)
        self.assertIn(r"<\/script>", loader)

        with tempfile.TemporaryDirectory() as tmp:
            manifesto = Path(tmp) / "manifest.json"
            manifesto.write_text(
                json.dumps({"registros": [{"id": "EPT-0099", "fonte_profept": {}, "arquivos": {"pdf_dissertacao_path": "/nao/existe.pdf"}}]}),
                encoding="utf-8",
            )
            rc = extract_main(["--manifesto", str(manifesto), "--saida-dir", tmp])
            self.assertEqual(rc, 1)


class TestAuditWave1Bibliometrics(unittest.TestCase):
    def test_janelas_epistemologicas_centradas_e_novas_matrizes(self):
        from lemeept_extractor.extractors.pdf_sections import isolar_secoes_pdf

        intro = "1 INTRODUÇÃO\n" + ("Texto contextual introdutório. " * 25)
        bloco_longo = ("Contextualização preliminar extensa. " * 45) + (
            "A análise ancora-se em David Ausubel e na aprendizagem significativa com subsunçores."
            " "
        ) + ("Consideração complementar final. " * 15)
        bloco_adorno = ("Discussão inicial. " * 45) + (
            "Sob a ótica da Teoria Crítica, Adorno e Horkheimer discutem a semiformação."
        )
        paginas = [
            (1, "Capa"),
            (8, intro),
            (15, bloco_longo),
            (16, bloco_adorno),
            (30, "REFERÊNCIAS\nAUSUBEL, David. Psicologia Educacional. 1980."),
        ]
        recortes, _ = isolar_secoes_pdf(paginas)
        textos = [t.texto for t in recortes.trechos_epistemologicos]
        self.assertTrue(any("Ausubel" in tx for tx in textos))
        self.assertTrue(any("Adorno" in tx for tx in textos))

    def test_overlay_normaliza_acentos_e_base_composta_com_phc_e_barra(self):
        from lemeept_extractor.config import CatalogosConfig, LemeConfig, usar_config
        from lemeept_extractor.normalizers import normalizar_base_epistemologica, normalizar_nome_orientador
        from lemeept_extractor.references import extrair_autores_referencias

        cfg = LemeConfig(
            catalogos=CatalogosConfig(
                aliases_docentes={"Fátima Silva": "Fátima Silva"},
                stopwords_entidade=["São José"],
            )
        )
        with usar_config(cfg):
            self.assertEqual(normalizar_nome_orientador("Fatima Silva"), "Fátima Silva")
            self.assertEqual(extrair_autores_referencias("SÃO JOSÉ. Plano Diretor. 2022."), [])

        self.assertEqual(
            normalizar_base_epistemologica("MHD e PHC"),
            ("Materialismo Histórico-Dialético e Pedagogia Histórico-Crítica", True),
        )
        self.assertEqual(
            normalizar_base_epistemologica("MHD E Teoria Crítica"),
            ("Materialismo Histórico-Dialético e Teoria Crítica", True),
        )
        self.assertEqual(
            normalizar_base_epistemologica("Educação Libertadora / Freireana e Teoria Crítica"),
            ("Educação Libertadora / Freireana e Teoria Crítica", True),
        )
        self.assertEqual(
            normalizar_base_epistemologica("Materialismo Histórico e Dialético e Pedagogia Histórico-Crítica"),
            ("Materialismo Histórico-Dialético e Pedagogia Histórico-Crítica", True),
        )

    def test_abnt_prenomes_compostos_tres_letras_e_sobrenomes_recuperados(self):
        from lemeept_extractor.references import extrair_autores_referencias

        refs = "\n".join(
            [
                "SARTRE, Jean-Paul. O ser e o nada. Petrópolis: Vozes, 2007.",
                "ROUSSEAU, Jean-Jacques. Emílio. São Paulo: Martins Fontes, 2004.",
                "SILVA, ANA. Didática em EPT. Florianópolis: IFC, 2021.",
                "COSTA, RUI. Trabalho e Educação. Campinas: Autores Associados, 2020.",
                "DELLA FONTE, Sandra Soares. Formação humana. Vitória: Ifes, 2018.",
                "CÂMARA, Joaquim Mattoso. Princípios de linguística. Petrópolis: Vozes, 1979.",
            ]
        )
        autores = extrair_autores_referencias(refs)
        self.assertEqual(
            autores,
            [
                "Ana Silva",
                "Jean-Jacques Rousseau",
                "Jean-Paul Sartre",
                "Joaquim Mattoso Câmara",
                "Rui Costa",
                "Sandra Soares Della Fonte",
            ],
        )


class TestAuditWave1LLMAndStep3(unittest.TestCase):
    def test_llm_provider_json_dumps_llama_sem_ollama_options_e_erro_4xx_sem_retry(self):
        from openai import APIStatusError

        # OpenRouter: usa json.dumps no prompt (aspas duplas válidas) e não retenta 401
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "k", "LLM_DELAY": "0"},
            clear=True,
        ):
            client = LLMClient()
            resp_ok = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"macroprojeto":"MP1"}'))]
            )
            client.openai_client.chat.completions.create = MagicMock(return_value=resp_ok)
            saida = client.gerar_estruturado("sys", "usr", RespostaInterpretativaLLM, max_retries=2)
            self.assertEqual(saida, '{"macroprojeto":"MP1"}')
            user_msg = client.openai_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
            self.assertIn('"additionalProperties": false', user_msg)
            self.assertNotIn("'additionalProperties': False", user_msg)

            req_fake = SimpleNamespace(url="https://openrouter.ai", method="POST", headers={})
            resp_401 = SimpleNamespace(request=req_fake, status_code=401, headers={})
            err_401 = APIStatusError("unauthorized", response=resp_401, body=None)
            client.openai_client.chat.completions.create = MagicMock(side_effect=err_401)
            with patch("lemeept_extractor.llm_provider.time.sleep") as mock_sleep:
                with self.assertRaises(APIStatusError):
                    client.gerar_estruturado("sys", "usr", RespostaInterpretativaLLM, max_retries=3)
                mock_sleep.assert_not_called()
                self.assertEqual(client.openai_client.chat.completions.create.call_count, 1)

        # llama: não envia extra_body.options do Ollama e valida resposta vazia
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "llama", "LLM_NUM_CTX": "4096", "LLM_THINK": "false", "LLM_DELAY": "0"},
            clear=True,
        ):
            client_llama = LLMClient()
            client_llama.openai_client.chat.completions.create = MagicMock(
                return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])
            )
            with self.assertRaises(ValueError):
                client_llama.gerar_estruturado("sys", "usr", RespostaInterpretativaLLM, max_retries=1)
            kwargs_llama = client_llama.openai_client.chat.completions.create.call_args.kwargs
            self.assertNotIn("extra_body", kwargs_llama)

    def test_limite_incremental_etapa3_ignora_ja_processados(self):
        from lemeept_extractor.stages.llm import executar_etapa3

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            s2 = root / "stage2"
            rec = root / "records"
            s2.mkdir()
            rec.mkdir()
            skill = root / "SKILL.md"
            skill.write_text("# SKILL\n", encoding="utf-8")

            for idx in (1, 2, 3):
                cod = f"EPT-000{idx}"
                payload = ContratoExtracaoDeterministicaV4(
                    id=cod,
                    metadados_resolvidos=MetadadosResolvidos(
                        ano=2025,
                        autor=f"Autor {idx}",
                        orientador="Orientador A",
                        instituicao="IFC",
                        campus="Blumenau",
                        linha_pesquisa="LP1",
                        macroprojeto="MP1",
                        sem_produto=True,
                    ),
                    dissertacao_deterministica=DissertacaoDeterministica(
                        titulo=f"Dissertacao {idx}",
                        link=f"https://ex/{idx}.pdf",
                        palavras_chave=["EPT"],
                        autores_referenciados=["Paulo Freire"],
                    ),
                    evidencias_educapes=EvidenciasEduCAPES(),
                    recortes_textuais=RecortesTextuais(resumo="Resumo teste."),
                )
                (s2 / f"{cod}.json").write_text(payload.model_dump_json(), encoding="utf-8")

            # EPT-0001 e EPT-0002 já existem no destino
            (rec / "EPT-0001.json").write_text("{}", encoding="utf-8")
            (rec / "EPT-0002.json").write_text("{}", encoding="utf-8")

            resposta_ok = json.dumps(
                {
                    "macroprojeto": "MP1",
                    "base_epistemologica": {
                        "valor": "Pedagogia Histórico-Crítica",
                        "candidato": None,
                        "confianca": "alta",
                        "justificativa": "Fundamentação explícita.",
                        "evidencias": [],
                    },
                },
                ensure_ascii=False,
            )

            with patch("lemeept_extractor.stages.llm.LLMClient") as mock_cls:
                mock_cls.return_value.gerar_estruturado.return_value = resposta_ok
                falhas = executar_etapa3(
                    limite=1,
                    skill_path=skill,
                    stage2_dir=s2,
                    records_dir=rec,
                    somente_dissertacoes=True,
                )

            self.assertEqual(falhas, 0)
            self.assertEqual(mock_cls.return_value.gerar_estruturado.call_count, 1)
            self.assertTrue((rec / "EPT-0003.json").exists())


class TestAuditWave1FrontendBuilder(unittest.TestCase):
    def test_frontend_builder_output_dir_absoluto_fora_do_root(self):
        from lemeept_extractor.frontend_builder import main as fb_main

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "saida_externa"
            rc = fb_main(
                [
                    "--root",
                    str(PROJECT_ROOT),
                    "--from-template",
                    "--emit-loader",
                    "--output-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "widget-elementor.html").exists())
            self.assertTrue((out_dir / "loader-elementor.html").exists())


if __name__ == "__main__":
    unittest.main()
