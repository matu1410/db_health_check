# Oracle Health Check - Automação de Monitoramento

Este projeto executa um Health Check automatizado em múltiplos bancos Oracle, gerando um relatório HTML visualmente moderno e enviando por e-mail um resumo inteligente e detalhado.

## 📦 Estrutura do Projeto

```
/health_check/
├── main_multi_full_healthcheck_atualizado.py   # Script principal
├── queries/                                    # Queries SQL separadas
│   ├── tablespaces.sql
│   ├── backups_failed.sql
│   ├── backups_last_4h.sql
│   ├── backups_running.sql
│   ├── diskgroups.sql
│   ├── fra_usage.sql
│   ├── dg_lag.sql
│   ├── sessions_waiting.sql
│   ├── resource_limit.sql
│   └── instance_status.sql
├── lista_prd.txt                               # Lista de TNS a serem monitorados
```

## ⚙️ Requisitos

Antes de rodar o projeto, você precisa:

- Python 3.8 ou superior
- Oracle Client instalado (ou Instant Client)
- Acesso de rede aos bancos Oracle desejados

## 📚 Pacotes Python necessários

Instale as dependências com:

```bash
pip install cx_Oracle jinja2
```

## 🔧 Configuração

1. **Configure a conexão**:

   Edite o arquivo `main_multi_full_healthcheck_atualizado.py` e preencha:

   ```python
   DB_USER = "seu_usuario"
   DB_PASS = "sua_senha"
   GMAIL_USER = "seu_email@gmail.com"
   GMAIL_APP_PASSWORD = "sua_senha_de_app"
   EMAIL_DESTINO = "destinatario@email.com"
   ```

2. **Configure o arquivo `lista_prd.txt`**:

   Adicione o alias de conexão TNS de cada banco, um por linha:

   ```
   DB1_TNS_ALIAS
   DB2_TNS_ALIAS
   DB3_TNS_ALIAS
   ```

3. **Configure o TNS_ADMIN** (se necessário):

   Exporte o caminho das entradas TNS no seu ambiente:

   ```bash
   export TNS_ADMIN=/path/to/your/network/admin
   ```

## 🚀 Executando o Script

Para executar manualmente:

```bash
python main_multi_full_healthcheck_atualizado.py
```

## 🕑 Agendamento automático (Linux)

Para rodar automaticamente todos os dias via cron:

```bash
crontab -e
```

Adicionar a linha:

```bash
0 8 * * * /usr/bin/python3 /path/to/health_check/main_multi_full_healthcheck_atualizado.py
```

Isso irá rodar todo dia às 08:00 AM.

## 📈 Expansão

Quer adicionar uma nova seção no Health Check?
- Crie um novo arquivo `.sql` dentro da pasta `queries/`
- Adicione a execução no Python
- Gere o novo bloco no HTML Detalhado

## 🤝 Contribuições

Pull Requests são bem-vindos!  
Sugestões, melhorias e novas métricas também.

## 🛡️ Licença

Este projeto está licenciado sob a Licença MIT.

## ✉️ Contato

Para dúvidas ou suporte, entre em contato:  
📧 **seu_email@dominio.com**