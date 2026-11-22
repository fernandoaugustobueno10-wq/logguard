
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from logguard.analisador import Alerta
from logguard.repositorio import (
    ErroRepositorio,
    RepositorioAlertas,
)


class TestRepositorio(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.banco = (
            Path(self.temp.name)
            / "subpasta"
            / "historico.sqlite3"
        )

        self.repo = RepositorioAlertas(
            self.banco
        )

        self.inicio = datetime(
            2026,
            11,
            22,
            12,
            tzinfo=timezone.utc,
        )

        self.alerta = Alerta(
            ip="192.0.2.10",
            quantidade=5,
            inicio=self.inicio,
            fim=self.inicio + timedelta(minutes=4),
            tipo="falhas_login",
            severidade="MEDIA",
        )

    def test_cria_banco_e_insere_alerta(self) -> None:
        inseridos = self.repo.salvar(
            [self.alerta]
        )

        self.assertEqual(inseridos, 1)
        self.assertTrue(
            self.banco.is_file()
        )

        registros = self.repo.listar()

        self.assertEqual(
            registros[0]["ip"],
            "192.0.2.10",
        )

    def test_reprocessamento_nao_duplica(self) -> None:
        self.assertEqual(
            self.repo.salvar([self.alerta]),
            1,
        )

        self.assertEqual(
            self.repo.salvar([self.alerta]),
            0,
        )

        self.assertEqual(
            len(self.repo.listar()),
            1,
        )

    def test_duas_analises_distintas(self) -> None:
        outro = replace(
            self.alerta,
            inicio=self.inicio + timedelta(hours=1),
            fim=self.inicio + timedelta(
                hours=1,
                minutes=4,
            ),
        )

        inseridos = self.repo.salvar(
            [self.alerta, outro]
        )

        self.assertEqual(inseridos, 2)

        self.assertEqual(
            len(self.repo.listar()),
            2,
        )

    def test_status_http_e_filtro(self) -> None:
        alerta_http = replace(
            self.alerta,
            tipo="pico_http",
            status=403,
            severidade="ALTA",
        )

        self.repo.salvar(
            [self.alerta, alerta_http]
        )

        registros = self.repo.listar(
            severidade="ALTA"
        )

        self.assertEqual(
            len(registros),
            1,
        )

        self.assertEqual(
            registros[0]["status"],
            403,
        )

    def test_consulta_em_banco_vazio(self) -> None:
        self.assertEqual(
            self.repo.listar(),
            [],
        )

    def test_limite(self) -> None:
        segundo = replace(
            self.alerta,
            fim=self.inicio + timedelta(minutes=2),
        )

        self.repo.salvar(
            [self.alerta, segundo]
        )

        self.assertEqual(
            len(self.repo.listar(limite=1)),
            1,
        )

        for limite in (0, -1, 1001, True):
            with self.subTest(limite=limite):
                with self.assertRaises(ValueError):
                    self.repo.listar(
                        limite=limite
                    )

    def test_severidade_invalida(self) -> None:
        with self.assertRaises(ValueError):
            self.repo.listar(
                severidade="ALTA' OR 1=1 --"
            )

    def test_alerta_invalido_nao_grava_parcialmente(
        self,
    ) -> None:
        invalido = replace(
            self.alerta,
            ip="IP_INVALIDO",
        )

        with self.assertRaises(ValueError):
            self.repo.salvar(
                [self.alerta, invalido]
            )

        self.assertFalse(
            self.banco.exists()
        )

    def test_nao_aceita_pasta_como_banco(self) -> None:
        with self.assertRaises(ErroRepositorio):
            RepositorioAlertas(
                Path(self.temp.name)
            )

    def test_status_nulo_salvo(self) -> None:
        self.repo.salvar(
            [self.alerta]
        )

        self.assertIsNone(
            self.repo.listar()[0]["status"]
        )


if __name__ == "__main__":
    unittest.main()
