
import unittest
from datetime import date

from logguard.painel import (
    calcular_indicadores,
    dados_evolucao,
    dados_severidade,
    dados_tabela,
    filtrar_alertas,
)


class TestPainel(unittest.TestCase):
    def setUp(self) -> None:
        self.registros = [
            {
                "tipo": "falhas_login",
                "severidade": "ALTA",
                "ip": "192.0.2.10",
                "status": None,
                "quantidade": 5,
                "inicio": "2026-11-22T12:00:00+00:00",
                "fim": "2026-11-22T12:01:00+00:00",
                "registrado_em": "2026-11-22T12:02:00+00:00",
            },
            {
                "tipo": "pico_http",
                "severidade": "MEDIA",
                "ip": "192.0.2.20",
                "status": 403,
                "quantidade": 5,
                "inicio": "2026-11-23T13:00:00+00:00",
                "fim": "2026-11-23T13:04:00+00:00",
                "registrado_em": "2026-11-23T13:05:00+00:00",
            },
            {
                "tipo": "pico_http",
                "severidade": "BAIXA",
                "ip": "192.0.2.20",
                "status": 404,
                "quantidade": 5,
                "inicio": "2026-11-23T14:00:00+00:00",
                "fim": "2026-11-23T14:04:00+00:00",
                "registrado_em": "2026-11-23T14:05:00+00:00",
            },
        ]

    def test_calcula_indicadores(self) -> None:
        resultado = calcular_indicadores(
            self.registros
        )

        self.assertEqual(
            resultado["total"],
            3,
        )
        self.assertEqual(
            resultado["alta"],
            1,
        )
        self.assertEqual(
            resultado["media"],
            1,
        )
        self.assertEqual(
            resultado["baixa"],
            1,
        )
        self.assertEqual(
            resultado["ips_unicos"],
            2,
        )

    def test_filtra_severidade(self) -> None:
        resultado = filtrar_alertas(
            self.registros,
            severidade="ALTA",
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(
            resultado[0]["ip"],
            "192.0.2.10",
        )

    def test_filtra_tipo(self) -> None:
        resultado = filtrar_alertas(
            self.registros,
            tipo="pico_http",
        )

        self.assertEqual(len(resultado), 2)

    def test_filtra_ip(self) -> None:
        resultado = filtrar_alertas(
            self.registros,
            ip="192.0.2.20",
        )

        self.assertEqual(len(resultado), 2)

    def test_rejeita_ip_invalido(self) -> None:
        with self.assertRaises(ValueError):
            filtrar_alertas(
                self.registros,
                ip="IP_INCORRETO",
            )

    def test_filtra_periodo(self) -> None:
        resultado = filtrar_alertas(
            self.registros,
            data_inicio=date(2026, 11, 23),
            data_fim=date(2026, 11, 23),
        )

        self.assertEqual(len(resultado), 2)

    def test_rejeita_periodo_invertido(self) -> None:
        with self.assertRaises(ValueError):
            filtrar_alertas(
                self.registros,
                data_inicio=date(2026, 11, 24),
                data_fim=date(2026, 11, 22),
            )

    def test_dados_dos_graficos(self) -> None:
        severidades = dados_severidade(
            self.registros
        )

        evolucao = dados_evolucao(
            self.registros
        )

        self.assertEqual(
            len(severidades),
            3,
        )

        self.assertEqual(
            len(evolucao),
            2,
        )

        self.assertEqual(
            evolucao[1]["Alertas"],
            2,
        )

    def test_tabela(self) -> None:
        tabela = dados_tabela(
            self.registros
        )

        self.assertEqual(len(tabela), 3)

        self.assertEqual(
            tabela[0]["Tipo"],
            "Falhas de login",
        )

        self.assertEqual(
            tabela[1]["HTTP"],
            403,
        )


if __name__ == "__main__":
    unittest.main()
