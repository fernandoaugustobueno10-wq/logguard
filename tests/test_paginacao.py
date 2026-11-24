
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from logguard.analisador import Alerta
from logguard.repositorio import RepositorioAlertas


class TestPaginacao(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.repo = RepositorioAlertas(
            Path(self.temp.name)
            / "dados"
            / "teste.sqlite3"
        )

        self.inicio = datetime(
            2026,
            11,
            20,
            12,
            tzinfo=timezone.utc,
        )

        self.alertas = [
            Alerta(
                ip="192.0.2.10",
                quantidade=5,
                inicio=self.inicio + timedelta(days=i),
                fim=self.inicio + timedelta(
                    days=i,
                    minutes=4,
                ),
            )
            for i in range(5)
        ]

        self.repo.salvar(self.alertas)

    def test_paginas(self) -> None:
        primeira = self.repo.consultar_pagina(
            pagina=1,
            tamanho_pagina=2,
        )

        self.assertEqual(
            (
                primeira.total,
                primeira.total_paginas,
                len(primeira.registros),
                primeira.pagina,
            ),
            (5, 3, 2, 1),
        )

        self.assertEqual(
            primeira.registros[0]["inicio"],
            self.alertas[4].inicio.isoformat(),
        )

        terceira = self.repo.consultar_pagina(
            pagina=3,
            tamanho_pagina=2,
        )

        self.assertEqual(
            terceira.registros[0]["inicio"],
            self.alertas[0].inicio.isoformat(),
        )

        quarta = self.repo.consultar_pagina(
            pagina=4,
            tamanho_pagina=2,
        )

        self.assertEqual(
            quarta.registros,
            [],
        )

    def test_filtro_data_inclusivo(self) -> None:
        resultado = self.repo.consultar_pagina(
            data_inicio=date(2026, 11, 21),
            data_fim=date(2026, 11, 22),
        )

        self.assertEqual(
            resultado.total,
            2,
        )

    def test_filtro_ip_normaliza(self) -> None:
        resultado = self.repo.consultar_pagina(
            ip=" 192.0.2.10 "
        )

        self.assertEqual(
            resultado.total,
            5,
        )

    def test_input_invalido(self) -> None:
        entradas = [
            {"pagina": 0},
            {"pagina": True},
            {"tamanho_pagina": 101},
            {"tamanho_pagina": True},
            {"tipo": "404 OR 1=1"},
            {
                "severidade": "ALTA' OR 1=1 --"
            },
            {
                "ip": "' OR 1=1--"
            },
            {
                "data_inicio": date(2026, 11, 25),
                "data_fim": date(2026, 11, 20),
            },
        ]

        for entrada in entradas:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ValueError):
                    self.repo.consultar_pagina(
                        **entrada
                    )

    def test_tipo_severidade(self) -> None:
        alerta_http = replace(
            self.alertas[0],
            tipo="pico_http",
            status=403,
            severidade="ALTA",
        )

        self.repo.salvar([alerta_http])

        resultado = self.repo.consultar_pagina(
            tipo="pico_http",
            severidade="ALTA",
        )

        self.assertEqual(
            resultado.total,
            1,
        )

        resultado_vazio = (
            self.repo.consultar_pagina(
                severidade="ALTA",
                ip="192.0.2.50",
            )
        )

        self.assertEqual(
            resultado_vazio.total,
            0,
        )

    def test_metodo_antigo_continua_funcionando(
        self,
    ) -> None:
        registros = self.repo.listar(
            limite=2
        )

        self.assertEqual(
            len(registros),
            2,
        )

    def test_data_meia_noite(self) -> None:
        alerta = Alerta(
            ip="192.0.2.99",
            quantidade=5,
            inicio=datetime(
                2026,
                11,
                21,
                tzinfo=timezone.utc,
            ),
            fim=datetime(
                2026,
                11,
                21,
                tzinfo=timezone.utc,
            ),
        )

        self.repo.salvar([alerta])

        resultado = self.repo.consultar_pagina(
            data_inicio=date(2026, 11, 21),
            data_fim=date(2026, 11, 21),
        )

        self.assertEqual(
            resultado.total,
            2,
        )


if __name__ == "__main__":
    unittest.main()
