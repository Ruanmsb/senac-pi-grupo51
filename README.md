# Encurtador de URL

Um sistema web rápido e seguro para encurtamento de links, desenvolvido em Python utilizando o microframework Flask. O projeto aplica padrões profissionais de arquitetura (MVC) e algoritmos criptográficos para garantir a integridade dos dados e a segurança das URLs geradas.

## Tecnologias Utilizadas

*   **Linguagem:** Python 3
*   **Framework Web:** Flask
*   **Banco de Dados:** SQLite
*   **ORM:** Flask-SQLAlchemy
*   **Frontend:** HTML5 e CSS3 puro

## Arquitetura do Projeto (MVC)

**MVC (Model-View-Controller)** 

*   `main.py`: O orquestrador da aplicação. Inicializa o servidor, configura a conexão com o banco de dados local via variáveis de ambiente e executa a criação física das tabelas.
*   `models.py`: A camada **Model**. Contém a representação da tabela do banco de dados (SQLite), estruturada com a sintaxe moderna do SQLAlchemy 2.0 (`Mapped` e `mapped_column`).
*   `controllers.py`: A camada **Controller**. Centraliza toda a regra de negócio, rotas, lógica de segurança e persistência de dados.
*   `templates/` e `static/`: A camada **View**. Separação estrita entre a marcação estrutural (`index.html`) e a estilização visual (`style.css`).

## Lógica de Funcionamento e Segurança

1.  **Algoritmo Base62 Seguro:** O sistema não utiliza métodos pseudoaleatórios preditivos. A geração da string de 6 caracteres utiliza o alfabeto Base62 (letras maiúsculas, minúsculas e números) alimentado pela biblioteca nativa `secrets`. Isso garante entropia criptográfica do sistema operacional, impossibilitando a dedução de links e gerando um ecossistema com aproximadamente **56,8 bilhões** de combinações únicas.
2.  **Prevenção de Colisões (Integridade de Dados):** Antes de salvar o registro, o Controller realiza uma checagem em tempo real no banco de dados. Caso o identificador sorteado já exista, um laço de repetição gera imediatamente novos códigos até garantir uma URL final 100% livre e inédita.
3.  **Redirecionamento Dinâmico:** O acesso ao link curto captura a variável da URL diretamente pelo roteador do Flask, realizando a busca otimizada no banco (através do índice único da coluna) e redirecionando o tráfego de volta à URL original.

## Observações

Foram implementados os requisitos funcionais do projeto. Vale ressaltar para evoluções futuras:

*   **Sobre a Lógica e Segurança:**
    *   O método de busca/checagem no banco pode ser otimizado para lidar com escala e alta concorrência.
    *   Deverão ser implementadas camadas de sanitização contra links maliciosos que possam causar danos à aplicação ou aos usuários finais.
*   **Sobre o Ciclo de Vida dos Dados:**
    *   Será implementado um prazo de expiração para o link gerado, garantindo que registros não fiquem armazenados no banco de dados por tempo indeterminado.
*   **Sobre o Banco de Dados**
    * Com o projeto indo para produção, utilizaríamos um banco mais robusto, como SQL Server, PostgreSQL, MySQL, etc.

## Como Executar o Projeto Localmente

**Pré-requisitos:** Ter o Python 3 instalado na máquina.

1. Clone ou baixe este repositório.
2. Abra o terminal na pasta raiz do projeto.
3. Crie e ative o ambiente virtual:
* **Windows:**
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
* **Linux/Mac:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
4. Instale as dependências:
    ```bash
    pip install -r requirements.txt
5. Crie o arquivo .env na raiz do projeto e insira a string de conexão local:
    ```bash
    DATABASE_URI=sqlite:///banco.db
6. Na pasta principal do projeto, inicie o servidor:
   ```bash
   python main.py