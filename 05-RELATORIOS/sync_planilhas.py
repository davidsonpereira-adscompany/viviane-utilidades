#!/usr/bin/env python3
"""Sincroniza o painel com as planilhas da cliente (Google Sheets via Maton).

ida   : dados.json  -> Controle Diário (colunas azuis: investido e conversas, por data)
volta : Controle Diário (colunas amarelas: vendas e valor vendido) -> vendas.json (lido pelo painel)
        e Projeção de Metas (dias trabalhados, vendas acumuladas, nº de vendas, por mês)

Uso: python3 sync_planilhas.py [ida|volta|tudo]   (padrão: tudo)
Precisa da variável de ambiente MATON_API_KEY (ou do arquivo ~/.config/maton/token).
Só usa a biblioteca padrão — roda em qualquer máquina, inclusive no GitHub Actions.
"""
import json, os, sys, datetime, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "planilhas.json"), encoding="utf-8"))
KEY = os.environ.get("MATON_API_KEY") or open(os.path.expanduser("~/.config/maton/token")).read().strip()
SHEETS = "https://api.maton.ai/google-sheets/v4/spreadsheets/"
EPOCH = datetime.date(1899, 12, 30)


def api(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"erro HTTP {e.code} em {url}: {e.read().decode()[:400]}")


def ler(sheet_id, intervalo, render="UNFORMATTED_VALUE"):
    r = api("GET", SHEETS + sheet_id + "/values/" + urllib.parse.quote(intervalo) + "?valueRenderOption=" + render + "&dateTimeRenderOption=SERIAL_NUMBER")
    return r.get("values", [])


def escrever(sheet_id, dados):  # dados = [{"range": "ABA!C5", "values": [[..]]}, ...]
    if not dados:
        return 0
    r = api("POST", SHEETS + sheet_id + "/values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": dados})
    return r.get("totalUpdatedCells", 0)


def numero(v):
    if v in ("", None, "-"):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def data_iso(v):
    if isinstance(v, (int, float)):
        return (EPOCH + datetime.timedelta(days=int(v))).isoformat()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def linhas_controle():
    c = CFG["controle"]; col = c["colunas"]
    rng = f"{c['aba']}!{col['data']}{c['linha_inicio']}:{col['valor_vendido']}{c['linha_fim']}"
    linhas = ler(c["id"], rng)
    idx = lambda letra: ord(letra) - ord("A")
    out = {}
    for i, row in enumerate(linhas):
        row = row + [""] * 8
        d = data_iso(row[idx(col["data"])])
        if d:
            out[d] = {"linha": c["linha_inicio"] + i,
                      "investido": numero(row[idx(col["investido"])]), "conversas": numero(row[idx(col["conversas"])]),
                      "vendas": numero(row[idx(col["vendas"])]), "valor_vendido": numero(row[idx(col["valor_vendido"])])}
    return out


def ida():
    dados = json.load(open(os.path.join(BASE, "dados.json"), encoding="utf-8"))
    c = CFG["controle"]; col = c["colunas"]
    mapa = linhas_controle()
    hoje = datetime.date.today().isoformat()
    upd = []
    for d in dados.get("dias", []):
        if d["data"] not in mapa:
            continue
        atual = mapa[d["data"]]
        inv, conv = round(float(d.get("investido") or 0), 2), int(d.get("conversas") or 0)
        if atual["investido"] != inv or atual["conversas"] != conv:
            upd.append({"range": f"{c['aba']}!{col['investido']}{atual['linha']}:{col['conversas']}{atual['linha']}", "values": [[inv, conv]]})
    n = escrever(c["id"], upd)
    print(f"ida: {len(upd)} dia(s) atualizado(s) no Controle Diário ({n} células)")


def volta():
    mapa = linhas_controle()
    vendas = []
    for d, v in sorted(mapa.items()):
        if v["vendas"] is not None or v["valor_vendido"] is not None:
            vendas.append({"data": d, "vendas": int(v["vendas"] or 0), "valor_vendido": round(v["valor_vendido"] or 0, 2)})
    saida = {"atualizado_em": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).isoformat(timespec="minutes"),
             "fonte": "Controle Diário (planilha da cliente)", "vendas": vendas}
    p = os.path.join(BASE, "vendas.json")
    antigo = json.load(open(p, encoding="utf-8")).get("vendas") if os.path.exists(p) else None
    mudou = antigo != vendas
    if mudou or not os.path.exists(p):
        json.dump(saida, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"volta: {len(vendas)} dia(s) com vendas na planilha · vendas.json {'atualizado' if mudou else 'sem mudança'}")
    # projeção por mês
    pj = CFG["projecao"]; cel = pj["celulas"]
    upd = []
    for mes, aba in pj["abas_por_mes"].items():
        do_mes = [x for x in vendas if x["data"].startswith(mes)]
        dias = len([x for x in do_mes if x["vendas"] or x["valor_vendido"]])
        total_valor = round(sum(x["valor_vendido"] for x in do_mes), 2)
        total_vendas = sum(x["vendas"] for x in do_mes)
        atual = ler(pj["id"], f"{aba}!{cel['dias_trabalhados']}:{cel['numero_vendas']}")
        atual = [numero(r[0]) if r else None for r in atual] + [None] * 3
        if atual[:3] != [float(dias), float(total_valor), float(total_vendas)]:
            upd.append({"range": f"{aba}!{cel['dias_trabalhados']}", "values": [[dias]]})
            upd.append({"range": f"{aba}!{cel['vendas_acumuladas']}", "values": [[total_valor]]})
            upd.append({"range": f"{aba}!{cel['numero_vendas']}", "values": [[total_vendas]]})
    n = escrever(pj["id"], upd)
    print(f"volta: projeção — {n} célula(s) atualizada(s)")


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    if modo in ("ida", "tudo"):
        ida()
    if modo in ("volta", "tudo"):
        volta()
