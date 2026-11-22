
import hashlib
import ipaddress
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from logguard.analisador import Alerta


SEVERIDADES = frozenset({"BAIXA", "MEDIA", "ALTA"})
TIPOS = frozenset({"falhas_login", "pico_http"})


class ErroRepositorio(Exception):
    pass


class RepositorioAlertas:
    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho).expanduser()

        if (
            self.caminho.exists()
            and not self.caminho.is_file()
        ):
            raise ErroRepositorio(
                "O destino do banco não é um arquivo."
            )

    def _conectar(self) -> sqlite3.Connection:
        try:
            self.caminho.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            conexao = sqlite3.connect(
                str(self.caminho),
                timeout=5,
            )

            conexao.row_factory = sqlite3.Row
            return conexao

        except (OSError, sqlite3.Error) as exc:
            raise ErroRepositorio(
                "Não foi possível abrir o banco local."
            ) from exc

    @staticmethod
    def _criar_tabela(
        conexao: sqlite3.Connection,
    ) -> None:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS alertas (
                chave TEXT PRIMARY KEY,
                tipo TEXT NOT NULL
                    CHECK (
                        tipo IN (
                            'falhas_login',
                            'pico_http'
                        )
                    ),
                severidade TEXT NOT NULL
                    CHECK (
                        severidade IN (
                            'BAIXA',
                            'MEDIA',
                            'ALTA'
                        )
                    ),
                ip TEXT NOT NULL,
                status INTEGER,
                quantidade INTEGER NOT NULL
                    CHECK (quantidade >= 2),
                inicio TEXT NOT NULL,
                fim TEXT NOT NULL,
                registrado_em TEXT NOT NULL
            )
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_alertas_inicio
            ON alertas(inicio DESC)
            """
        )

    @staticmethod
    def _parametros(
        alerta: Alerta,
    ) -> tuple:
        if (
            alerta.tipo not in TIPOS
            or alerta.severidade not in SEVERIDADES
        ):
            raise ValueError(
                "Tipo ou severidade de alerta inválidos."
            )

        if (
            isinstance(alerta.quantidade, bool)
            or not isinstance(alerta.quantidade, int)
            or alerta.quantidade < 2
        ):
            raise ValueError(
                "Quantidade inválida."
            )

        if (
            alerta.tipo == "falhas_login"
            and alerta.status is not None
        ) or (
            alerta.tipo == "pico_http"
            and alerta.status not in {401, 403, 404}
        ):
            raise ValueError(
                "Status incompatível com o tipo do alerta."
            )

        ip = str(
            ipaddress.ip_address(alerta.ip)
        )

        if (
            not isinstance(alerta.inicio, datetime)
            or not isinstance(alerta.fim, datetime)
        ):
            raise ValueError("Data inválida.")

        if (
            alerta.inicio.tzinfo is None
            or alerta.fim.tzinfo is None
            or alerta.inicio.utcoffset() is None
            or alerta.fim.utcoffset() is None
        ):
            raise ValueError(
                "Datas precisam ter fuso horário."
            )

        inicio = alerta.inicio.astimezone(
            timezone.utc
        )

        fim = alerta.fim.astimezone(
            timezone.utc
        )

        if inicio > fim:
            raise ValueError(
                "Intervalo inválido."
            )

        dados = {
            "tipo": alerta.tipo,
            "severidade": alerta.severidade,
            "ip": ip,
            "status": alerta.status,
            "quantidade": alerta.quantidade,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        }

        conteudo = json.dumps(
            dados,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        chave = hashlib.sha256(
            conteudo
        ).hexdigest()

        registrado_em = datetime.now(
            timezone.utc
        ).isoformat()

        return (
            chave,
            dados["tipo"],
            dados["severidade"],
            dados["ip"],
            dados["status"],
            dados["quantidade"],
            dados["inicio"],
            dados["fim"],
            registrado_em,
        )

    def salvar(
        self,
        alertas: list[Alerta],
    ) -> int:
        parametros = [
            self._parametros(alerta)
            for alerta in alertas
        ]

        try:
            with closing(
                self._conectar()
            ) as conexao:
                with conexao:
                    self._criar_tabela(conexao)

                    antes = conexao.total_changes

                    conexao.executemany(
                        """
                        INSERT INTO alertas (
                            chave,
                            tipo,
                            severidade,
                            ip,
                            status,
                            quantidade,
                            inicio,
                            fim,
                            registrado_em
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(chave) DO NOTHING
                        """,
                        parametros,
                    )

                    inseridos = (
                        conexao.total_changes - antes
                    )

                return inseridos

        except sqlite3.Error as exc:
            raise ErroRepositorio(
                "Falha ao gravar alertas "
                "no banco local."
            ) from exc

    def listar(
        self,
        limite: int = 100,
        severidade: str | None = None,
    ) -> list[dict]:
        if (
            isinstance(limite, bool)
            or not isinstance(limite, int)
            or not 1 <= limite <= 1000
        ):
            raise ValueError(
                "O limite deve estar entre 1 e 1000."
            )

        if (
            severidade is not None
            and severidade not in SEVERIDADES
        ):
            raise ValueError(
                "Severidade inválida."
            )

        try:
            with closing(
                self._conectar()
            ) as conexao:
                with conexao:
                    self._criar_tabela(conexao)

                    linhas = conexao.execute(
                        """
                        SELECT
                            tipo,
                            severidade,
                            ip,
                            status,
                            quantidade,
                            inicio,
                            fim,
                            registrado_em
                        FROM alertas
                        WHERE (
                            ? IS NULL
                            OR severidade = ?
                        )
                        ORDER BY
                            inicio DESC,
                            chave ASC
                        LIMIT ?
                        """,
                        (
                            severidade,
                            severidade,
                            limite,
                        ),
                    ).fetchall()

                return [
                    dict(linha)
                    for linha in linhas
                ]

        except sqlite3.Error as exc:
            raise ErroRepositorio(
                "Falha ao consultar "
                "o histórico local."
            ) from exc
