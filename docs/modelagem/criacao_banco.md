# Criação do banco e dos papéis: guia de execução

**Status: testado** num PostgreSQL limpo (em 2026-10-29 e no CI, `.github/workflows/testes.yml`).
Este guia descreve como executar [`sql/00_criar_banco_e_papel.sql`](../../sql/00_criar_banco_e_papel.sql)
no seu servidor local. Depois dele, rode `sql/executar_tudo.sql` (ver o README principal).

O que será criado: o papel `bi_brasileirao` (dono do banco do projeto), o papel
`bi_brasileirao_leitura` (somente leitura, para o Power BI) e o banco `brasileirao2024`.
Nada existente no servidor é alterado. Os privilégios e suas justificativas estão na
[proposta da Fase 3, seção 6](proposta_fase3.md).

## 1. Pré-requisitos

| # | Pré-requisito | Como verificar | Observação |
|---|---|---|---|
| 1 | Serviço do PostgreSQL 18 em execução | PowerShell: `Get-Service postgresql*` → `Running` | — |
| 2 | Saber em qual servidor e porta executar | pgAdmin → propriedades do servidor, ou `SHOW port;` | Se houver mais de uma instalação, confirme que é a do PostgreSQL 18 |
| 3 | Credencial de um **superusuário** (ex.: `postgres`) | Consulta 1e do script | Só para este script; o projeto não usa mais o superusuário depois |
| 4 | `psql` disponível pelo caminho completo | `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version` | Não precisa estar no PATH |
| 5 | Nomes livres, ICU `pt-BR`, `scram-sha-256` | Consultas 1b a 1d do script (somente leitura) | Sem ICU, use a alternativa indicada no BLOCO 3 |
| 6 | `pg_hba.conf` permitindo login local por senha | Padrão da instalação no Windows (`scram-sha-256` para `127.0.0.1/32` e `::1/128`) | Nenhuma alteração prevista. Se o login falhar, **não** altere o `pg_hba.conf` sem antes conversarmos |
| 7 | Decidir onde guardar as senhas dos papéis | — | Gerenciador de senhas, ou `%APPDATA%\postgresql\pgpass.conf` (fora do repositório) |

Não é preciso backup: o script só cria objetos novos e falha, sem alterar nada, se algum deles já
existir.

## 2. Comandos específicos do psql (não existem no pgAdmin)

| Comando | Para que serve | Onde aparece |
|---|---|---|
| `-v ON_ERROR_STOP=1` (opção de linha de comando) | Interrompe a execução no primeiro erro | Seção 3, passo 2 |
| `\password <papel>` | Define a senha de forma interativa; o psql criptografa a senha (SCRAM) **antes** de enviá-la ao servidor, então ela não aparece em logs nem no histórico de comandos | Seção 3, passo 3 |
| `\copy` | Carga dos CSVs (Fase 3, `03_carga.sql`) | Fora deste guia |

O arquivo `00_criar_banco_e_papel.sql` **não contém nenhum desses comandos**: é SQL puro.

## 3. Execução pelo psql (recomendada)

```powershell
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
```

**Passo 1. Pré-verificação (somente leitura).** Abra uma sessão interativa e cole **apenas** as
consultas do BLOCO 1. Não execute o arquivo inteiro nesta etapa, porque os blocos seguintes criam
os papéis e o banco:

```powershell
& $psql -U postgres -d postgres
```

**Passo 2. Executar o script** (parar no primeiro erro):

```powershell
& $psql -v ON_ERROR_STOP=1 -U postgres -d postgres -f sql/00_criar_banco_e_papel.sql
```

**Passo 3. Definir as senhas** (interativo; o psql pede a senha duas vezes):

```powershell
& $psql -U postgres -d postgres
```
```
\password bi_brasileirao
\password bi_brasileirao_leitura
\q
```

**Passo 4. Testar o acesso:**

```powershell
& $psql -U bi_brasileirao -d brasileirao2024 -c "SELECT current_user, current_database();"
```

## 4. Execução pelo pgAdmin (alternativa)

No Query Tool, conectado ao banco **`postgres`** com um superusuário:

1. **BLOCO 1:** selecione as consultas e execute; confira cada resultado.
2. **BLOCO 2:** selecione os dois `CREATE ROLE` e os `COMMENT ON ROLE` e execute.
3. **BLOCO 3:** selecione **apenas** o `CREATE DATABASE … ;` e execute **sozinho**. Junto com
   outros comandos, ele falha com "CREATE DATABASE cannot run inside a transaction block".
4. **BLOCO 4:** selecione `COMMENT ON DATABASE`, `REVOKE` e `GRANT` e execute.
5. **BLOCO 5:** execute as consultas de conferência.
6. **Senhas:** a recomendação é o `\password` do psql (seção 3, passo 3). Se usar o pgAdmin
   (*Login/Group Roles → Properties → Definition*), saiba que ele envia um `ALTER ROLE … PASSWORD`
   com a senha em texto ao servidor. Ela pode ficar registrada no log do servidor, se o log de
   comandos estiver ativo.

O ON_ERROR_STOP não existe no pgAdmin; executar bloco a bloco cumpre esse papel: se um bloco
falhar, não siga para o próximo.

## 5. Resultado esperado (BLOCO 5)

| Verificação | Esperado |
|---|---|
| `bi_brasileirao`, `bi_brasileirao_leitura` | `rolsuper`, `rolcreatedb`, `rolcreaterole` = false; `rolcanlogin` = true; `tem_senha` = true após o passo 3 |
| `brasileirao2024` | dono `bi_brasileirao`; `datlocprovider` = `i`; `datacl` sem entrada `=…` (PUBLIC) |

## 6. Reversão

Se for preciso desfazer, os comandos estão no fim do script, comentados. Eles afetam somente os
objetos criados aqui e **não devem ser executados sem uma decisão explícita**.
