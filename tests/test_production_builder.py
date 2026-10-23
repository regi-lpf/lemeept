import unittest

from lemeept.pipeline.production_builder import build_production_dataset


class TestProductionBuilder(unittest.TestCase):
    def test_splits_defense_into_independent_linked_productions(self):
        dataset = build_production_dataset([{
            "id": "EPT-0108",
            "ano": "2026",
            "autor": "Ana Exemplo",
            "orientador": "Prof. Exemplo",
            "orientadorChave": "exemplo",
            "titulo": "Dissertação de exemplo",
            "produto": "Guia de exemplo",
            "linkPdf": "https://example.org/dissertacao.pdf",
            "linkProduto": "https://educapes.capes.gov.br/handle/capes/123",
            "codigoMacroprojeto": "MP3",
            "macroprojeto": "Macroprojeto 3 – Práticas Educativas no Currículo Integrado",
            "linhaPesquisa": "Linha antiga",
            "tipoProduto": "Guia",
            "metadadosEduCAPES": {"campos_dc": {"dc.subject": ["EPT"]}, "colecoes": ["Livros digitais"]},
        }], generated_at="2026-10-23T00:00:00Z")
        self.assertEqual("2.0", dataset["schemaVersion"])
        self.assertEqual(1, len(dataset["defesas"]))
        self.assertEqual(2, len(dataset["producoes"]))
        dissertation, product = dataset["producoes"]
        self.assertEqual(["EPT-0108-DIS", "EPT-0108-PRO"], [dissertation["id"], product["id"]])
        self.assertEqual({"EPT-0108"}, {item["defesaId"] for item in dataset["producoes"]})
        self.assertEqual("dissertacao", dissertation["tipo"])
        self.assertEqual("produto_educacional", product["tipo"])
        self.assertEqual("MP3", dataset["defesas"][0]["macroprojeto"]["codigo"])
        self.assertTrue(dataset["defesas"][0]["linhaPesquisa"]["nome"].startswith("Práticas Educativas"))
        self.assertEqual("Guia", product["metadados"]["tipoProduto"]["nome"])
        self.assertEqual(["Livros digitais"], product["metadados"]["colecaoEduCAPES"])
        self.assertIsNone(dissertation["metadados"]["resumo"])
        self.assertEqual("pendente", dissertation["estadoEnriquecimento"])

    def test_attaches_pdf_fields_and_page_evidence(self):
        record = {
            "id": "EPT-0002", "titulo": "Dissertação", "produto": "Guia",
            "linkPdf": "https://example.org/d.pdf", "linkProduto": "https://example.org/p",
        }
        extraction = {
            "resumo": "Resumo extraído do PDF.",
            "palavrasChave": ["EPT", "currículo"],
            "evidenciasCampos": {"resumo": [{"pagina": 3, "metodo": "texto_pdf", "trecho": "Resumo extraído"}]},
        }
        dataset = build_production_dataset([record], extractions={"EPT-0002": extraction})
        dissertation = dataset["producoes"][0]
        self.assertEqual("Resumo extraído do PDF.", dissertation["metadados"]["resumo"])
        self.assertEqual(["EPT", "currículo"], dissertation["metadados"]["palavrasChave"])
        self.assertEqual(3, dissertation["fontes"][0]["evidencias"]["resumo"][0]["pagina"])
        self.assertEqual("parcial", dissertation["estadoEnriquecimento"])
        self.assertIn("resumo extraido do pdf", dissertation["buscaTexto"])

    def test_rejects_duplicate_defense_ids(self):
        record = {"id": "EPT-0001", "titulo": "D", "linkPdf": "https://x/d", "produto": "P", "linkProduto": "https://x/p"}
        with self.assertRaisesRegex(ValueError, "duplicado"):
            build_production_dataset([record, record])

    def test_rejects_missing_production_url(self):
        record = {"id": "EPT-0001", "titulo": "D", "linkPdf": "https://x/d", "produto": "P"}
        with self.assertRaisesRegex(ValueError, "título e URL"):
            build_production_dataset([record])


if __name__ == "__main__":
    unittest.main()
