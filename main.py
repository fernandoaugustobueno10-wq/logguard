
import argparse
from pathlib import Path

from logguard.analisador import (
    ArquivoInvalido,
    detectar_falhas,
    ler_eventos,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LogGuard - análise local de logs CSV"
    )

    parser.add_argument(
        "arquivo",
        type=Path,
        help="Caminho para um arquivo CSV"
    )

    args = parser.parse_args()

    try:
        eventos = ler_eventos(args.arquivo)
        alertas = detectar_falhas(eventos)
    except ArquivoInvalido as exc:
        parser.exit(2, f"Erro: {exc}\n")

    print(f"Eventos analisados: {len(eventos)}")
    print(f"IPs com alerta: {len(alertas)}")

    for alerta in alertas:
        print(
            f"[ALERTA] IP {alerta.ip}: "
            f"{alerta.quantidade} falhas entre "
            f"{alerta.inicio.isoformat()} e "
            f"{alerta.fim.isoformat()}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
