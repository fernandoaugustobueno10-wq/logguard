
import argparse
from pathlib import Path

from logguard.analisador import (
    Alerta,
    ArquivoInvalido,
    detectar_falhas,
    detectar_picos_http,
    ler_eventos,
)


def exibir_alerta(alerta: Alerta) -> None:
    descricao = (
        "Falhas repetidas de login"
        if alerta.tipo == "falhas_login"
        else f"Pico de respostas HTTP {alerta.status}"
    )

    print(
        f"[{alerta.severidade}] {descricao}"
    )
    print(f"  IP: {alerta.ip}")
    print(f"  Eventos: {alerta.quantidade}")
    print(f"  Início: {alerta.inicio.isoformat()}")
    print(f"  Fim: {alerta.fim.isoformat()}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "LogGuard - Analisador local "
            "de logs de segurança"
        )
    )

    parser.add_argument(
        "arquivo",
        type=Path,
        help="Caminho para o arquivo CSV",
    )

    args = parser.parse_args()

    try:
        eventos = ler_eventos(args.arquivo)

        alertas_login = detectar_falhas(
            eventos
        )

        alertas_http = detectar_picos_http(
            eventos
        )

    except ArquivoInvalido as exc:
        parser.exit(
            2,
            f"Erro: {exc}\n",
        )

    print()
    print("=" * 46)
    print("                 LogGuard")
    print("       Analisador de Segurança")
    print("=" * 46)
    print()

    print(f"Eventos analisados: {len(eventos)}")
    print(f"Alertas de login: {len(alertas_login)}")
    print(f"Alertas HTTP: {len(alertas_http)}")

    todos_alertas = sorted(
        alertas_login + alertas_http,
        key=lambda alerta: (
            alerta.inicio,
            alerta.ip,
            alerta.tipo,
        ),
    )

    print(f"Total de alertas: {len(todos_alertas)}")
    print()

    if not todos_alertas:
        print(
            "Nenhum comportamento suspeito "
            "identificado pelas regras atuais."
        )

        return 0

    print("-" * 46)
    print("ALERTAS IDENTIFICADOS")
    print("-" * 46)
    print()

    for alerta in todos_alertas:
        exibir_alerta(alerta)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
