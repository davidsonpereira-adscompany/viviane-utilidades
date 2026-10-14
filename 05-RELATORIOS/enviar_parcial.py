#!/usr/bin/env python3
"""Envia a parcial do dia (05-RELATORIOS/parciais/AAAA-MM-DD.md) pelo WhatsApp via Evolution API.

Uso: python3 enviar_parcial.py [AAAA-MM-DD] [--somente-copia]
 - sem data: usa a data de hoje em Brasília.
 - --somente-copia: manda só para os números de "copia" (teste), não para o grupo.
Precisa de EVOLUTION_APIKEY no ambiente. Registra os envios em parciais/.enviadas para nunca repetir o mesmo dia.
"""
import json, os, sys, datetime, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "parcial.json"), encoding="utf-8"))
KEY = os.environ.get("EVOLUTION_APIKEY", "")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
somente_copia = "--somente-copia" in sys.argv
hoje = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date().isoformat()
data = args[0] if args else hoje
arq = os.path.join(BASE, "parciais", data + ".md")
marcador = os.path.join(BASE, "parciais", ".enviadas")

if not KEY:
    print("EVOLUTION_APIKEY não definido — nada enviado."); sys.exit(0)
if not os.path.exists(arq):
    print(f"sem parcial para {data} — nada a enviar."); sys.exit(0)
enviadas = open(marcador, encoding="utf-8").read().split() if os.path.exists(marcador) else []
if data in enviadas and not somente_copia:
    print(f"parcial de {data} já enviada — nada a fazer."); sys.exit(0)

texto = open(arq, encoding="utf-8").read().strip()
destinos = ([] if somente_copia else CFG.get("destinos", [])) + CFG.get("copia", [])
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
if ok and not somente_copia:
    with open(marcador, "a", encoding="utf-8") as f:
        f.write(data + "\n")
print(f"{ok}/{len(destinos)} envio(s) concluído(s) · parcial de {data}")
sys.exit(0 if ok == len(destinos) else 1)
