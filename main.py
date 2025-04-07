
import cx_Oracle
import smtplib
import matplotlib.pyplot as plt
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from jinja2 import Template

# === CONFIGURAÇÕES ===
DB_USER = "DBA_MON"
DB_PASS = "Duda@2024"
LISTA_TNS = "lista_prd.txt" 

GMAIL_USER = "mhenrique88@gmail.com"
GMAIL_APP_PASSWORD = "yvav duzz egdi cbao"
EMAIL_DESTINO = "mhenrique88@gmail.com"

# === COLETORES ===
resumo_global = {"tablespace_alertas": 0, "backups_falhos": 0, "dataguard_lag": 0}
detalhes_por_banco = []

with open(LISTA_TNS) as f:
    bancos = [l.strip() for l in f if l.strip()]

for tns in bancos:
    try:
        conn = cx_Oracle.connect(DB_USER, DB_PASS, tns)
        cursor = conn.cursor()

        # Tablespaces
        cursor.execute("""
        SELECT df.tablespace_name,
               ROUND(SUM(df.bytes)/1024/1024, 2),
               ROUND(SUM(df.bytes - NVL(fs.bytes,0))/1024/1024, 2),
               ROUND(NVL(fs.bytes,0)/1024/1024, 2),
               ROUND((SUM(df.bytes - NVL(fs.bytes,0)) / SUM(df.bytes)) * 100, 2)
        FROM dba_data_files df
        LEFT JOIN (
            SELECT tablespace_name, SUM(bytes) AS bytes
            FROM dba_free_space
            GROUP BY tablespace_name
        ) fs ON df.tablespace_name = fs.tablespace_name
        GROUP BY df.tablespace_name, fs.bytes
        ORDER BY 5 DESC
        """)
        tablespaces = []
        ts_alertas = 0
        for row in cursor.fetchall():
            nome, total, usado, livre, pct = row
            classe = ""
            if pct > 95:
                classe = "bg-critical"
            elif pct > 80:
                classe = "bg-warning"
            if pct > 80:
                ts_alertas += 1
            tablespaces.append({
                "nome": nome, "total_mb": total, "usado_mb": usado,
                "livre_mb": livre, "pct_usado": pct, "classe": classe
            })
        resumo_global["tablespace_alertas"] += ts_alertas

        # Backups com falha
        cursor.execute("""
        SELECT status, TO_CHAR(start_time, 'DD/MM/YYYY HH24:MI'), input_type
        FROM V$RMAN_BACKUP_JOB_DETAILS
        WHERE start_time > SYSDATE - 1
        AND status NOT IN ('COMPLETED', 'SUCCESS')
        """)
        backups = [{"status": s, "inicio": t, "tipo": tipo} for s, t, tipo in cursor.fetchall()]
        resumo_global["backups_falhos"] += len(backups)

        # Lag DG
        cursor.execute("""
        SELECT value
        FROM V$DATAGUARD_STATS
        WHERE name = 'apply lag'
        """)
        lags = []
        for (v,) in cursor.fetchall():
            if v and v != '0' and v != '0 seconds':
                try:
                    num = int(''.join(filter(str.isdigit, v)))
                    if num > 300:
                        resumo_global["dataguard_lag"] += 1
                        lags.append(v)
                except:
                    pass

        detalhes_por_banco.append({
            "instancia": tns,
            "tablespaces": tablespaces,
            "backups": backups,
            "lags": lags
        })

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao conectar em {tns}: {e}")

# === GRÁFICO DE ALERTAS ===
labels = ["Tablespace > 80%", "Backups Falhos", "DG Lag > 5min"]
values = [resumo_global["tablespace_alertas"], resumo_global["backups_falhos"], resumo_global["dataguard_lag"]]

plt.figure(figsize=(6,4))
plt.bar(labels, values, color=["orange", "red", "orange"])
plt.title("Resumo de Alertas Oracle")
plt.ylabel("Qtd Bancos")
plt.tight_layout()
plt.savefig("grafico_resumo.png")

# === HTML RESUMO ===
html_topo = Template("""
<html><head><style>
body { font-family: Arial; margin: 20px; }
.card { display: inline-block; width: 30%; margin: 1%; padding: 15px; border-radius: 8px; color: white; font-size: 20px; font-weight: bold; text-align: center; }
.critical { background: #e74c3c; }
.warning { background: #f1c40f; color: black; }
.ok { background: #2ecc71; }
</style></head><body>
<h1>Resumo Geral - {{ agora }}</h1>
<div class="card {{ 'warning' if ts > 0 else 'ok' }}">Tablespaces > 80%<br>{{ ts }}</div>
<div class="card {{ 'critical' if bf > 0 else 'ok' }}">Backups com falha<br>{{ bf }}</div>
<div class="card {{ 'warning' if dg > 0 else 'ok' }}">Data Guard Lag > 5min<br>{{ dg }}</div>
<img src="cid:chart_resumo" style="margin-top:20px; max-width:600px;" />
</body></html>
""").render(
    agora=datetime.now().strftime('%d/%m/%Y %H:%M'),
    ts=resumo_global["tablespace_alertas"],
    bf=resumo_global["backups_falhos"],
    dg=resumo_global["dataguard_lag"]
)

# === HTML DETALHADO (ANEXO) ===
html_detalhado = "<html><head><style>body { font-family: Arial; margin: 20px; } table { border-collapse: collapse; width: 100%; margin-bottom: 30px; } th, td { border: 1px solid #ccc; padding: 6px; } .bg-warning { background: yellow; } .bg-critical { background: red; color: white; }</style></head><body>"
for banco in detalhes_por_banco:
    html_detalhado += f"<h2>{banco['instancia']}</h2>"
    html_detalhado += "<h3>Tablespaces</h3><table><tr><th>Nome</th><th>Total</th><th>Usado</th><th>Livre</th><th>%</th></tr>"
    for t in banco["tablespaces"]:
        html_detalhado += f"<tr class='{t['classe']}'><td>{t['nome']}</td><td>{t['total_mb']}</td><td>{t['usado_mb']}</td><td>{t['livre_mb']}</td><td>{t['pct_usado']}</td></tr>"
    html_detalhado += "</table>"

    html_detalhado += "<h3>Backups com Falha</h3><table><tr><th>Status</th><th>Início</th><th>Tipo</th></tr>"
    for b in banco["backups"]:
        html_detalhado += f"<tr><td>{b['status']}</td><td>{b['inicio']}</td><td>{b['tipo']}</td></tr>"
    html_detalhado += "</table>"

    html_detalhado += "<h3>Lag Data Guard</h3><ul>"
    for l in banco["lags"]:
        html_detalhado += f"<li>{l}</li>"
    html_detalhado += "</ul><hr>"

html_detalhado += "</body></html>"

with open("relatorio_detalhado.html", "w", encoding="utf-8") as f:
    f.write(html_detalhado)

# === ENVIO DO EMAIL ===
msg = MIMEMultipart('related')
msg['Subject'] = "Resumo Oracle - Múltiplos Bancos"
msg['From'] = GMAIL_USER
msg['To'] = EMAIL_DESTINO

alt = MIMEMultipart('alternative')
alt.attach(MIMEText(html_topo, 'html'))
msg.attach(alt)

with open("grafico_resumo.png", 'rb') as f:
    img = MIMEImage(f.read())
    img.add_header('Content-ID', '<chart_resumo>')
    msg.attach(img)

with open("relatorio_detalhado.html", 'rb') as f:
    part = MIMEApplication(f.read(), _subtype='html')
    part.add_header('Content-Disposition', 'attachment', filename="relatorio_detalhado.html")
    msg.attach(part)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    server.send_message(msg)

print("Email enviado com sucesso.")
