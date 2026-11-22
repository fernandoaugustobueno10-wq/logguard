
import csv
import ipaddress
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


MAX_BYTES = 5 * 1024 * 1024
MAX_EVENTOS = 20000

COLUNAS = {"timestamp", "ip", "evento", "status"}


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


class ArquivoInvalido(ValueError):
    pass


def ler_eventos(caminho: Path) -> list[Evento]:
    if not caminho.is_file():
        raise ArquivoInvalido("Arquivo CSV não encontrado.")

    if caminho.stat().st_size > MAX_BYTES:
        raise ArquivoInvalido(
            "Arquivo ultrapassa o limite de 5 MB."
        )

    eventos: list[Evento] = []

    try:
        with caminho.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as arquivo:
            leitor = csv.DictReader(arquivo, strict=True)

            if (
                leitor.fieldnames is None
                or len(leitor.fieldnames) != len(COLUNAS)
                or set(leitor.fieldnames) != COLUNAS
            ):
                raise ArquivoInvalido(
                    "Colunas exigidas: timestamp,ip,evento,status."
                )

            for numero, linha in enumerate(leitor, start=2):
                if len(eventos) >= MAX_EVENTOS:
                    raise ArquivoInvalido(
                        "Arquivo ultrapassa o limite de 20.000 eventos."
                    )

                try:
                    valores = [linha[chave] for chave in COLUNAS]

                    if any(
                        valor is None or len(valor) > 128
                        for valor in valores
                    ):
                        raise ValueError(
                            "Campo ausente ou muito longo"
                        )

                    instante = datetime.fromisoformat(
                        linha["timestamp"].replace(
                            "Z", "+00:00"
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
                        ipaddress.ip_address(linha["ip"])
                    )

                    evento = linha["evento"]

                    if evento not in {
                        "login_falha",
                        "login_sucesso",
                        "requisicao"
                    }:
                        raise ValueError(
                            "Evento desconhecido"
                        )

                    status = int(linha["status"])

                    if not 100 <= status <= 599:
                        raise ValueError(
                            "Status HTTP inválido"
                        )

                    eventos.append(
                        Evento(
                            instante.astimezone(timezone.utc),
                            ip,
                            evento,
                            status
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                    OverflowError
                ) as exc:
                    raise ArquivoInvalido(
                        f"Linha {numero} inválida."
                    ) from exc

    except (
        UnicodeError,
        csv.Error,
        OSError
    ) as exc:
        raise ArquivoInvalido(
            "Não foi possível ler o arquivo CSV."
        ) from exc

    return eventos


def detectar_falhas(
    eventos: list[Evento],
    minimo: int = 5,
    janela_minutos: int = 10
) -> list[Alerta]:
    if minimo < 2 or janela_minutos < 1:
        raise ValueError(
            "Parâmetros de detecção inválidos."
        )

    janelas: dict[str, deque[datetime]] = {}
    alertas: list[Alerta] = []

    delta = timedelta(minutes=janela_minutos)
    ips_alertados: set[str] = set()

    for evento in sorted(
        eventos,
        key=lambda item: item.instante
    ):
        if (
            evento.evento != "login_falha"
            or evento.status not in {401, 403}
        ):
            continue

        fila = janelas.setdefault(
            evento.ip,
            deque()
        )

        while fila and evento.instante - fila[0] > delta:
            fila.popleft()

        fila.append(evento.instante)

        if (
            len(fila) >= minimo
            and evento.ip not in ips_alertados
        ):
            alertas.append(
                Alerta(
                    evento.ip,
                    len(fila),
                    fila[0],
                    evento.instante
                )
            )

            ips_alertados.add(evento.ip)

    return alertas
