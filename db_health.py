import cx_Oracle
import smtplib
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from jinja2 import Template

# === CONFIG ===
DB_USER = "xxxxx"
DB_PASS = "xxxxxx"
LISTA_TNS = "lista_prd.txt" 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUERIES_PATH = os.path.join(BASE_DIR, "queries")

GMAIL_USER = "xxxxx"
GMAIL_APP_PASSWORD = "xxxxx"
EMAIL_DESTINO = "xxxxxx"

def carregar_query(nome_arquivo):
    caminho = os.path.join(QUERIES_PATH, nome_arquivo)
    with open(caminho, "r") as f:
        return f.read()

resumo_global = {
    "tablespace_alertas": 0,
    "backups_falhos": 0,
    "dataguard_lag": 0,
    "diskgroups_criticos": 0,
    "backups_falhos_4h": 0
}
detalhes_por_banco = []

with open(LISTA_TNS) as f:
    bancos = [l.strip() for l in f if l.strip()]

for tns in bancos:
    try:
        conn = cx_Oracle.connect(DB_USER, DB_PASS, tns)
        cursor = conn.cursor()

        def executar(nome):
            cursor.execute(carregar_query(nome))
            return cursor.fetchall()

        # Capturar nome do banco
        cursor.execute("SELECT name FROM v$database")
        dbname = cursor.fetchone()[0]

        # Instância Status
        status_instancia = executar("instance_status.sql")[0]
        status_info = {
            "instance_name": status_instancia[0],
            "status": status_instancia[1],
            "db_status": status_instancia[2]
        }

        # Tablespaces
        tablespaces = []
        for row in executar("tablespaces.sql"):
            nome, total, usado, livre, pct = row
            classe = "bg-critical" if pct > 95 else "bg-warning" if pct > 80 else ""
            if pct > 80: resumo_global["tablespace_alertas"] += 1
            tablespaces.append(dict(nome=nome, total_mb=total, usado_mb=usado, livre_mb=livre, pct_usado=pct, classe=classe))

        # Diskgroups
        diskgroups = []
        for row in executar("diskgroups.sql"):
            name, total, free, pct = row
            classe = "bg-critical" if pct > 90 else ""
            if pct > 90: resumo_global["diskgroups_criticos"] += 1
            diskgroups.append(dict(name=name, total_mb=total, free_mb=free, pct_used=pct, classe=classe))

        # FRA Usage
        fra = executar("fra_usage.sql")

        # Backups Falhos
        backups_falhos = [dict(status=r[0], inicio=r[1], tipo=r[2]) for r in executar("backups_failed.sql")]
        resumo_global["backups_falhos"] += len(backups_falhos)

        # Backups últimos 4 horas
        backups_4h = [dict(start=r[0], end=r[1], output=r[2], status=r[3], tipo=r[4]) for r in executar("backups_last_4h.sql")]
        resumo_global["backups_falhos_4h"] += sum(1 for b in backups_4h if b['status'] != 'COMPLETED')

        # Backups em execução
        backups_running = [dict(start=r[0], status=r[1], tipo=r[2]) for r in executar("backups_running.sql")]

        # Sessions Waiting
        sessions_wait = [dict(sid=r[0], user=r[1], event=r[2], status=r[3], wait_class=r[4],
                              sql_id=r[5], seconds=r[6], module=r[7], logon=r[8]) for r in executar("sessions_waiting.sql")]

        # Resource Limits
        resource_limits = [dict(name=r[0], current=r[1], limit=r[2], pct=r[3]) for r in executar("resource_limit.sql")]

        # Data Guard Lag
        dg_lag = executar("dg_lag.sql")

        detalhes_por_banco.append(dict(
            instancia=tns,
            dbname=dbname,
            status=status_info,
            tablespaces=tablespaces,
            diskgroups=diskgroups,
            fra=fra,
            backups=backups_falhos,
            backups_4h=backups_4h,
            backups_running=backups_running,
            sessions_wait=sessions_wait,
            resource_limits=resource_limits,
            dg_lag=dg_lag
        ))

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao conectar no banco {tns}: {e}")

# === HTML RESUMO ===
html_topo = Template("""
<html><head>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">
<style>
body { font-family: 'Open Sans', Arial, sans-serif; background-color: #f7f9fc; margin: 20px; color: #333; }
h1, h2, h3 { color: #2c3e50; }
.card { display: inline-block; width: 22%; margin: 1%; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); font-size: 18px; font-weight: bold; text-align: center; }
.card.ok { background: #2ecc71; color: white; }
.card.warning { background: #f1c40f; color: black; }
.card.critical { background: #e74c3c; color: white; }
</style>
</head><body>

<h1>Resumo Health Check - {{ agora }}</h1>
<div class="card {{ 'warning' if ts > 0 else 'ok' }}">Tablespaces > 80%<br>{{ ts }}</div>
<div class="card {{ 'critical' if bf > 0 else 'ok' }}">Backups Falhos<br>{{ bf }}</div>
<div class="card {{ 'warning' if dg > 0 else 'ok' }}">DG Lag > 5min<br>{{ dg }}</div>
<div class="card {{ 'critical' if asm > 0 else 'ok' }}">Diskgroups > 90%<br>{{ asm }}</div>
<div class="card {{ 'critical' if bf4 > 0 else 'ok' }}">Falhas últimas 4h<br>{{ bf4 }}</div>

</body></html>
""").render(
    agora=datetime.now().strftime('%d/%m/%Y %H:%M'),
    ts=resumo_global["tablespace_alertas"],
    bf=resumo_global["backups_falhos"],
    dg=resumo_global["dataguard_lag"],
    asm=resumo_global["diskgroups_criticos"],
    bf4=resumo_global["backups_falhos_4h"]
)

# === HTML DETALHADO ===
html_detalhado = """
<html><head>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">
<style>
body { font-family: 'Open Sans', Arial, sans-serif; background-color: #f7f9fc; margin: 20px; color: #333; }
h1, h2, h3 { color: #2c3e50; }
ul.toc { list-style-type: none; padding: 0; }
ul.toc li { margin: 8px 0; }
ul.toc a { color: #3498db; text-decoration: none; }
ul.toc a:hover { text-decoration: underline; }
table { width: 100%; border-collapse: separate; border-spacing: 0 10px; margin-top: 20px; }
th { background-color: #3498db; color: white; padding: 10px; border-radius: 5px 5px 0 0; }
td { background: white; padding: 12px; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
tr.bg-warning td { background-color: #fff3cd; }
tr.bg-critical td { background-color: #f8d7da; color: #721c24; }
hr { border: 0; height: 2px; background: #e1e4e8; margin: 40px 0; }
</style>
</head><body>
"""

for banco in detalhes_por_banco:
    html_detalhado += f"<h1>Database: <b>{banco['dbname']}</b></h1>"
    html_detalhado += """
    <h2>🔎 Sumário</h2>
    <ul class="toc">
      <li><a href="#tablespaces">🗄️ Tablespaces</a></li>
      <li><a href="#diskgroups">💾 Diskgroups</a></li>
      <li><a href="#fra">🔁 FRA Usage</a></li>
      <li><a href="#backups">🔥 Backups</a></li>
      <li><a href="#dg">🔄 Data Guard Lag</a></li>
      <li><a href="#sessions">⏱ Sessions Waiting</a></li>
      <li><a href="#resources">⚙️ Resource Limits</a></li>
    </ul>
    <hr>
    """

    # Tablespaces
    html_detalhado += "<h2 id='tablespaces'>🗄️ Tablespaces</h2><table><tr><th>Nome</th><th>Total</th><th>Usado</th><th>Livre</th><th>%</th></tr>"
    for t in banco["tablespaces"]:
        html_detalhado += f"<tr class='{t['classe']}'><td>{t['nome']}</td><td>{t['total_mb']}</td><td>{t['usado_mb']}</td><td>{t['livre_mb']}</td><td>{t['pct_usado']}%</td></tr>"
    html_detalhado += "</table>"

    # Diskgroups
    html_detalhado += "<h2 id='diskgroups'>💾 Diskgroups</h2><table><tr><th>Nome</th><th>Total</th><th>Livre</th><th>% Usado</th></tr>"
    for dg in banco["diskgroups"]:
        html_detalhado += f"<tr class='{dg['classe']}'><td>{dg['name']}</td><td>{dg['total_mb']}</td><td>{dg['free_mb']}</td><td>{dg['pct_used']}%</td></tr>"
    html_detalhado += "</table>"

    # FRA
    if banco["fra"]:
        fra = banco["fra"][0]
        classe_fra = "bg-critical" if fra[3] > 90 else "bg-warning" if fra[3] > 80 else ""
        html_detalhado += "<h2 id='fra'>🔁 FRA Usage</h2><table><tr><th>Nome</th><th>Total</th><th>Usado</th><th>% Utilizado</th></tr>"
        html_detalhado += f"<tr class='{classe_fra}'><td>{fra[0]}</td><td>{fra[1]}</td><td>{fra[2]}</td><td>{fra[3]}%</td></tr>"
        html_detalhado += "</table>"

    # Backups Falhos
    html_detalhado += "<h2 id='backups'>🔥 Backups</h2><table><tr><th>Status</th><th>Início</th><th>Tipo</th></tr>"
    for b in banco["backups"]:
        html_detalhado += f"<tr><td>{b['status']}</td><td>{b['inicio']}</td><td>{b['tipo']}</td></tr>"
    html_detalhado += "</table>"

    # Data Guard Lag
    html_detalhado += "<h2 id='dg'>🔄 Data Guard Lag</h2><table><tr><th>Lag Detectado</th></tr>"
    if banco["dg_lag"]:
        html_detalhado += f"<tr class='bg-critical'><td>{banco['dg_lag'][0][0]}</td></tr>"
    else:
        html_detalhado += "<tr><td>Sem Lag</td></tr>"
    html_detalhado += "</table>"

    # Sessions Waiting
    html_detalhado += "<h2 id='sessions'>⏱ Sessions Waiting</h2><table><tr><th>SID</th><th>Usuário</th><th>Evento</th><th>Tempo de Espera (s)</th></tr>"
    for s in banco["sessions_wait"]:
        html_detalhado += f"<tr><td>{s['sid']}</td><td>{s['user']}</td><td>{s['event']}</td><td>{s['seconds']}</td></tr>"
    html_detalhado += "</table>"

    # Resource Limits
    html_detalhado += "<h2 id='resources'>⚙️ Resource Limits</h2><table><tr><th>Resource</th><th>Atual</th><th>Limite</th><th>% Utilizado</th></tr>"
    for r in banco["resource_limits"]:
        classe_res = "bg-warning" if r['pct'] > 85 else ""
        html_detalhado += f"<tr class='{classe_res}'><td>{r['name']}</td><td>{r['current']}</td><td>{r['limit']}</td><td>{r['pct']}%</td></tr>"
    html_detalhado += "</table>"

html_detalhado += "</body></html>"

# Gravar o HTML
with open("relatorio_detalhado.html", "w", encoding="utf-8") as f:
    f.write(html_detalhado)

# === ENVIO DO EMAIL ===
msg = MIMEMultipart('mixed')
msg['Subject'] = "Resumo Health Check - Bancos Oracle"
msg['From'] = GMAIL_USER
msg['To'] = EMAIL_DESTINO

# Anexar o HTML resumo no corpo do e-mail
alt = MIMEMultipart('alternative')
alt.attach(MIMEText(html_topo, 'html'))
msg.attach(alt)

# Anexar o relatório detalhado
with open("relatorio_detalhado.html", 'rb') as f:
    part = MIMEApplication(f.read(), _subtype="html")
    part.add_header("Content-Disposition", "attachment", filename="relatorio_detalhado.html")
    msg.attach(part)

# Enviar
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    server.send_message(msg)

print("✅ Email enviado com sucesso!")


