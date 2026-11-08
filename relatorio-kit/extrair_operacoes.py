#!/usr/bin/env python3
"""Extrai as operações do SCR, faixa por faixa, de um PDF da Concentre.

Aceita o "Dossiê de Crédito" (seção 08, operações uma a uma) e o "Diagnóstico de Crédito /
Rating PF|PJ" (layout com "O P E R AÇÃO n", que também traz os códigos V110, V210...).

Uso: python3 extrair_operacoes.py relatorio.pdf > operacoes.json
"""
import json, re, subprocess, sys


def num(s):
    return float(s.replace(".", "").replace(",", "."))


FAIXA = re.compile(r"Cr[eé]ditos (a vencer|vencidos|baixados como preju[ií]zo)\s*(.*?) R\$ ([\d.]+,\d{2})(?: (V\d+) (\d+) (Sim|Não))?$", re.I)
LIMITE = re.compile(r"Limite de cr[eé]dito (.*?) R\$ ([\d.]+,\d{2})(?: (V\d+) (\d+) (Sim|Não))?$", re.I)


def faixa_de(l):
    fm, lm = FAIXA.match(l), LIMITE.match(l)
    if fm:
        tipo = {"a vencer": "a_vencer", "vencidos": "vencido"}.get(fm.group(1).lower(), "prejuizo")
        return {"tipo": tipo, "faixa": fm.group(2).replace("ate ", "até "), "valor": num(fm.group(3)), "codigo": fm.group(4)}
    if lm:
        return {"tipo": "limite", "faixa": lm.group(1), "valor": num(lm.group(2)), "codigo": lm.group(3)}
    return None


def extrai_dossie(linhas):
    ini = next(i for i, l in enumerate(linhas) if l.startswith("08 O P E R"))
    fim = next((i for i, l in enumerate(linhas) if l.startswith("C O M O L E R U M A") or l.startswith("09 C O N")), len(linhas))
    ops, cur = [], None
    for i in range(ini + 1, fim):
        l = linhas[i]
        cab = re.match(r"(.+?) R\$ ([\d.]+,\d{2})$", l)
        prox = linhas[i + 1] if i + 1 < fim else ""
        if cab and "código Bacen" in prox and not l.startswith("Cr"):
            cur = {"n": len(ops) + 1, "grupo": cab.group(1), "total": num(cab.group(2)), "faixas": []}
            mm = re.match(r"(?:(.*?) · )?código Bacen (\d+)", prox)
            cur["modalidade"] = (mm.group(1) or cab.group(1)).rstrip(".") if mm else cab.group(1)
            cur["cod_modalidade"], cur["cod_submodalidade"] = None, mm.group(2) if mm else None
            ops.append(cur)
            continue
        f = faixa_de(l) if cur else None
        if f:
            cur["faixas"].append(f)
    return ops


def extrai(pdf):
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    linhas = [re.sub(r"\s+", " ", l).strip() for l in txt.splitlines()]
    linhas = [l for l in linhas if l and not l.startswith("Ref. ")]
    if any(l.startswith("DOSSIÊ DE CRÉDITO") for l in linhas[:5]):
        return finaliza(extrai_dossie(linhas))
    ops, cur = [], None
    i = 0
    while i < len(linhas):
        l = linhas[i]
        m = re.match(r"O P E R A ?Ç ?Ã ?O (\d+)$", l)
        if m:
            cur = {"n": int(m.group(1)), "faixas": []}
            ops.append(cur)
            # próximas linhas: valor total, grupo + código
            vm = re.match(r"R\$ ([\d.]+,\d{2})", linhas[i + 1])
            cur["total"] = num(vm.group(1)) if vm else None
            gm = re.match(r"(.+?) (\d{2})$", linhas[i + 2])
            cur["grupo"] = gm.group(1) if gm else linhas[i + 2]
            i += 3
            continue
        if cur is not None:
            f = faixa_de(l)
            if f:
                cur["faixas"].append(f)
            elif l.startswith("MODALIDADE ("):
                mm = re.match(r"MODALIDADE \((\d+)\) SUB-MODALIDADE \((\d+)\)", l)
                if mm:
                    cur["cod_modalidade"], cur["cod_submodalidade"] = mm.group(1), mm.group(2)
                nomes = linhas[i + 1]
                g = cur.get("grupo", "")
                cur["modalidade"] = nomes[len(g):].strip() if nomes.startswith(g) else nomes
                i += 2
                continue
            elif l.startswith("PARTICIPAÇÃO NA CARTEIRA"):
                pm = re.search(r"([\d,]+)%", l)
                cur["participacao"] = pm.group(1) + "%" if pm else None
        i += 1
    return finaliza(ops)


def finaliza(ops):
    for o in ops:
        f = o["faixas"]
        o["a_vencer"] = round(sum(x["valor"] for x in f if x["tipo"] == "a_vencer"), 2)
        o["vencido"] = round(sum(x["valor"] for x in f if x["tipo"] == "vencido"), 2)
        o["prejuizo"] = round(sum(x["valor"] for x in f if x["tipo"] == "prejuizo"), 2)
        venc = [x["faixa"] for x in f if x["tipo"] == "vencido"]
        o["faixa_mais_antiga"] = venc[-1] if venc else None
        o["eh_limite"] = all(x["tipo"] == "limite" for x in f) and bool(f)
    return ops


if __name__ == "__main__":
    print(json.dumps(extrai(sys.argv[1]), ensure_ascii=False, indent=1))
