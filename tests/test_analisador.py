
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from logguard.analisador import (
    Alerta,
    ArquivoInvalido,
    Evento,
    detectar_falhas,
    detectar_picos_http,
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
            encoding="utf-8",
        )
        return arquivo

    def criar_eventos(
        self,
        quantidade: int,
        tipo: str,
        status: int,
        intervalo_segundos: int = 60,
        ip: str = "192.0.2.10",
        inicio_segundos: int = 0,
    ) -> list[Evento]:
        inicio = datetime(
            2026,
            11,
            22,
            12,
            tzinfo=timezone.utc,
        ) + timedelta(
            seconds=inicio_segundos
        )

        return [
            Evento(
                instante=inicio + timedelta(
                    seconds=i * intervalo_segundos
                ),
                ip=ip,
                evento=tipo,
                status=status,
            )
            for i in range(quantidade)
        ]

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
        self.assertEqual(alertas[0].tipo, "falhas_login")
        self.assertEqual(alertas[0].severidade, "MEDIA")

    def test_nao_gera_alerta_com_quatro_falhas(self) -> None:
        eventos = self.criar_eventos(
            4,
            "login_falha",
            401,
        )

        self.assertEqual(
            detectar_falhas(eventos),
            [],
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
        eventos = self.criar_eventos(
            5,
            "login_sucesso",
            200,
        )

        self.assertEqual(
            detectar_falhas(eventos),
            [],
        )

    def test_detecta_falhas_rapidas_com_severidade_alta(self) -> None:
        eventos = self.criar_eventos(
            5,
            "login_falha",
            401,
            intervalo_segundos=20,
        )

        alertas = detectar_falhas(eventos)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].severidade, "ALTA")

    def test_detecta_dois_episodios_do_mesmo_ip(self) -> None:
        primeiro = self.criar_eventos(
            5,
            "login_falha",
            401,
        )

        segundo = self.criar_eventos(
            5,
            "login_falha",
            401,
            inicio_segundos=3600,
        )

        alertas = detectar_falhas(
            primeiro + segundo
        )

        self.assertEqual(len(alertas), 2)
        self.assertEqual(
            [alerta.quantidade for alerta in alertas],
            [5, 5],
        )

    def test_ordena_eventos_fora_de_ordem(self) -> None:
        eventos = self.criar_eventos(
            5,
            "login_falha",
            401,
        )

        alertas = detectar_falhas(
            list(reversed(eventos))
        )

        self.assertEqual(len(alertas), 1)
        self.assertEqual(
            alertas[0].inicio,
            eventos[0].instante,
        )

    def test_nao_detecta_falhas_fora_da_janela(self) -> None:
        eventos = self.criar_eventos(
            5,
            "login_falha",
            401,
            intervalo_segundos=600,
        )

        self.assertEqual(
            detectar_falhas(eventos),
            [],
        )

    def test_detecta_pico_http_401(self) -> None:
        eventos = self.criar_eventos(
            5,
            "requisicao",
            401,
            intervalo_segundos=60,
        )

        alertas = detectar_picos_http(eventos)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].status, 401)
        self.assertEqual(alertas[0].tipo, "pico_http")
        self.assertEqual(alertas[0].severidade, "MEDIA")

    def test_detecta_pico_http_403(self) -> None:
        eventos = self.criar_eventos(
            5,
            "requisicao",
            403,
            intervalo_segundos=10,
        )

        alertas = detectar_picos_http(eventos)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].status, 403)
        self.assertEqual(alertas[0].severidade, "ALTA")

    def test_detecta_pico_http_404_baixa(self) -> None:
        eventos = self.criar_eventos(
            5,
            "requisicao",
            404,
            intervalo_segundos=60,
        )

        alertas = detectar_picos_http(eventos)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].severidade, "BAIXA")

    def test_nao_mistura_status_http(self) -> None:
        eventos = (
            self.criar_eventos(
                3,
                "requisicao",
                401,
            )
            + self.criar_eventos(
                3,
                "requisicao",
                404,
            )
        )

        self.assertEqual(
            detectar_picos_http(eventos),
            [],
        )

    def test_nao_mistura_enderecos_ip(self) -> None:
        eventos = (
            self.criar_eventos(
                3,
                "login_falha",
                401,
                ip="192.0.2.10",
            )
            + self.criar_eventos(
                3,
                "login_falha",
                401,
                ip="198.51.100.20",
            )
        )

        self.assertEqual(
            detectar_falhas(eventos),
            [],
        )

    def test_ignora_http_200(self) -> None:
        eventos = self.criar_eventos(
            10,
            "requisicao",
            200,
        )

        self.assertEqual(
            detectar_picos_http(eventos),
            [],
        )

    def test_rejeita_parametros_invalidos(self) -> None:
        with self.assertRaises(ValueError):
            detectar_falhas([], minimo=1)

        with self.assertRaises(ValueError):
            detectar_picos_http(
                [],
                janela_minutos=0,
            )

    def test_rejeita_linha_csv_com_coluna_extra(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento,status\n"
            "2026-11-22T12:00:00Z,"
            "192.0.2.10,login_falha,401,extra\n"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_colunas_duplicadas(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento,status,status\n"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)

    def test_rejeita_status_http_invalido(self) -> None:
        arquivo = self.escrever_csv(
            "timestamp,ip,evento,status\n"
            "2026-11-22T12:00:00Z,"
            "192.0.2.10,requisicao,999\n"
        )

        with self.assertRaises(ArquivoInvalido):
            ler_eventos(arquivo)


if __name__ == "__main__":
    unittest.main()
