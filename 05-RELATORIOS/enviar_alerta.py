#!/usr/bin/env python3
"""Envia o alerta do dia (05-RELATORIOS/alertas/AAAA-MM-DD.md) pelo WhatsApp via Evolution API.

Uso: python3 enviar_alerta.py [AAAA-MM-DD]
Alertas vão SOMENTE para os números de "copia" do parcial.json (Davidson), nunca para o grupo do cliente.
Precisa de EVOLUTION_APIKEY no ambiente. Registra em alertas/.enviados para nunca repetir o mesmo dia.
"""
import json, os, sys, datetime, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "parcial.json"), encoding="utf-8"))
KEY = os.environ.get("EVOLUTION_APIKEY", "")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
hoje = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date().isoformat()
data = args[0] if args else hoje
arq = os.path.join(BASE, "alertas", data + ".md")
marcador = os.path.join(BASE, "alertas", ".enviados")

if not KEY:
    print("EVOLUTION_APIKEY não definido — nada enviado."); sys.exit(0)
if not os.path.exists(arq):
    print(f"sem alerta para {data} — nada a enviar."); sys.exit(0)
enviados = open(marcador, encoding="utf-8").read().split() if os.path.exists(marcador) else []
if data in enviados:
    print(f"alerta de {data} já enviado — nada a fazer."); sys.exit(0)

texto = "🚨 " + open(arq, encoding="utf-8").read().strip()
destinos = CFG.get("copia", [])
url = CFG["evolution_url"].rstrip("/") + "/message/sendText/" + urllib.parse.quote(CFG["instancia"])
ok = 0
for numero in destinos:
    req = urllib.request.Request(url, method="POST", data=json.dumps({"number": numero, "text": texto}).encode(),
                                 headers={"apikey": KEY, "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=60); ok += 1; print("enviado para", numero)
    except urllib.error.HTTPError as e:
        print("ERRO", e.code, "para", numero, ":", e.read().decode()[:300])
    except Exception as e:
        print("ERRO para", numero, ":", e)
if ok:
    with open(marcador, "a", encoding="utf-8") as f:
        f.write(data + "\n")
print(f"{ok}/{len(destinos)} envio(s) de alerta · {data}")
sys.exit(0 if ok == len(destinos) else 1)
