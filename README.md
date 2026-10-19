# MedSinc — Backend

API Flask do **MedSinc**, sistema de gestão e intermediação de plantões na área da saúde.

Este repositório cobre autenticação, plantões, marketplace (oportunidades e candidaturas), finanças, pacientes/atendimentos e notificações.

Interface (frontend): [plantao-medico-finance](https://github.com/HierroPagotto/plantaoMedicoFinance)

## Pré-requisitos

- Python 3.10 ou superior
- MySQL 8
- Conta/credenciais locais para o banco

## Configuração

```bash
git clone https://github.com/HierroPagotto/MedSincBackend.git
cd MedSincBackend

python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

Copie o exemplo de variáveis e ajuste:

```bash
cp .env.example .env
```

No `.env`, preencha pelo menos:

| Variável | Exemplo | Uso |
|----------|---------|-----|
| `DB_HOST` | `localhost` | Host do MySQL |
| `DB_PORT` | `3306` | Porta |
| `DB_USERNAME` | `root` | Usuário |
| `DB_PASSWORD` | | Senha |
| `DB_NAME` | `medsinc` | Nome do banco |
| `SECRET_KEY` | string longa e aleatória | Assinatura JWT |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Validade do token |

`MAIL_*`, `NOTIFICATIONS_JOB_SECRET` e `APP_BASE_URL` são opcionais para desenvolvimento local (e-mail e jobs de notificação).

Crie o banco no MySQL:

```sql
CREATE DATABASE medsinc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Rodar local

Com o venv ativo e o MySQL acessível:

```bash
python run.py
```

A API sobe em modo debug em [http://127.0.0.1:5000](http://127.0.0.1:5000). As rotas da API ficam sob `/api/...`.

No startup, o bootstrap cria ou ajusta tabelas e colunas necessárias. As migrações Alembic ficam em `migrations/versions/`.

### CORS (frontend local)

A API libera a origem da interface em desenvolvimento:

- `http://localhost:8080`
- `http://127.0.0.1:8080`

Suba o frontend nessa porta (veja o README do repositório da interface).

## Ordem sugerida

1. MySQL com o banco `medsinc` criado  
2. Backend (`python run.py`)  
3. Frontend com `VITE_API_BASE_URL=http://127.0.0.1:5000/api`  
4. Abrir [http://localhost:8080](http://localhost:8080)

## Estrutura

```
app/
  routes/        # Endpoints HTTP
  models/        # Modelos SQLAlchemy
  repositories/  # Acesso a dados
  services/      # Regras de negócio (ex.: marketplace)
  schemas/       # Payloads / dataclasses
  utils/         # Auth, bootstrap, e-mail, etc.
migrations/      # Alembic
run.py           # Entrada local (debug)
```

## Produção

Em produção a API costuma rodar com Gunicorn (ver `requirements.txt`). Credenciais e `SECRET_KEY` devem vir de variáveis de ambiente, nunca commitadas.
