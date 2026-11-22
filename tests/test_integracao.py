
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from dashboard import MAX_BYTES, analisar_upload
from logguard.analisador import ArquivoInvalido
from logguard.repositorio import RepositorioAlertas


class TestIntegracao(unittest.TestCase):
    def setUp(self) -> None:
        self.diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.diretorio.cleanup)

        self.banco = (
            Path(self.diretorio.name)
            / "dados"
            / "teste.sqlite3"
        )

    def criar_csv(self, linhas: list[str]) -> bytes:
        conteudo = (
            "timestamp,ip,evento,status\n"
            + "".join(linhas)
        )

        return conteudo.encode("utf-8")

    def criar_falhas(
        self,
        quantidade: int = 5,
    ) -> bytes:
        linhas = [
            (
                f"2026-11-22T12:{indice:02d}:00Z,"
                "192.0.2.10,login_falha,401\n"
            )
            for indice in range(quantidade)
        ]

        return self.criar_csv(linhas)

    def criar_erros_http(self) -> bytes:
        linhas = [
            (
                f"2026-11-22T13:00:{indice * 10:02d}Z,"
                "192.0.2.50,requisicao,403\n"
            )
            for indice in range(5)
        ]

        return self.criar_csv(linhas)

    def processar(
        self,
        conteudo: bytes,
    ) -> tuple[int, int, int]:
        with patch(
            "dashboard.BANCO",
            self.banco,
        ):
            return analisar_upload(
                BytesIO(conteudo)
            )

    def listar_alertas(self) -> list[dict]:
        return RepositorioAlertas(
            self.banco
        ).listar()

    def test_importa_falhas_login_e_salva(self) -> None:
        resultado = self.processar(
            self.criar_falhas()
        )

        self.assertEqual(
            resultado,
            (5, 1, 1),
        )

        registros = self.listar_alertas()

        self.assertEqual(len(registros), 1)
        self.assertEqual(
            registros[0]["tipo"],
            "falhas_login",
        )
        self.assertEqual(
            registros[0]["ip"],
            "192.0.2.10",
        )
        self.assertEqual(
            registros[0]["severidade"],
            "MEDIA",
        )

    def test_importa_erros_http_e_salva(self) -> None:
        resultado = self.processar(
            self.criar_erros_http()
        )

        self.assertEqual(
            resultado,
            (5, 1, 1),
        )

        registros = self.listar_alertas()

        self.assertEqual(len(registros), 1)
        self.assertEqual(
            registros[0]["tipo"],
            "pico_http",
        )
        self.assertEqual(
            registros[0]["status"],
            403,
        )
        self.assertEqual(
            registros[0]["severidade"],
            "ALTA",
        )

    def test_nao_duplica_alerta_reimportado(self) -> None:
        conteudo = self.criar_falhas()

        primeira = self.processar(conteudo)
        segunda = self.processar(conteudo)

        self.assertEqual(
            primeira,
            (5, 1, 1),
        )
        self.assertEqual(
            segunda,
            (5, 1, 0),
        )
        self.assertEqual(
            len(self.listar_alertas()),
            1,
        )

    def test_importa_dois_tipos_de_alerta(self) -> None:
        linhas_login = [
            (
                f"2026-11-22T12:{indice:02d}:00Z,"
                "192.0.2.10,login_falha,401\n"
            )
            for indice in range(5)
        ]

        linhas_http = [
            (
                f"2026-11-22T13:00:{indice * 10:02d}Z,"
                "192.0.2.50,requisicao,403\n"
            )
            for indice in range(5)
        ]

        resultado = self.processar(
            self.criar_csv(
                linhas_login + linhas_http
            )
        )

        self.assertEqual(
            resultado,
            (10, 2, 2),
        )

        tipos = {
            registro["tipo"]
            for registro in self.listar_alertas()
        }

        self.assertEqual(
            tipos,
            {"falhas_login", "pico_http"},
        )

    def test_nao_cria_alerta_sem_limite_minimo(
        self,
    ) -> None:
        resultado = self.processar(
            self.criar_falhas(4)
        )

        self.assertEqual(
            resultado,
            (4, 0, 0),
        )
        self.assertEqual(
            self.listar_alertas(),
            [],
        )

    def test_rejeita_cabecalho_invalido(self) -> None:
        conteudo = (
            b"timestamp,ip,evento\n"
            b"2026-11-22T12:00:00Z,"
            b"192.0.2.10,login_falha\n"
        )

        with self.assertRaises(ArquivoInvalido):
            self.processar(conteudo)

        self.assertFalse(
            self.banco.exists()
        )

    def test_rejeita_ip_invalido(self) -> None:
        conteudo = self.criar_csv([
            (
                "2026-11-22T12:00:00Z,"
                "IP_INVALIDO,login_falha,401\n"
            )
        ])

        with self.assertRaises(ArquivoInvalido):
            self.processar(conteudo)

        self.assertFalse(
            self.banco.exists()
        )

    def test_rejeita_upload_vazio(self) -> None:
        with self.assertRaises(ArquivoInvalido):
            self.processar(b"")

        self.assertFalse(
            self.banco.exists()
        )

    def test_rejeita_upload_acima_de_5mb(self) -> None:
        conteudo = b"x" * (MAX_BYTES + 1)

        with self.assertRaises(ArquivoInvalido):
            self.processar(conteudo)

        self.assertFalse(
            self.banco.exists()
        )

    def test_normaliza_fuso_horario_para_utc(
        self,
    ) -> None:
        linhas = [
            (
                f"2026-11-22T12:{indice:02d}:00+03:00,"
                "192.0.2.10,login_falha,401\n"
            )
            for indice in range(5)
        ]

        resultado = self.processar(
            self.criar_csv(linhas)
        )

        self.assertEqual(
            resultado,
            (5, 1, 1),
        )

        registro = self.listar_alertas()[0]

        self.assertEqual(
            registro["inicio"],
            "2026-11-22T09:00:00+00:00",
        )
        self.assertEqual(
            registro["fim"],
            "2026-11-22T09:04:00+00:00",
        )

    def test_rejeita_csv_com_codificacao_invalida(
        self,
    ) -> None:
        conteudo = (
            b"timestamp,ip,evento,status\n"
            b"\xff,192.0.2.10,login_falha,401\n"
        )

        with self.assertRaises(ArquivoInvalido):
            self.processar(conteudo)

        self.assertFalse(
            self.banco.exists()
        )


if __name__ == "__main__":
    unittest.main()
