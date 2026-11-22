
import tempfile
import unittest
from pathlib import Path

from logguard.analisador import (
    ArquivoInvalido,
    detectar_falhas,
    ler_eventos,
)


class TestAnalisador(unittest.TestCase):
    def setUp(self) -> None:
        self.diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.diretorio.cleanup)

    def escrever_csv(self, conteudo: str) -> Path:
        arquivo = Path(self.diretorio.name) / "eventos.csv"

        arquivo.write_text(
            conteudo,
            encoding="utf-8"
        )

        return arquivo

    def test_detecta_cinco_falhas_em_dez_minutos(self) -> None:
        cabecalho = "timestamp,ip,evento,status\n"

        linhas = "".join(
            f"2026-11-22T12:0{i}:00Z,"
            f"192.0.2.10,login_falha,401\n"
            for i in range(5)
        )

        eventos = ler_eventos(
            self.escrever_csv(cabecalho + linhas)
        )

        alertas = detectar_falhas(eventos)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].ip, "192.0.2.10")
        self.assertEqual(alertas[0].quantidade, 5)

    def test_nao_gera_alerta_com_quatro_falhas(self) -> None:
        cabecalho = "timestamp,ip,evento,status\n"

        linhas = "".join(
            f"2026-11-22T12:0{i}:00Z,"
            f"192.0.2.10,login_falha,401\n"
            for i in range(4)
        )

        eventos = ler_eventos(
            self.escrever_csv(cabecalho + linhas)
        )

        self.assertEqual(
            detectar_falhas(eventos),
            []
        )

    def test_rejeita_ip_invalido(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento,status\n"
            "2026-11-22T12:00:00Z,"
            "invalido,login_falha,401\n"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_timestamp_sem_fuso(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento,status\n"
            "2026-11-22T12:00:00,"
            "192.0.2.10,login_falha,401\n"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_colunas_faltando(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento\n"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_ignora_eventos_que_nao_sao_falhas(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento,status\n"
            "2026-11-22T12:00:00Z,"
            "192.0.2.10,login_sucesso,200\n"
        )

        eventos = ler_eventos(arquivo)

        self.assertEqual(
            detectar_falhas(eventos),
            []
        )


if __name__ == "__main__":
    unittest.main()
