
import argparse
from pathlib import Path

from logguard.analisador import (
    Alerta,
    ArquivoInvalido,
    detectar_falhas,
    detectar_picos_http,
    ler_eventos,
)
from logguard.repositorio import (
    ErroRepositorio,
    RepositorioAlertas,
)


BANCO_PADRAO = Path("dados/logguard.sqlite3")


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


def mostrar_historico(
    repositorio: RepositorioAlertas,
    limite: int,
    severidade: str | None,
) -> None:
    registros = repositorio.listar(
        limite=limite,
        severidade=severidade,
    )

    print()
    print("=" * 46)
    print("           LogGuard - Histórico")
    print("=" * 46)
    print(f"Alertas encontrados: {len(registros)}")
    print()

    if not registros:
        print(
            "Nenhum alerta armazenado "
            "para os filtros informados."
        )
        return

    for registro in registros:
        descricao = (
            "Falhas repetidas de login"
            if registro["tipo"] == "falhas_login"
            else (
                "Pico de respostas HTTP "
                f"{registro['status']}"
            )
        )

        print(
            f"[{registro['severidade']}] "
            f"{descricao}"
        )
        print(f"  IP: {registro['ip']}")
        print(
            f"  Eventos: "
            f"{registro['quantidade']}"
        )
        print(f"  Início: {registro['inicio']}")
        print(f"  Fim: {registro['fim']}")
        print(
            f"  Registrado em: "
            f"{registro['registrado_em']}"
        )
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
        nargs="?",
        type=Path,
        help="Caminho para um arquivo CSV",
    )

    operacoes = parser.add_mutually_exclusive_group()

    operacoes.add_argument(
        "--salvar",
        action="store_true",
        help="Gravar os alertas no SQLite local",
    )

    operacoes.add_argument(
        "--historico",
        action="store_true",
        help="Consultar alertas armazenados",
    )

    parser.add_argument(
        "--banco",
        type=Path,
        default=BANCO_PADRAO,
        help=(
            "Caminho do SQLite local "
            "(padrão: dados/logguard.sqlite3)"
        ),
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=20,
        help="Máximo de alertas exibidos no histórico",
    )

    parser.add_argument(
        "--severidade",
        choices=("BAIXA", "MEDIA", "ALTA"),
        help="Filtrar histórico por severidade",
    )

    args = parser.parse_args()

    if args.historico and args.arquivo is not None:
        parser.error(
            "Não informe um CSV ao usar --historico."
        )

    if not args.historico and args.arquivo is None:
        parser.error(
            "Informe um CSV ou utilize --historico."
        )

    if not args.historico and args.severidade is not None:
        parser.error(
            "--severidade exige --historico."
        )

    if (
        isinstance(args.limite, bool)
        or not 1 <= args.limite <= 1000
    ):
        parser.error(
            "--limite deve estar entre 1 e 1000."
        )

    try:
        if args.historico:
            repositorio = RepositorioAlertas(
                args.banco
            )

            mostrar_historico(
                repositorio,
                args.limite,
                args.severidade,
            )

            return 0

        eventos = ler_eventos(
            args.arquivo
        )

        alertas_login = detectar_falhas(
            eventos
        )

        alertas_http = detectar_picos_http(
            eventos
        )

        todos_alertas = sorted(
            alertas_login + alertas_http,
            key=lambda alerta: (
                alerta.inicio,
                alerta.ip,
                alerta.tipo,
            ),
        )

        print()
        print("=" * 46)
        print("                 LogGuard")
        print("       Analisador de Segurança")
        print("=" * 46)
        print()

        print(f"Eventos analisados: {len(eventos)}")
        print(
            f"Alertas de login: "
            f"{len(alertas_login)}"
        )
        print(
            f"Alertas HTTP: "
            f"{len(alertas_http)}"
        )
        print(
            f"Total de alertas: "
            f"{len(todos_alertas)}"
        )
        print()

        if not todos_alertas:
            print(
                "Nenhum comportamento suspeito "
                "identificado pelas regras atuais."
            )
        else:
            print("-" * 46)
            print("ALERTAS IDENTIFICADOS")
            print("-" * 46)
            print()

            for alerta in todos_alertas:
                exibir_alerta(alerta)

        if args.salvar:
            repositorio = RepositorioAlertas(
                args.banco
            )

            inseridos = repositorio.salvar(
                todos_alertas
            )

            duplicados = (
                len(todos_alertas) - inseridos
            )

            print(
                f"Novos alertas armazenados: "
                f"{inseridos}"
            )
            print(
                f"Alertas já existentes: "
                f"{duplicados}"
            )
            print(
                f"Banco local: "
                f"{repositorio.caminho}"
            )

        return 0

    except (
        ArquivoInvalido,
        ErroRepositorio,
        ValueError,
    ) as exc:
        print(
            f"Erro: {exc}",
            file=__import__("sys").stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
