
import csv
import ipaddress
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


MAX_BYTES = 5 * 1024 * 1024
MAX_EVENTOS = 20000

COLUNAS = {"timestamp", "ip", "evento", "status"}

EVENTOS_PERMITIDOS = {
    "login_falha",
    "login_sucesso",
    "requisicao",
}

STATUS_SUSPEITOS = {401, 403, 404}


@dataclass(frozen=True)
class Evento:
    instante: datetime
    ip: str
    evento: str
    status: int


@dataclass(frozen=True)
class Alerta:
    ip: str
    quantidade: int
    inicio: datetime
    fim: datetime
    tipo: str = "falhas_login"
    severidade: str = "MEDIA"
    status: int | None = None


class ArquivoInvalido(ValueError):
    pass


def ler_eventos(caminho: Path) -> list[Evento]:
    try:
        if not caminho.is_file():
            raise ArquivoInvalido(
                "Arquivo CSV não encontrado."
            )

        if caminho.stat().st_size > MAX_BYTES:
            raise ArquivoInvalido(
                "Arquivo ultrapassa o limite de 5 MB."
            )

        eventos: list[Evento] = []

        with caminho.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as arquivo:
            leitor = csv.DictReader(
                arquivo,
                strict=True,
            )

            if (
                leitor.fieldnames is None
                or len(leitor.fieldnames) != len(COLUNAS)
                or set(leitor.fieldnames) != COLUNAS
            ):
                raise ArquivoInvalido(
                    "Colunas exigidas: "
                    "timestamp,ip,evento,status."
                )

            for numero, linha in enumerate(leitor, start=2):
                if len(eventos) >= MAX_EVENTOS:
                    raise ArquivoInvalido(
                        "Arquivo ultrapassa o limite "
                        "de 20.000 eventos."
                    )

                try:
                    if None in linha:
                        raise ValueError(
                            "Quantidade de colunas inválida"
                        )

                    valores = [
                        linha[chave]
                        for chave in COLUNAS
                    ]

                    if any(
                        valor is None
                        or not valor.strip()
                        or len(valor) > 128
                        for valor in valores
                    ):
                        raise ValueError(
                            "Campo ausente ou inválido"
                        )

                    instante = datetime.fromisoformat(
                        linha["timestamp"].replace(
                            "Z",
                            "+00:00",
                        )
                    )

                    if (
                        instante.tzinfo is None
                        or instante.utcoffset() is None
                    ):
                        raise ValueError(
                            "Data precisa ter fuso horário"
                        )

                    ip = str(
                        ipaddress.ip_address(
                            linha["ip"]
                        )
                    )

                    evento = linha["evento"]

                    if evento not in EVENTOS_PERMITIDOS:
                        raise ValueError(
                            "Evento desconhecido"
                        )

                    status_texto = linha["status"]

                    if (
                        len(status_texto) != 3
                        or not status_texto.isascii()
                        or not status_texto.isdecimal()
                    ):
                        raise ValueError(
                            "Status HTTP inválido"
                        )

                    status = int(status_texto)

                    if not 100 <= status <= 599:
                        raise ValueError(
                            "Status HTTP inválido"
                        )

                    eventos.append(
                        Evento(
                            instante=instante.astimezone(
                                timezone.utc
                            ),
                            ip=ip,
                            evento=evento,
                            status=status,
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                    OverflowError,
                    KeyError,
                ) as exc:
                    raise ArquivoInvalido(
                        f"Linha {numero} inválida."
                    ) from exc

        return eventos

    except (
        UnicodeError,
        csv.Error,
        OSError,
    ) as exc:
        raise ArquivoInvalido(
            "Não foi possível ler o arquivo CSV."
        ) from exc


def _validar_parametros(
    minimo: int,
    janela_minutos: int,
) -> None:
    if (
        isinstance(minimo, bool)
        or isinstance(janela_minutos, bool)
        or not isinstance(minimo, int)
        or not isinstance(janela_minutos, int)
        or minimo < 2
        or janela_minutos < 1
    ):
        raise ValueError(
            "Parâmetros de detecção inválidos."
        )


def _detectar_por_grupo(
    eventos: list[Evento],
    minimo: int,
    janela_minutos: int,
    selecionar: Callable[[Evento], bool],
    chave: Callable[[Evento], tuple[str, int | None]],
    tipo: str,
) -> list[Alerta]:
    _validar_parametros(
        minimo,
        janela_minutos,
    )

    delta = timedelta(
        minutes=janela_minutos
    )

    janelas: dict[
        tuple[str, int | None],
        deque[datetime],
    ] = {}

    alertas: list[Alerta] = []

    for evento in sorted(
        eventos,
        key=lambda item: item.instante,
    ):
        if not selecionar(evento):
            continue

        grupo = chave(evento)
        fila = janelas.setdefault(
            grupo,
            deque(),
        )

        while (
            fila
            and evento.instante - fila[0] > delta
        ):
            fila.popleft()

        fila.append(evento.instante)

        if len(fila) < minimo:
            continue

        inicio = fila[0]
        fim = fila[-1]
        duracao = fim - inicio

        if tipo == "falhas_login":
            severidade = (
                "ALTA"
                if duracao <= timedelta(minutes=2)
                else "MEDIA"
            )
        elif grupo[1] == 404:
            severidade = (
                "MEDIA"
                if duracao <= timedelta(minutes=1)
                else "BAIXA"
            )
        else:
            severidade = (
                "ALTA"
                if duracao <= timedelta(minutes=1)
                else "MEDIA"
            )

        alertas.append(
            Alerta(
                ip=evento.ip,
                quantidade=len(fila),
                inicio=inicio,
                fim=fim,
                tipo=tipo,
                severidade=severidade,
                status=grupo[1],
            )
        )

        # Cada evento participa de apenas um alerta.
        # Um novo grupo de eventos pode gerar outro alerta.
        fila.clear()

    return alertas


def detectar_falhas(
    eventos: list[Evento],
    minimo: int = 5,
    janela_minutos: int = 10,
) -> list[Alerta]:
    return _detectar_por_grupo(
        eventos=eventos,
        minimo=minimo,
        janela_minutos=janela_minutos,
        selecionar=lambda evento: (
            evento.evento == "login_falha"
            and evento.status in {401, 403}
        ),
        chave=lambda evento: (
            evento.ip,
            None,
        ),
        tipo="falhas_login",
    )


def detectar_picos_http(
    eventos: list[Evento],
    minimo: int = 5,
    janela_minutos: int = 5,
) -> list[Alerta]:
    return _detectar_por_grupo(
        eventos=eventos,
        minimo=minimo,
        janela_minutos=janela_minutos,
        selecionar=lambda evento: (
            evento.evento == "requisicao"
            and evento.status in STATUS_SUSPEITOS
        ),
        chave=lambda evento: (
            evento.ip,
            evento.status,
        ),
        tipo="pico_http",
    )
