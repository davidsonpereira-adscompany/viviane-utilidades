#!/usr/bin/env python3
"""Atualiza 05-RELATORIOS/dados.json com os números do dia.

Uso: python3 atualizar.py < payload.json

payload.json (gerado pela rotina das 07h a partir do Gerenciador):
{
  "atualizado_em": "2026-10-08T07:05:00-03:00",
  "dias": [ {"data": "2026-10-07", "investido": 12.34, "conversas": 4, "alcance": 1200, "impressoes": 2100, "cliques": 30} ],
  "grupos": [ {"id": "...", "nome": "...", "investido": 0, "conversas": 0, "alcance": 0, "impressoes": 0, "cliques": 0, "status": "ACTIVE"} ],
  "anuncios": [ {"id": "...", "nome": "...", "grupo": "A", "investido": 0, "conversas": 0, "alcance": 0, "impressoes": 0, "cliques": 0, "status": "ACTIVE"} ],
  "vendas": [ {"data": "2026-10-07", "vendas": 3, "valor_vendido": 540.0} ],
  "campanha_status": "ACTIVE"
}
Dias repetidos são sobrescritos (o Meta corrige números de ontem ao longo do dia).
"vendas" é opcional: vem da planilha da cliente quando disponível e nunca é apagado por uma atualização sem esse campo.
"""
import json, sys, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "dados.json")

with open(PATH, encoding="utf-8") as f:
    dados = json.load(f)
payload = json.load(sys.stdin)

dias = {d["data"]: d for d in dados.get("dias", [])}
for d in payload.get("dias", []):
    atual = dias.get(d["data"], {})
    vendas, valor = atual.get("vendas"), atual.get("valor_vendido")
    novo = {"data": d["data"]}
    for k in ("investido", "conversas", "alcance", "impressoes", "cliques"):
        novo[k] = d.get(k, atual.get(k, 0)) or 0
    novo["vendas"], novo["valor_vendido"] = vendas, valor
    dias[d["data"]] = novo
for v in payload.get("vendas", []):
    if v["data"] in dias:
        dias[v["data"]]["vendas"] = v.get("vendas")
        dias[v["data"]]["valor_vendido"] = v.get("valor_vendido")
    else:
        dias[v["data"]] = {"data": v["data"], "investido": 0, "conversas": 0, "alcance": 0, "impressoes": 0, "cliques": 0,
                           "vendas": v.get("vendas"), "valor_vendido": v.get("valor_vendido")}
dados["dias"] = [dias[k] for k in sorted(dias)]

if payload.get("grupos"):
    dados["grupos"] = payload["grupos"]
if payload.get("anuncios"):
    dados["anuncios"] = payload["anuncios"]
if payload.get("campanha_status"):
    dados["campanha"]["status"] = payload["campanha_status"]

agora = payload.get("atualizado_em") or datetime.datetime.now().astimezone().isoformat(timespec="minutes")
dados["atualizado_em"] = agora
dados["atualizacoes"] = (dados.get("atualizacoes", []) + [agora])[-60:]

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

tot_inv = sum(d["investido"] for d in dados["dias"])
tot_conv = sum(d["conversas"] for d in dados["dias"])
print(f"ok: {len(dados['dias'])} dias · investido R$ {tot_inv:.2f} · conversas {tot_conv} · atualizado {agora}")
