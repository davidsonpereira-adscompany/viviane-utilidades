#!/usr/bin/env python3
"""Atualiza 05-RELATORIOS/dados.json com os números do dia (lido pelo dashboard.html).

Uso: python3 atualizar.py < payload.json

payload.json (gerado pela rotina das 07h a partir do Gerenciador):
{
  "atualizado_em": "2026-10-08T07:05:00-03:00",
  "campanha_status": "ACTIVE",
  "leitura": "<strong>Frase-chave.</strong> Duas ou três frases em linguagem de loja.",
  "dias": [
    {"data": "2026-10-07", "investido": 12.34, "conversas": 4, "alcance": 1200, "impressoes": 2100, "cliques": 30,
     "engajamentos": 0,
     "campanhas": {"A | Vestidos": {"investido": 6.0, "conversas": 2, "alcance": 600},
                   "B | Masculino": {"investido": 3.0, "conversas": 1, "alcance": 300},
                   "C | Família e Confiança": {"investido": 3.34, "conversas": 1, "alcance": 300}}}
  ],
  "grupos": [ {"id": "...", "nome": "A | Vestidos", "investido": 0, "conversas": 0, "alcance": 0, "impressoes": 0, "cliques": 0, "status": "ACTIVE"} ],
  "anuncios": [ {"id": "...", "nome": "...", "grupo": "A", "investido": 0, "conversas": 0, "alcance": 0, "impressoes": 0, "cliques": 0, "status": "ACTIVE"} ],
  "vendas": [ {"data": "2026-10-07", "vendas": 3, "valor_vendido": 540.0} ]
}
Dias repetidos são sobrescritos (o Meta corrige os números de ontem ao longo do dia).
"vendas" é opcional: vem da planilha da cliente e nunca é apagado por uma atualização sem esse campo.
"""
import json, sys, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "dados.json")
METRICAS = ("investido", "conversas", "alcance", "impressoes", "cliques", "engajamentos")

with open(PATH, encoding="utf-8") as f:
    dados = json.load(f)
payload = json.load(sys.stdin)

dias = {d["data"]: d for d in dados.get("dias", [])}
for d in payload.get("dias", []):
    atual = dias.get(d["data"], {})
    novo = {"data": d["data"]}
    for k in METRICAS:
        novo[k] = d.get(k, atual.get(k, 0)) or 0
    novo["campanhas"] = d.get("campanhas") or atual.get("campanhas") or {}
    novo["vendas"] = atual.get("vendas")
    novo["valor_vendido"] = atual.get("valor_vendido")
    dias[d["data"]] = novo
for v in payload.get("vendas", []):
    base = dias.get(v["data"]) or {"data": v["data"], **{k: 0 for k in METRICAS}, "campanhas": {}}
    base["vendas"] = v.get("vendas")
    base["valor_vendido"] = v.get("valor_vendido")
    dias[v["data"]] = base
dados["dias"] = [dias[k] for k in sorted(dias)]

for chave in ("grupos", "anuncios", "leitura"):
    if payload.get(chave):
        dados[chave] = payload[chave]
if payload.get("campanha_status"):
    dados.setdefault("campanha", {})["status"] = payload["campanha_status"]

agora = payload.get("atualizado_em") or datetime.datetime.now().astimezone().isoformat(timespec="minutes")
dados["atualizado_em"] = agora
dados["atualizacoes"] = (dados.get("atualizacoes", []) + [agora])[-60:]

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

tot_inv = sum(d["investido"] for d in dados["dias"])
tot_conv = sum(d["conversas"] for d in dados["dias"])
print(f"ok: {len(dados['dias'])} dias · investido R$ {tot_inv:.2f} · conversas {tot_conv} · atualizado {agora}")
