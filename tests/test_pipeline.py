from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lemeept.atualizar_dados import ler_registros, processar_registros
from lemeept.pipeline.builder import GeradorPainel
from lemeept.pipeline.classifier import classificar_registro
from lemeept.pipeline.normalizer import normalizar_registro


class TestPipelinePainel(unittest.TestCase):
    def test_normaliza_tags_ano_e_orientador(self):
        registro = normalizar_registro({
            "ano": "Defesa em 2024",
            "orientador": "Dra. Maria Souza",
            "titulo": "Título de teste",
            "palavrasChave": ["EPT; Ensino", "ensino"],
        })
        self.assertEqual("2024", registro["ano"])
        self.assertEqual("maria souza", registro["orientadorChave"])
        self.assertEqual(["EPT", "Ensino"], registro["palavrasChave"])

    def test_nao_classifica_sem_evidencia(self):
        classificacao = classificar_registro({"titulo": "Trabalho sem termos relevantes"})
        self.assertEqual("Não classificado", classificacao["codigoMacroprojeto"])
        self.assertEqual("Sim", classificacao["revisaoManual"])

    def test_classifica_tema_de_inclusao(self):
        classificacao = classificar_registro({
            "titulo": "Acessibilidade e inclusão na educação profissional e tecnológica",
            "produto": "Guia pedagógico sobre educação inclusiva",
            "resumo": "Estudo sobre práticas de acessibilidade para estudantes com deficiência.",
        })
        self.assertEqual("MP2", classificacao["codigoMacroprojeto"])
        self.assertIn(classificacao["confiancaLinhaMacro"], {"Média", "Alta"})

    def test_saida_tem_contrato_estavel_e_resumo_limitado(self):
        resumo = "Texto de resumo longo " * 300
        registros = processar_registros([{
            "Ano": "2023",
            "Autor": "Ana Exemplo",
            "Título da Dissertação": "Material didático para práticas educativas na EPT",
            "Resumo": resumo,
            "Palavras-chave": "produto educacional; ensino",
        }])
        with tempfile.TemporaryDirectory() as pasta:
            destino = GeradorPainel(str(Path(pasta) / "painel.json")).salvar(registros)
            payload = json.loads(destino.read_text(encoding="utf-8"))

        registro = payload[0]
        obrigatorios = {
            "id", "ano", "autor", "orientador", "titulo", "produto", "linhaPesquisa",
            "macroprojeto", "codigoMacroprojeto", "linkPdf", "linkProduto", "searchText",
        }
        self.assertTrue(obrigatorios.issubset(registro))
        self.assertLessEqual(len(registro["resumo"]), 283)
        self.assertNotIn(resumo, registro["searchText"])
        self.assertEqual(1, len({registro["id"]}))

    def test_preserva_classificacao_oficial_existente(self):
        registro = processar_registros([{
            "ano": "2022",
            "autor": "Pessoa Teste",
            "titulo": "Título antigo sem termos de classificação",
            "linhaPesquisa": "Linha revisada",
            "macroprojeto": "Macro revisado",
            "codigoMacroprojeto": "MP4",
            "revisaoManual": "Não",
        }])[0]
        self.assertEqual("MP4", registro["codigoMacroprojeto"])
        self.assertEqual("Linha revisada", registro["linhaPesquisa"])

    def test_conta_dissertacao_e_produto_como_duas_producoes(self):
        registros = processar_registros([
            {"titulo": "Dissertação", "produto": "Guia", "linkProduto": "https://exemplo.org/produto"},
            {"titulo": "Outra dissertação", "produto": "---"},
            {"titulo": "", "produto": "---", "linkProduto": "https://exemplo.org/produto"},
            {"titulo": "Dissertação com dados incompletos", "produto": "A revisar"},
        ])
        with tempfile.TemporaryDirectory() as pasta:
            destino = GeradorPainel(str(Path(pasta) / "painel.json")).salvar(registros)
            payload = json.loads(destino.read_text(encoding="utf-8"))

        self.assertEqual([2, 1, 1, 1], [registro["quantidadeProducoes"] for registro in payload])

    def test_fonte_json_avisa_ou_rejeita_item_invalido(self):
        with tempfile.TemporaryDirectory() as pasta:
            origem = Path(pasta) / "origem.json"
            origem.write_text(json.dumps([{"titulo": "Registro"}, ["inválido"]]), encoding="utf-8")
            registros, ignorados = ler_registros(origem)
            self.assertEqual(1, len(registros))
            self.assertEqual(1, ignorados)
            with self.assertRaisesRegex(ValueError, "Registro 2"):
                ler_registros(origem, estrito=True)


if __name__ == "__main__":
    unittest.main()