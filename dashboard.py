
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from logguard.analisador import (
    ArquivoInvalido,
    detectar_falhas,
    detectar_picos_http,
    ler_eventos,
)
from logguard.painel import (
    calcular_indicadores,
    dados_evolucao,
    dados_severidade,
    dados_tabela,
    filtrar_alertas,
)
from logguard.repositorio import (
    ErroRepositorio,
    RepositorioAlertas,
)


BANCO = Path(__file__).resolve().parent / (
    "dados/logguard.sqlite3"
)

MAX_BYTES = 5 * 1024 * 1024
LIMITE_HISTORICO = 1000


def analisar_upload(arquivo) -> tuple[int, int, int]:
    conteudo = arquivo.getvalue()

    if not conteudo:
        raise ArquivoInvalido(
            "O arquivo CSV está vazio."
        )

    if len(conteudo) > MAX_BYTES:
        raise ArquivoInvalido(
            "O arquivo ultrapassa 5 MB."
        )

    with tempfile.TemporaryDirectory(
        prefix="logguard_"
    ) as diretorio:
        caminho = Path(diretorio) / "entrada.csv"
        caminho.write_bytes(conteudo)
        eventos = ler_eventos(caminho)

    alertas = (
        detectar_falhas(eventos)
        + detectar_picos_http(eventos)
    )

    repositorio = RepositorioAlertas(BANCO)
    inseridos = repositorio.salvar(alertas)

    return (
        len(eventos),
        len(alertas),
        inseridos,
    )


def exibir_importacao() -> None:
    st.subheader("Analisar arquivo CSV")

    st.caption(
        "Importe um arquivo no formato "
        "timestamp,ip,evento,status. "
        "Limite de 5 MB."
    )

    with st.form("formulario_importacao"):
        arquivo = st.file_uploader(
            "Selecione um arquivo CSV",
            type=["csv"],
            max_upload_size=5,
            help=(
                "O processamento é feito localmente. "
                "Não utilize logs reais sem autorização."
            ),
        )

        executar = st.form_submit_button(
            "Analisar e salvar alertas",
            type="primary",
        )

    if not executar:
        return

    if arquivo is None:
        st.warning(
            "Selecione um arquivo CSV antes de analisar."
        )
        return

    try:
        eventos, alertas, inseridos = analisar_upload(
            arquivo
        )

    except (
        ArquivoInvalido,
        ErroRepositorio,
        ValueError,
    ) as exc:
        st.error(str(exc))
        return

    except OSError:
        st.error(
            "Não foi possível processar "
            "o arquivo enviado."
        )
        return

    st.success(
        "Análise concluída com sucesso."
    )

    coluna1, coluna2, coluna3 = st.columns(3)

    coluna1.metric(
        "Eventos analisados",
        eventos,
    )
    coluna2.metric(
        "Alertas detectados",
        alertas,
    )
    coluna3.metric(
        "Novos alertas salvos",
        inseridos,
    )

    if alertas > inseridos:
        st.info(
            f"{alertas - inseridos} alerta(s) "
            "já existiam no histórico."
        )


def obter_filtros(
    registros: list[dict],
) -> list[dict]:
    with st.sidebar:
        st.header("Filtros")

        severidade = st.selectbox(
            "Severidade",
            ["TODAS", "ALTA", "MEDIA", "BAIXA"],
        )

        tipo = st.selectbox(
            "Tipo de alerta",
            [
                "TODOS",
                "Falhas de login",
                "Pico HTTP",
            ],
        )

        ip = st.text_input(
            "Endereço IP",
            placeholder="Ex.: 192.0.2.10",
        )

        if registros:
            datas = [
                datetime.fromisoformat(
                    registro["inicio"]
                ).date()
                for registro in registros
            ]

            menor_data = min(datas)
            maior_data = max(datas)

            data_inicio = st.date_input(
                "Data inicial",
                value=menor_data,
            )

            data_fim = st.date_input(
                "Data final",
                value=maior_data,
            )
        else:
            data_inicio = None
            data_fim = None

        st.divider()

        st.caption(
            "Histórico local em SQLite. "
            "Horários exibidos em UTC."
        )

    mapa_tipos = {
        "TODOS": None,
        "Falhas de login": "falhas_login",
        "Pico HTTP": "pico_http",
    }

    try:
        return filtrar_alertas(
            registros,
            severidade=(
                None
                if severidade == "TODAS"
                else severidade
            ),
            tipo=mapa_tipos[tipo],
            ip=ip or None,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    except ValueError as exc:
        st.error(str(exc))
        return []


def exibir_indicadores(
    registros: list[dict],
) -> None:
    indicadores = calcular_indicadores(
        registros
    )

    colunas = st.columns(5)

    colunas[0].metric(
        "Total de alertas",
        indicadores["total"],
    )

    colunas[1].metric(
        "Alta",
        indicadores["alta"],
    )

    colunas[2].metric(
        "Média",
        indicadores["media"],
    )

    colunas[3].metric(
        "Baixa",
        indicadores["baixa"],
    )

    colunas[4].metric(
        "IPs distintos",
        indicadores["ips_unicos"],
    )


def exibir_graficos(
    registros: list[dict],
) -> None:
    esquerda, direita = st.columns(2)

    with esquerda:
        st.subheader(
            "Alertas por severidade"
        )

        st.bar_chart(
            dados_severidade(registros),
            x="Severidade",
            y="Alertas",
            sort=False,
        )

    with direita:
        st.subheader(
            "Evolução dos alertas"
        )

        st.line_chart(
            dados_evolucao(registros),
            x="Dia",
            y="Alertas",
        )


def main() -> None:
    st.set_page_config(
        page_title="LogGuard | Security Dashboard",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🛡️ LogGuard")
    st.caption(
        "Security Dashboard | "
        "Análise local de logs e alertas"
    )

    st.markdown(
        "Monitore eventos suspeitos, "
        "consulte alertas armazenados "
        "e analise novos arquivos CSV."
    )

    with st.expander(
        "Importar e analisar um CSV",
        expanded=False,
    ):
        exibir_importacao()

    st.divider()
    st.subheader("Visão geral")

    try:
        repositorio = RepositorioAlertas(
            BANCO
        )
        registros = repositorio.listar(
            limite=LIMITE_HISTORICO
        )

    except (
        ErroRepositorio,
        ValueError,
    ) as exc:
        st.error(str(exc))
        st.stop()

    if len(registros) == LIMITE_HISTORICO:
        st.warning(
            "O painel apresenta no máximo "
            "1.000 alertas recentes. "
            "Os indicadores e gráficos "
            "consideram apenas esses registros."
        )

    filtrados = obter_filtros(
        registros
    )

    exibir_indicadores(
        filtrados
    )

    if not filtrados:
        st.info(
            "Nenhum alerta encontrado para "
            "os filtros selecionados. "
            "Importe um CSV ou ajuste os filtros."
        )
        return

    st.divider()

    exibir_graficos(
        filtrados
    )

    st.divider()
    st.subheader("Histórico de alertas")

    st.dataframe(
        dados_tabela(filtrados),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Exibindo {len(filtrados)} "
        "alerta(s) após os filtros."
    )


if __name__ == "__main__":
    main()
