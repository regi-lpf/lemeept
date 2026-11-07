import json
from pathlib import Path
import tempfile
import unittest

from pipeline.downloader import executar


class RespostaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def raise_for_status(self):
        return None

    def iter_content(self, tamanho):
        yield b"%PDF-1.7\nconteudo"


class SessaoFalsa:
    def __init__(self):
        self.urls = []

    def get(self, url, **_):
        self.urls.append(url)
        return RespostaFalsa()


class DownloaderTests(unittest.TestCase):
    def test_baixa_por_id_e_reaproveita_pdf_valido(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            entrada = raiz / "indice.json"
            saida = raiz / "pdf"
            entrada.write_text(
                json.dumps(
                    [
                        {
                            "id": "EPT-0001",
                            "linkPdf": "https://profept.ifc.edu.br/dissertacao.pdf",
                            "linkProduto": "http://educapes.capes.gov.br/handle/capes/123",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            sessao = SessaoFalsa()

            primeiro = executar(entrada, saida, sessao=sessao)
            segundo = executar(entrada, saida, sessao=sessao)

            self.assertEqual(primeiro, {"baixados": 1, "existentes": 0})
            self.assertEqual(segundo, {"baixados": 0, "existentes": 1})
            self.assertEqual(sessao.urls, ["https://profept.ifc.edu.br/dissertacao.pdf"])
            self.assertTrue((saida / "EPT-0001.pdf").read_bytes().startswith(b"%PDF-"))
            manifesto = json.loads((saida / "manifesto.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifesto["dissertacoes"][0]["link_educapes"],
                "http://educapes.capes.gov.br/handle/capes/123",
            )

    def test_rejeita_host_fora_da_fonte_oficial(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            entrada = raiz / "indice.json"
            entrada.write_text(
                json.dumps(
                    [
                        {"id": "EPT-0001", "linkPdf": "https://example.org/dissertacao.pdf"}
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Link PDF inválido"):
                executar(entrada, raiz / "pdf", sessao=SessaoFalsa())


if __name__ == "__main__":
    unittest.main()