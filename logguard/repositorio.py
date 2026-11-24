
import hashlib
import ipaddress
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path

from logguard.analisador import Alerta


SEVERIDADES = frozenset({"BAIXA", "MEDIA", "ALTA"})
TIPOS = frozenset({"falhas_login", "pico_http"})


class ErroRepositorio(Exception):
    pass


@dataclass(frozen=True)
class PaginaAlertas:
    registros: list[dict]
    total: int
    pagina: int
    tamanho_pagina: int
    total_paginas: int


class RepositorioAlertas:
    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho).expanduser()

        if self.caminho.exists() and not self.caminho.is_file():
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

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_alertas_severidade_inicio
            ON alertas(severidade, inicio DESC)
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_alertas_tipo_inicio
            ON alertas(tipo, inicio DESC)
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_alertas_ip_inicio
            ON alertas(ip, inicio DESC)
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
            raise ValueError(
                "Data inválida."
            )

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

    @staticmethod
    def _filtros_paginacao(
        severidade: str | None,
        tipo: str | None,
        ip: str | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> tuple[str, list[str]]:
        condicoes = []
        valores = []

        if severidade is not None:
            if severidade not in SEVERIDADES:
                raise ValueError(
                    "Severidade inválida."
                )

            condicoes.append(
                "severidade = ?"
            )
            valores.append(severidade)

        if tipo is not None:
            if tipo not in TIPOS:
                raise ValueError(
                    "Tipo de alerta inválido."
                )

            condicoes.append(
                "tipo = ?"
            )
            valores.append(tipo)

        if ip is not None:
            if not isinstance(ip, str):
                raise ValueError(
                    "Endereço IP inválido."
                )

            if ip.strip():
                try:
                    ip_normalizado = str(
                        ipaddress.ip_address(
                            ip.strip()
                        )
                    )
                except ValueError as exc:
                    raise ValueError(
                        "Endereço IP inválido."
                    ) from exc

                condicoes.append(
                    "ip = ?"
                )
                valores.append(ip_normalizado)

        for valor in (data_inicio, data_fim):
            if (
                valor is not None
                and type(valor) is not date
            ):
                raise ValueError(
                    "Informe datas válidas."
                )

        if (
            data_inicio is not None
            and data_fim is not None
            and data_inicio > data_fim
        ):
            raise ValueError(
                "A data inicial não pode ser "
                "posterior à final."
            )

        if data_inicio is not None:
            condicoes.append(
                "inicio >= ?"
            )
            valores.append(
                datetime.combine(
                    data_inicio,
                    time.min,
                    tzinfo=timezone.utc,
                ).isoformat()
            )

        if data_fim is not None:
            condicoes.append(
                "inicio <= ?"
            )
            valores.append(
                datetime.combine(
                    data_fim,
                    time.max,
                    tzinfo=timezone.utc,
                ).isoformat()
            )

        return (
            " AND ".join(condicoes)
            if condicoes
            else "1 = 1",
            valores,
        )

    def consultar_pagina(
        self,
        pagina: int = 1,
        tamanho_pagina: int = 20,
        severidade: str | None = None,
        tipo: str | None = None,
        ip: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> PaginaAlertas:
        if (
            isinstance(pagina, bool)
            or not isinstance(pagina, int)
            or not 1 <= pagina <= 1_000_000
        ):
            raise ValueError(
                "A página deve estar entre "
                "1 e 1.000.000."
            )

        if (
            isinstance(tamanho_pagina, bool)
            or not isinstance(tamanho_pagina, int)
            or not 1 <= tamanho_pagina <= 100
        ):
            raise ValueError(
                "O tamanho da página deve "
                "estar entre 1 e 100."
            )

        filtro_sql, parametros = (
            self._filtros_paginacao(
                severidade,
                tipo,
                ip,
                data_inicio,
                data_fim,
            )
        )

        deslocamento = (
            (pagina - 1) * tamanho_pagina
        )

        try:
            with closing(
                self._conectar()
            ) as conexao:
                with conexao:
                    self._criar_tabela(conexao)

                    total = conexao.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM alertas
                        WHERE {filtro_sql}
                        """,
                        parametros,
                    ).fetchone()[0]

                    linhas = conexao.execute(
                        f"""
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
                        WHERE {filtro_sql}
                        ORDER BY
                            inicio DESC,
                            chave ASC
                        LIMIT ? OFFSET ?
                        """,
                        [
                            *parametros,
                            tamanho_pagina,
                            deslocamento,
                        ],
                    ).fetchall()

                return PaginaAlertas(
                    registros=[
                        dict(linha)
                        for linha in linhas
                    ],
                    total=total,
                    pagina=pagina,
                    tamanho_pagina=tamanho_pagina,
                    total_paginas=(
                        total + tamanho_pagina - 1
                    ) // tamanho_pagina,
                )

        except sqlite3.Error as exc:
            raise ErroRepositorio(
                "Falha ao consultar "
                "o histórico local."
            ) from exc
