
import ipaddress
from collections import Counter
from datetime import date, datetime


SEVERIDADES = ("ALTA", "MEDIA", "BAIXA")


def filtrar_alertas(
    registros: list[dict],
    severidade: str | None = None,
    tipo: str | None = None,
    ip: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[dict]:
    if (
        data_inicio is not None
        and data_fim is not None
        and data_inicio > data_fim
    ):
        raise ValueError(
            "A data inicial não pode ser posterior "
            "à data final."
        )

    ip_normalizado = None

    if ip:
        try:
            ip_normalizado = str(
                ipaddress.ip_address(ip.strip())
            )
        except ValueError as exc:
            raise ValueError(
                "Informe um endereço IP válido."
            ) from exc

    resultado = []

    for registro in registros:
        if (
            severidade is not None
            and registro["severidade"] != severidade
        ):
            continue

        if (
            tipo is not None
            and registro["tipo"] != tipo
        ):
            continue

        if (
            ip_normalizado is not None
            and registro["ip"] != ip_normalizado
        ):
            continue

        dia = datetime.fromisoformat(
            registro["inicio"]
        ).date()

        if data_inicio is not None and dia < data_inicio:
            continue

        if data_fim is not None and dia > data_fim:
            continue

        resultado.append(registro)

    return resultado


def calcular_indicadores(
    registros: list[dict],
) -> dict[str, int]:
    contagem = Counter(
        registro["severidade"]
        for registro in registros
    )

    return {
        "total": len(registros),
        "alta": contagem["ALTA"],
        "media": contagem["MEDIA"],
        "baixa": contagem["BAIXA"],
        "ips_unicos": len({
            registro["ip"]
            for registro in registros
        }),
    }


def dados_severidade(
    registros: list[dict],
) -> list[dict]:
    indicadores = calcular_indicadores(registros)

    return [
        {
            "Severidade": "ALTA",
            "Alertas": indicadores["alta"],
        },
        {
            "Severidade": "MEDIA",
            "Alertas": indicadores["media"],
        },
        {
            "Severidade": "BAIXA",
            "Alertas": indicadores["baixa"],
        },
    ]


def dados_evolucao(
    registros: list[dict],
) -> list[dict]:
    contagem = Counter(
        datetime.fromisoformat(
            registro["inicio"]
        ).date().isoformat()
        for registro in registros
    )

    return [
        {
            "Dia": dia,
            "Alertas": quantidade,
        }
        for dia, quantidade in sorted(
            contagem.items()
        )
    ]


def dados_tabela(
    registros: list[dict],
) -> list[dict]:
    return [
        {
            "Severidade": registro["severidade"],
            "Tipo": (
                "Falhas de login"
                if registro["tipo"] == "falhas_login"
                else "Pico HTTP"
            ),
            "IP": registro["ip"],
            "HTTP": (
                registro["status"]
                if registro["status"] is not None
                else "-"
            ),
            "Eventos": registro["quantidade"],
            "Início (UTC)": registro["inicio"],
            "Fim (UTC)": registro["fim"],
        }
        for registro in registros
    ]
