
import codecs
import tempfile
import unittest
from pathlib import Path

from logguard.analisador import (
    ArquivoInvalido,
    MAX_BYTES,
    MAX_EVENTOS,
    ler_eventos,
)


CABECALHO = b"timestamp,ip,evento,status\n"

LINHA_VALIDA = (
    b"2026-11-22T12:00:00Z,"
    b"192.0.2.10,login_falha,401\n"
)


class TestSegurancaCSV(unittest.TestCase):
    def setUp(self) -> None:
        self.diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.diretorio.cleanup)

        self.arquivo = (
            Path(self.diretorio.name)
            / "eventos.csv"
        )

    def gravar(self, conteudo: bytes) -> Path:
        self.arquivo.write_bytes(conteudo)
        return self.arquivo

    def test_aceita_utf8_com_bom(self) -> None:
        arquivo = self.gravar(
            codecs.BOM_UTF8
            + CABECALHO
            + LINHA_VALIDA
        )

        eventos = ler_eventos(arquivo)

        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].status, 401)

    def test_rejeita_arquivo_acima_de_5_mb(self) -> None:
        arquivo = self.gravar(
            b"x" * (MAX_BYTES + 1)
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_mais_de_20000_eventos(self) -> None:
        arquivo = self.gravar(
            CABECALHO
            + LINHA_VALIDA * (MAX_EVENTOS + 1)
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_tipo_de_evento_desconhecido(
        self,
    ) -> None:
        arquivo = self.gravar(
            CABECALHO
            + (
                b"2026-11-22T12:00:00Z,"
                b"192.0.2.10,comando_desconhecido,401\n"
            )
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_status_com_digitos_unicode(
        self,
    ) -> None:
        linha = (
            "2026-11-22T12:00:00Z,"
            "192.0.2.10,login_falha,٤٠٣\n"
        ).encode("utf-8")

        arquivo = self.gravar(
            CABECALHO + linha
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_codificacao_invalida(self) -> None:
        arquivo = self.gravar(
            CABECALHO
            + (
                b"\xff,192.0.2.10,"
                b"login_falha,401\n"
            )
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_arquivo_inexistente(self) -> None:
        caminho = (
            Path(self.diretorio.name)
            / "inexistente.csv"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(caminho)

    def test_rejeita_campo_vazio(self) -> None:
        arquivo = self.gravar(
            CABECALHO
            + (
                b"2026-11-22T12:00:00Z,"
                b",login_falha,401\n"
            )
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_aspas_csv_nao_fechadas(
        self,
    ) -> None:
        arquivo = self.gravar(
            CABECALHO
            + (
                b'"2026-11-22T12:00:00Z,'
                b"192.0.2.10,login_falha,401\n"
            )
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_aceita_endereco_ipv6_valido(self) -> None:
        arquivo = self.gravar(
            CABECALHO
            + (
                b"2026-11-22T12:00:00Z,"
                b"2001:db8::1,login_falha,401\n"
            )
        )

        eventos = ler_eventos(arquivo)

        self.assertEqual(len(eventos), 1)
        self.assertEqual(
            eventos[0].ip,
            "2001:db8::1",
        )


if __name__ == "__main__":
    unittest.main()
