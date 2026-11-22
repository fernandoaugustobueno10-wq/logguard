
# LogGuard

**Analisador de logs de segurança desenvolvido em Python.**

O LogGuard é um projeto pessoal criado para praticar programação em Python, processamento de arquivos, análise de eventos, identificação de comportamentos suspeitos e testes automatizados.

O objetivo é desenvolver uma ferramenta capaz de analisar registros de aplicações e identificar situações que merecem investigação, como múltiplas tentativas de autenticação malsucedidas.

O projeto é executado localmente e não necessita de hospedagem, Docker ou serviços pagos.

## Status do projeto

**Versão atual: 0.1 — Analisador inicial de autenticação**

Nesta primeira versão, o LogGuard processa arquivos CSV e identifica endereços IP que apresentam cinco ou mais falhas de login em um intervalo de dez minutos.

O projeto está em desenvolvimento. Novas regras de detecção, armazenamento de resultados e uma interface gráfica estão planejados para as próximas versões.

## Tecnologias

| Tecnologia | Utilização |
|---|---|
| Python 3.13 | Linguagem principal |
| csv | Leitura de arquivos CSV |
| ipaddress | Validação de endereços IPv4 e IPv6 |
| datetime | Processamento de datas e intervalos |
| dataclasses | Representação dos eventos e alertas |
| unittest | Testes automatizados |
| Git e GitHub | Versionamento do projeto |

A versão atual utiliza apenas bibliotecas da própria linguagem Python.

## Funcionalidades implementadas

- Leitura e processamento de arquivos CSV.
- Validação das colunas obrigatórias.
- Validação de endereços IP.
- Normalização de datas para UTC.
- Validação de códigos HTTP.
- Detecção de tentativas repetidas de login.
- Agrupamento de eventos por endereço IP.
- Identificação de alertas em janelas de tempo.
- Exibição dos resultados pelo terminal.
- Tratamento de arquivos inválidos.
- Testes automatizados.

## Regra de detecção inicial

O LogGuard identifica um possível comportamento suspeito quando um mesmo endereço IP apresenta pelo menos cinco falhas de autenticação em uma janela de dez minutos.

São considerados eventos de falha:

- `login_falha` com status HTTP `401`.
- `login_falha` com status HTTP `403`.

Quando o limite é atingido, o sistema registra um alerta contendo o endereço IP, a quantidade de falhas e os horários de início e fim da janela identificada.

Cada IP gera, no máximo, um alerta por execução nesta versão.

**Importante:** o alerta representa um indício para investigação, não a confirmação de um ataque. Falhas de autenticação também podem ocorrer por erros legítimos de usuários.

## Estrutura do projeto

```text
logguard/
|
|-- logguard/
|   |-- __init__.py
|   |-- analisador.py
|
|-- tests/
|   |-- test_analisador.py
|
|-- exemplos/
|   |-- eventos.csv
|
|-- main.py
|-- .gitignore
|-- README.md
```

## Formato dos arquivos CSV

O analisador utiliza quatro colunas obrigatórias:

| Coluna | Descrição | Exemplo |
|---|---|---|
| timestamp | Data e hora com fuso horário | 2026-11-22T12:00:00Z |
| ip | Endereço IP do evento | 192.0.2.10 |
| evento | Tipo de evento | login_falha |
| status | Código HTTP | 401 |

Exemplo:

```csv
timestamp,ip,evento,status
2026-11-22T12:00:00Z,192.0.2.10,login_falha,401
2026-11-22T12:01:00Z,192.0.2.10,login_falha,401
2026-11-22T12:02:00Z,192.0.2.10,login_falha,401
2026-11-22T12:03:00Z,192.0.2.10,login_falha,401
2026-11-22T12:04:00Z,192.0.2.10,login_falha,401
```

Os endereços IP utilizados nos exemplos são reservados para documentação e não identificam usuários reais.

Nesta versão, são aceitos os tipos de evento `login_falha`, `login_sucesso` e `requisicao`.

## Como executar

### 1. Requisitos

- Python 3.11 ou superior.
- Git, caso deseje clonar o repositório.

Não é necessário instalar bibliotecas adicionais para executar a versão inicial.

### 2. Clonar o repositório

Abra o PowerShell:

```powershell
git clone https://github.com/fernandoaugustobueno10-wq/logguard.git

cd logguard
```

### 3. Executar a análise

No Windows:

```powershell
py main.py exemplos\eventos.csv
```

Em sistemas em que o Python 3 está disponível como `python3`:

```bash
python3 main.py exemplos/eventos.csv
```

### 4. Resultado esperado

```text
Eventos analisados: 6
IPs com alerta: 1
[ALERTA] IP 192.0.2.10: 5 falhas entre 2026-11-22T12:00:00+00:00 e 2026-11-22T12:04:00+00:00
```

O resultado demonstra a identificação de cinco falhas provenientes do mesmo IP dentro da janela configurada.

### 5. Analisar outro arquivo

O usuário também pode fornecer o caminho de outro CSV compatível:

```powershell
py main.py "C:\caminho\para\eventos.csv"
```

O arquivo precisa utilizar o formato de colunas documentado anteriormente.

## Testes automatizados

O projeto utiliza o módulo `unittest` da biblioteca padrão do Python.

Para executar os testes no Windows:

```powershell
py -m unittest discover -s tests -v
```

Os seis testes iniciais verificam:

1. Detecção de cinco falhas dentro da janela.
2. Ausência de alerta para quatro falhas.
3. Rejeição de endereço IP inválido.
4. Rejeição de data sem fuso horário.
5. Rejeição de arquivo com colunas obrigatórias ausentes.
6. Desconsideração de eventos que não representam falhas.

Na primeira validação local, os resultados foram:

```text
Ran 6 tests

OK
```

A cobertura de testes será ampliada conforme novas funcionalidades forem implementadas.

## Segurança e validação

O LogGuard trata os arquivos importados como entradas não confiáveis.

A versão inicial implementa:

- Limite de 5 MB por arquivo.
- Limite de 20.000 eventos por análise.
- Validação de campos obrigatórios.
- Validação de endereços IP.
- Verificação de datas com fuso horário.
- Verificação de códigos HTTP válidos.
- Tratamento de arquivos malformados.
- Processamento sem execução de comandos presentes nos logs.

Os registros utilizados nos exemplos são fictícios.

**Cuidados:** arquivos de log reais podem conter endereços IP, identificadores e outras informações sensíveis. Não publique registros de produção no GitHub sem revisar e anonimizar os dados.

O LogGuard é uma ferramenta educacional em desenvolvimento. Não substitui soluções profissionais de monitoramento ou investigação de incidentes.

## Limitações da versão 0.1

- Suporta somente o formato CSV documentado.
- Ainda não importa diretamente logs brutos de Apache, Nginx ou Windows.
- Utiliza uma única regra de detecção.
- Não possui armazenamento persistente.
- Não possui dashboard gráfico.
- Gera no máximo um alerta por IP em cada análise.
- Não realiza monitoramento em tempo real.

Essas limitações serão trabalhadas nas próximas etapas.

## Próximas funcionalidades

- Regras adicionais de detecção de eventos suspeitos.
- Classificação de alertas por severidade.
- Identificação de picos de erros HTTP.
- Suporte a diferentes formatos de logs.
- Armazenamento de análises em SQLite.
- Dashboard interativo com Streamlit.
- Filtros e consultas por data, IP e severidade.
- Exportação de relatórios.
- Ampliação dos testes automatizados.
- Melhorias de desempenho e tratamento de arquivos grandes.

## Sobre o projeto

Desenvolvi o LogGuard para ampliar meus conhecimentos em Python e explorar a aplicação de conceitos de segurança da informação no desenvolvimento de software.

O projeto complementa minha experiência com aplicações web, APIs e bancos de dados, permitindo trabalhar também com processamento de arquivos, algoritmos de análise, validação de entradas e testes automatizados.

## Autor

**Fernando Augusto Bueno Canquerini**

Estudante de Tecnologia em Análise e Desenvolvimento de Sistemas na Universidade Federal do Paraná (UFPR).

GitHub: https://github.com/fernandoaugustobueno10-wq

---

Projeto pessoal desenvolvido para aprendizado e portfólio.
