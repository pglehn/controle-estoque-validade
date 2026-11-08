# Estoque em Dia

Sistema de Controle de Estoque e Validade para Redução do Desperdício de Alimentos. Esta é uma primeira versão acadêmica para apoiar a organização de produtos, lotes e movimentações. As prioridades do projeto devem ser validadas com o parceiro.

## O que a versão faz

- Login com contas cadastradas por um administrador.
- Cadastro de produtos, unidades de medida e lotes com data de validade.
- Registro de entrada, saída e descarte com motivo.
- Saldo por lote, verificação de saldo insuficiente e proteção contra o reenvio do mesmo lançamento.
- Consulta de lotes e alertas para itens vencidos ou com vencimento nos próximos sete dias.
- Histórico das últimas 100 movimentações, com filtro por tipo.

Lotes com saldo zero aparecem na consulta, mas não geram alertas. Um produto que vence hoje é considerado próximo do vencimento. Novos lotes começam com saldo zero: registre uma entrada para adicionar quantidade.

## Tecnologias

Python 3.14 (compatível também com Python 3.10 a 3.13), Django 5.2 LTS, PostgreSQL 17 com Psycopg 3, Bootstrap 5.3 e JavaScript com Fetch API. SQLite é fornecido como alternativa para demonstração local individual.

## Execução local no Windows

1. Instale Python 3.14 e baixe ou clone este repositório.
2. Abra o PowerShell na pasta do projeto e crie um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

3. Para uma demonstração individual, o SQLite já vem configurado. Prepare o banco e crie o usuário administrador:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

4. Acesse <http://127.0.0.1:8000/> e entre com a conta criada. O cadastro de outras contas pode ser realizado pelo administrador em <http://127.0.0.1:8000/admin/>.

Se o PowerShell bloquear a ativação do ambiente virtual, é possível executar o Python dele diretamente, por exemplo: `.\.venv\Scripts\python.exe manage.py migrate`.

### Usar PostgreSQL

Crie previamente um banco PostgreSQL e um usuário com permissão sobre ele. Antes de rodar as migrações, informe no terminal os dados do seu ambiente. Substitua os exemplos pelos dados reais sem publicar senhas:

```powershell
$env:DB_ENGINE = "postgresql"
$env:DB_NAME = "nome_do_banco"
$env:DB_USER = "usuario_do_banco"
$env:DB_PASSWORD = "senha_do_banco"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "5432"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Essas variáveis valem para a sessão atual do terminal. Para uso com acessos simultâneos, utilize PostgreSQL: o SQLite é apenas uma alternativa de demonstração e não oferece os mesmos bloqueios de linha.

## Uso

1. Entre com seu usuário e senha.
2. Em **Produtos**, cadastre o produto e sua unidade.
3. Em **Lotes e validade**, crie um lote com o código e a data de validade.
4. Em **Movimentações**, registre a entrada inicial. Registre as saídas e os descartes conforme ocorram.
5. Acompanhe os saldos e os avisos na tela inicial ou filtre os lotes por situação.

## Testes

```powershell
python manage.py test estoque
```

Os testes cobrem autenticação, formulários, movimentações, repetição de lançamento, saldo insuficiente e classificação de validade. Há também um teste de concorrência que é executado apenas quando o banco de testes é PostgreSQL; o usuário do banco precisa ter permissão para criar o banco de testes.

## Situação e limites

Este projeto é uma primeira versão para desenvolvimento e avaliação, não uma implantação pronta para produção. Por padrão, as configurações são de desenvolvimento local e o acesso ao CSS do Bootstrap usa uma CDN. Antes de qualquer uso público ou com dados reais, configure uma chave secreta exclusiva por meio de `DJANGO_SECRET_KEY`, desative `DJANGO_DEBUG`, configure `DJANGO_ALLOWED_HOSTS`, HTTPS, permissões, backup e demais proteções apropriadas. Não publique credenciais no repositório.

O sistema permite que usuários autenticados realizem as operações de estoque; perfis e permissões específicas ainda dependem de definição. Não registra comprovação de visita, de perdas reais ou de validação do parceiro.
