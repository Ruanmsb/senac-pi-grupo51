# Encurtador de URL

Aplicacao web para encurtar links com Flask.

## O que faz

- Cria URL curta a partir de uma URL original.
- Redireciona para a URL original pelo codigo curto.
- Conta cliques por link.
- Expira links por TTL.
- Aplica rate limit por IP.
- Exibe documentacao da API em Swagger.

## Requisitos

- Windows
- Python 3.11+

Observacao: se Python nao estiver instalado, o script pergunta se deseja instalar via winget.

## Como executar (recomendado)

No PowerShell, na raiz do projeto:

```powershell
.\Start.ps1
```

Para apenas preparar ambiente (sem subir servidor):

```powershell
.\Start.ps1 -SetupOnly
```

## O que o Start.ps1 faz

1. Verifica se Python existe no sistema.
2. Oferece instalacao via winget quando necessario.
3. Cria .venv localmente.
4. Garante pip no .venv.
5. Instala dependencias de requirements.txt.
6. Garante arquivo .env.
7. Se existir env_venv.zip, extrai somente .env.
8. Se nao existir, cria .env padrao.
9. Valida a aplicacao com teste rapido da rota /.

## Enderecos

- App: http://127.0.0.1:5000
- Swagger: http://127.0.0.1:5000/apidocs/

## Variaveis de ambiente

Arquivo .env na raiz.

- DATABASE_URI=sqlite:///urls.db
- FLASK_DEBUG=False
- API_KEY=
- URL_CODIGO_TAMANHO=6
- URL_TTL_DIAS=30
- RATE_LIMIT_JANELA_SEGUNDOS=60
- RATE_LIMIT_MAX_REQUISICOES=10

## Rotas principais

- GET /
- POST /api/encurtar
- GET /api/stats
- GET /api/links
- DELETE /api/links/<id>
- GET /<codigo>

## Autenticacao da API

Se API_KEY estiver preenchida no .env, as rotas /api/stats e /api/links exigem:

Authorization: Bearer SUA_CHAVE

## Estrutura essencial

- main.py: inicializacao Flask e banco
- controllers.py: regras e rotas
- models.py: modelo de dados
- Start.ps1: setup e execucao no Windows
