
# LogGuard

**Analisador de logs de segurança com dashboard interativo, desenvolvido em Python.**

O LogGuard é um projeto pessoal voltado à análise de eventos de segurança. A aplicação processa arquivos CSV, identifica padrões suspeitos, classifica alertas por severidade e permite consultar um histórico armazenado em SQLite.

Além da execução pelo terminal, o projeto possui um dashboard desenvolvido com Streamlit, permitindo visualizar indicadores, gráficos e filtros.

O objetivo é aplicar conhecimentos de desenvolvimento de software, algoritmos, segurança da informação, persistência de dados e testes automatizados em uma ferramenta prática.

## Funcionalidades

### Análise de segurança

- Leitura de arquivos CSV.
- Validação de endereços IPv4 e IPv6.
- Validação de datas e horários com fuso horário.
- Detecção de tentativas repetidas de login malsucedidas.
- Detecção de picos de respostas HTTP 401, 403 e 404.
- Classificação de alertas por severidade.
- Identificação de episódios distintos de atividade suspeita.
- Processamento de eventos fora de ordem.

### Persistência

- Armazenamento de alertas em SQLite.
- Prevenção de registros duplicados.
- Consulta do histórico.
- Filtro por severidade.
- Consultas SQL parametrizadas.
- Gravação transacional.

### Dashboard

- Indicadores de alertas.
- Contagem de alertas por severidade.
- Número de endereços IP distintos.
- Gráficos de severidade e evolução temporal.
- Filtros por IP, tipo, período e severidade.
- Tabela de histórico.
- Importação e análise de arquivos CSV pelo navegador.

## Tecnologias

| Tecnologia | Aplicação |
|---|---|
| Python 3.13 | Linguagem principal |
| Streamlit | Interface web |
| SQLite | Armazenamento local |
| unittest | Testes automatizados |
| Git | Versionamento |
| GitHub Actions | Integração contínua |

A análise e a persistência utilizam bibliotecas da própria linguagem Python. O Streamlit é a principal dependência externa do projeto.

## Arquitetura

O LogGuard foi dividido em módulos com responsabilidades específicas:

- `main.py`: interface de linha de comando.
- `dashboard.py`: interface web com Streamlit.
- `logguard/analisador.py`: leitura de CSV, validação de eventos e detecção de alertas.
- `logguard/repositorio.py`: persistência e consultas SQLite.
- `logguard/painel.py`: filtros e preparação dos indicadores do dashboard.
- `tests/`: testes automatizados.
- `exemplos/`: arquivos CSV fictícios para demonstração.

As interfaces de terminal e navegador reutilizam o mesmo analisador e o mesmo repositório SQLite.

## Estrutura do projeto

```text
logguard/
├── .github/
│   └── workflows/
│       └── tests.yml
├── .streamlit/
│   └── config.toml
├── exemplos/
│   ├── eventos.csv
│   └── eventos_http.csv
├── logguard/
│   ├── __init__.py
│   ├── analisador.py
│   ├── painel.py
│   └── repositorio.py
├── tests/
│   ├── test_analisador.py
│   ├── test_painel.py
│   └── test_repositorio.py
├── .gitignore
├── dashboard.py
├── main.py
├── README.md
└── requirements.txt
```

O diretório `dados/` e o ambiente virtual `.venv/` são locais e não devem ser enviados ao repositório.

## Requisitos

- Python 3.13.
- Git, para clonar o projeto.
- Navegador moderno, para acessar o dashboard.

O LogGuard não exige Docker, WSL ou servidor de banco de dados.

## Instalação no Windows

### 1. Clonar o projeto

```powershell
git clone https://github.com/fernandoaugustobueno10-wq/logguard.git

cd logguard
```

### 2. Criar um ambiente virtual

```powershell
py -3.13 -m venv .venv
```

### 3. Instalar as dependências

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O ambiente virtual mantém as dependências do projeto separadas das demais instalações Python.

## Executar o dashboard

No diretório do projeto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Depois, acesse:

http://127.0.0.1:8501

O dashboard será executado localmente no computador.

Para interromper o servidor, pressione `Ctrl+C` no terminal.

## Analisar arquivos pelo dashboard

1. Abra o dashboard no navegador.
2. Expanda a seção de importação.
3. Selecione um arquivo CSV válido.
4. Clique em **Analisar e salvar alertas**.
5. Consulte os indicadores, os gráficos e o histórico.

O processamento utiliza a mesma lógica de detecção da aplicação de terminal.

## Executar pelo terminal

### Análise sem armazenamento

```powershell
.\.venv\Scripts\python.exe main.py exemplos\eventos.csv
```

### Análise com armazenamento

```powershell
.\.venv\Scripts\python.exe main.py exemplos\eventos.csv --salvar
```

### Analisar erros HTTP

```powershell
.\.venv\Scripts\python.exe main.py exemplos\eventos_http.csv --salvar
```

### Consultar o histórico

```powershell
.\.venv\Scripts\python.exe main.py --historico
```

### Filtrar o histórico por severidade

```powershell
.\.venv\Scripts\python.exe main.py --historico --severidade ALTA --limite 10
```

O banco padrão é criado em `dados/logguard.sqlite3`.

## Formato do CSV

O arquivo deve conter exatamente as colunas:

| Coluna | Exemplo |
|---|---|
| timestamp | 2026-11-22T12:00:00Z |
| ip | 192.0.2.10 |
| evento | login_falha |
| status | 401 |

Exemplo de arquivo:

```csv
timestamp,ip,evento,status
2026-11-22T12:00:00Z,192.0.2.10,login_falha,401
2026-11-22T12:01:00Z,192.0.2.10,login_falha,401
2026-11-22T12:02:00Z,192.0.2.10,login_falha,401
2026-11-22T12:03:00Z,192.0.2.10,login_falha,401
2026-11-22T12:04:00Z,192.0.2.10,login_falha,401
```

Os tipos de evento atualmente aceitos são:

- `login_falha`
- `login_sucesso`
- `requisicao`

Os endereços IP utilizados nos exemplos são reservados para documentação.

## Regras de detecção

### Falhas repetidas de login

Identifica cinco ou mais eventos `login_falha`, com resposta HTTP 401 ou 403, originados do mesmo endereço IP em uma janela de dez minutos.

A severidade é considerada alta quando o episódio acontece em até dois minutos; caso contrário, é média.

### Picos HTTP

Identifica cinco ou mais eventos `requisicao`, com o mesmo status HTTP suspeito e provenientes do mesmo IP, em uma janela de cinco minutos.

São analisados os códigos:

- `401`: não autorizado.
- `403`: acesso proibido.
- `404`: recurso não encontrado.

A severidade depende do código HTTP e da duração do episódio.

Os parâmetros são heurísticos e foram definidos para demonstrar o funcionamento do projeto. Um alerta não representa confirmação de ataque.

## Testes automatizados

O LogGuard utiliza `unittest`.

Para executar todos os testes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A versão 0.4 possui 39 testes automatizados, distribuídos entre:

- Validação e análise de eventos.
- Regras de detecção.
- Persistência SQLite.
- Controle de duplicidade.
- Filtros e indicadores do dashboard.

Os testes também serão executados automaticamente pelo GitHub Actions.

## Segurança

O projeto inclui medidas de validação e proteção:

- Limite de 5 MB para os arquivos CSV.
- Limite de 20.000 eventos por análise.
- Validação de campos e formatos.
- Validação de endereços IP.
- Tratamento de arquivos inválidos.
- Consultas SQL parametrizadas.
- Transações no SQLite.
- Prevenção de duplicidade de alertas.
- Processamento temporário de arquivos enviados.
- Execução local do dashboard.
- Proteção contra publicação acidental do banco e de configurações sensíveis por meio do `.gitignore`.

Os arquivos enviados devem ser considerados dados não confiáveis.

**Atenção:** registros reais podem conter dados pessoais e informações sensíveis. Utilize somente arquivos autorizados e não publique logs de produção ou bancos de dados locais no GitHub.

## Limitações

A versão atual:

- Aceita somente o formato CSV documentado.
- Não interpreta diretamente logs brutos de Apache, Nginx ou Windows.
- Não realiza monitoramento contínuo.
- Não substitui um SIEM profissional.
- Não confirma automaticamente a ocorrência de ataques.
- Exibe no dashboard até 1.000 registros recentes do histórico.
- Não possui autenticação de usuários.
- Foi projetada para execução local, não para exposição pública na internet.

As regras podem produzir falsos positivos e devem ser utilizadas como apoio à análise.

## Melhorias futuras

- Novos formatos de logs.
- Novas regras de detecção.
- Exportação de relatórios.
- Ampliação dos testes de integração.
- Otimização das consultas ao histórico.
- Melhorias de acessibilidade e visualização.
- Documentação adicional sobre arquitetura e segurança.

## Autor

**Fernando Augusto Bueno Canquerini**

Estudante de Tecnologia em Análise e Desenvolvimento de Sistemas — Universidade Federal do Paraná (UFPR).

GitHub: https://github.com/fernandoaugustobueno10-wq

---

Projeto pessoal desenvolvido para aprendizado, experimentação e portfólio.
