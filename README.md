# Encurtador de URL

Um sistema web para encurtamento de links, desenvolvido em Python com Flask. O projeto aplica arquitetura MVC, algoritmos criptográficos e boas práticas de segurança.

## Tecnologias

- **Linguagem:** Python 3.11+
- **Framework Web:** Flask
- **ORM:** Flask-SQLAlchemy 2.0
- **Frontend:** HTML5, CSS3, JavaScript

## Arquitetura (MVC)

| Arquivo | Camada | Responsabilidade |
|---|---|---|
| `main.py` | Orquestrador | Inicializa Flask, banco de dados e logging |
| `models.py` | Model | Tabela `url` com tipagem moderna do SQLAlchemy 2.0 |
| `controllers.py` | Controller | Regras de negócio, rotas API e persistência |
| `templates/index.html` | View | Interface assíncrona |
| `static/style.css` | View | Estilização dark minimalista |

## Funcionalidades

### Interface (Frontend assíncrono)
- Encurtamento via `fetch()` + JSON — sem recarregamento de página
- Mmétricas em tempo real: links criados, cliques totais e links do dia
- Histórico de links com contagem de cliques, data de criação e expiração
- Botões de copiar e excluir por linha

### Backend (API REST)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Página principal |
| `POST` | `/api/encurtar` | Encurta uma URL, retorna JSON |
| `GET` | `/api/stats` | Retorna métricas agregadas |
| `GET` | `/api/links` | Lista os últimos 50 links |
| `DELETE` | `/api/links/<id>` | Remove um link |
| `GET` | `/<codigo>` | Redireciona e registra o clique |

### Segurança

**Geração Base62 criptográfica** — usa `secrets.choice()` sobre o alfabeto Base62, gerando ~56,8 bilhões de combinações únicas por código de 6 caracteres.

**Prevenção de colisões via `IntegrityError`** — o INSERT é tentado diretamente; em caso de colisão o banco lança `IntegrityError`, a sessão sofre rollback e um novo código é gerado. Operação atômica, segura sob concorrência.

**Sanitização de URLs** — valida esquema (`http/https` apenas), host e blocklist de domínios.

**Rate limiting por IP** — janela deslizante em memória; retorna `429` ao exceder o limite.

**Expiração de links (TTL)** — campo `data_expiracao` no banco; links vencidos retornam `410 Gone`.

**Contagem de cliques** — incrementada a cada redirecionamento, sem SELECT adicional.

## Variáveis de Ambiente

Copie `.env.example` para `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URI` | — | String de conexão do banco |
| `URL_CODIGO_TAMANHO` | `6` | Tamanho do código gerado |
| `URL_TTL_DIAS` | `30` | Dias até expiração (0 = sem expiração) |
| `RATE_LIMIT_JANELA_SEGUNDOS` | `60` | Janela do rate limit por IP |
| `RATE_LIMIT_MAX_REQUISICOES` | `10` | Máximo de encurtamentos por janela |

## Como Executar

**Pré-requisitos:** Python 3.11+

```bash
# 1. Clone e entre na pasta
git clone <repo> && cd url-shortener

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 5. Inicie o servidor
python main.py
```

### Limpeza de links expirados

```bash
flask limpar-expirados
```

## Evoluções Futuras

- **Blocklist dinâmica** — integração com Google Safe Browsing ou VirusTotal
- **Limpeza agendada** — cron job ou Celery Beat para `flask limpar-expirados`
- **Autenticação** — painel de gerenciamento por usuário
- **Banco de produção** — PostgreSQL com Alembic para controle de migrações
- **Domínio customizado** — suporte a slugs personalizados pelo usuário

## Observação sobre Métricas e Histórico

Conforme definido no documento de requisitos, as funcionalidades de analytics (cards de métricas, histórico de links e contagem de cliques) são previstas para usuários autenticados. No MVP atual, essas funcionalidades estão implementadas e expostas sem autenticação **exclusivamente para fins de demonstração técnica**, validando que a coleta de dados e as rotas da API funcionam corretamente. A proteção dessas rotas por login será implementada na próxima fase do projeto.