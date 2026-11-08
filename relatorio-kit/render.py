#!/usr/bin/env python3
"""Gera o Diagnóstico de Crédito e o Resumo da Planner a partir de um JSON.

Uso: python3 render.py dados.json pasta_saida [--modelos resumo,dossie]  (também: diagnostico, rating)
"""
import json, re, sys, asyncio, unicodedata
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).resolve().parent
ESCALA = ["AAA", "AA", "A", "BBB", "BB", "B", "C", "C-"]
CORES = {"AAA": "#2F6B4A", "AA": "#3F7355", "A": "#6C8A4A", "BBB": "#A8913E",
         "BB": "#B07D2B", "B": "#B8662F", "C": "#A94E3B", "C-": "#7E2F22"}
PARTICULAS = {"de", "da", "do", "das", "dos", "e"}


def brl(v):
    if v is None:
        return "—"
    s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def nivel(classe):
    return "ok" if classe in ("AAA", "AA", "A") else "warn" if classe in ("BBB", "BB") else "risk"


def titulo(nome):
    out = []
    for i, p in enumerate(nome.lower().split()):
        out.append(p if (i and p in PARTICULAS) else p.capitalize())
    return " ".join(out)


def mascara(doc):
    d = re.sub(r"\D", "", doc)
    if len(d) == 11:
        return f"{d[:3]}.***.***-{d[-2:]}"
    return doc


def prepara(d):
    c = d["cliente"]
    c.setdefault("nome_exibicao", titulo(c["nome"]))
    c["doc_mascarado"] = mascara(c["documento"])
    pl = d.setdefault("planner", {})
    pl.setdefault("especialista", "André Freitas")
    pl.setdefault("whatsapp", "(92) 99523-8398")
    pl["whatsapp_link"] = "55" + re.sub(r"\D", "", pl["whatsapp"])
    cl = d["classificacao"]
    cl["nivel"] = nivel(cl["classe"])
    cl["idx"] = ESCALA.index(cl["classe"]) if cl["classe"] in ESCALA else -1
    restr = [b for b in d["biros"] if b.get("qtd")]
    qtd = sum(b["qtd"] for b in restr)
    val = sum(b.get("valor") or 0 for b in restr)
    s = d["scr"]
    if s.get("prejuizo"):
        scr_st, scr_lv = f"Prejuízo de {brl(s['prejuizo'])}", "risk"
    elif s.get("vencido"):
        scr_st, scr_lv = f"Vencido: {brl(s['vencido'])}", "risk"
    else:
        scr_st, scr_lv = "Em dia", "ok"
    d["pilares"] = [
        {"n": "Pilar 1", "t": "Birôs e cartórios",
         "st": "Nada consta" if not qtd else f"{qtd} registro(s) · {brl(val)}",
         "lv": "ok" if not qtd else "risk", "p": "Serasa, SPC, Boa Vista, protestos e cheques"},
        {"n": "Pilar 2", "t": "SCR do Banco Central", "st": scr_st, "lv": scr_lv,
         "p": f"{s['instituicoes']} instituições · {s['operacoes']} operações"},
        {"n": "Pilar 3", "t": "Classificação de risco", "st": f"Classe {cl['classe']}", "lv": cl["nivel"],
         "p": f"Score {d['classificacao']['score']} de 1000"},
        {"n": "Pilar 4", "t": "Veredito", "st": cl.get("veredito", cl.get("sintese", "")), "lv": cl["nivel"],
         "p": cl.get("sintese", "")},
    ]
    d["restricoes_qtd"], d["restricoes_valor"] = qtd, val
    tot = (s.get("a_vencer") or 0) + (s.get("vencido") or 0) + (s.get("prejuizo") or 0)
    s["total"] = tot
    s["pct_av"] = 100 * (s.get("a_vencer") or 0) / tot if tot else 0
    s["pct_vd"] = 100 * (s.get("vencido") or 0) / tot if tot else 0
    s["pct_pj"] = 100 * (s.get("prejuizo") or 0) / tot if tot else 0
    for o in d["operacoes"]:
        o["pct_vencido"] = 100 * (o.get("vencido") or 0) / o["total"] if o.get("total") else 0
    d["consultas"]["total"] = sum(d["consultas"]["por_mes"])
    return d


MODELOS = {
    "diagnostico": ("diagnostico.html", "Diagnostico-de-Credito-Planner", False, "", False),
    "resumo": ("resumo.html", "Resumo-de-Credito-Planner", False, "", False),
    "dossie": ("dossie.html", "Dossie-de-Credito-Planner", True, "Dossiê de Crédito", True),
    "rating": ("rating.html", "Rating-Bancario-Planner", True, "Rating Bancário", False),
}


def faixa_html(titulo, rodape, logo_b64):
    head = (f'<div style="width:100%;height:14mm;margin:-0.4mm 0 0;background:#15182C;-webkit-print-color-adjust:exact;'
            f'display:flex;align-items:center;justify-content:space-between;padding:0 16mm;box-sizing:border-box;font-family:Montserrat,Arial">'
            f'<img src="data:image/png;base64,{logo_b64}" style="height:8mm">'
            f'<span style="font-size:7pt;letter-spacing:.18em;text-transform:uppercase;color:#E8CF8B">{titulo}</span></div>')
    foot = (f'<div style="width:100%;font-family:Montserrat,Arial;font-size:6.6pt;color:#8A8D9C;padding:0 16mm;box-sizing:border-box;'
            f'display:flex;justify-content:space-between"><span>{rodape}</span>'
            f'<span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>')
    return head, foot


def render(dados_path, out_dir, modelos=("resumo", "dossie")):
    import base64
    d = prepara(json.load(open(dados_path, encoding="utf-8")))
    env = Environment(loader=FileSystemLoader(BASE), autoescape=True)
    env.filters["brl"] = brl
    ctx = dict(d=d, ESCALA=ESCALA, CORES=CORES)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    ascii_nome = unicodedata.normalize("NFKD", d["cliente"]["nome_exibicao"]).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_nome).strip("-")
    data = d["consulta"]["data"].replace("/", "-")
    logo = base64.b64encode((BASE / "assets/logo-horizontal.png").read_bytes()).decode()
    rodape = f'Planner Consultoria · {d["cliente"]["nome_exibicao"]} · Consulta de {d["consulta"]["data"]}'
    alvos = []
    for m in modelos:
        tpl, prefixo, corrido, titulo, tem_capa = MODELOS[m]
        nome = f"{prefixo}-{slug}-{data}"
        html = BASE / f".{nome}.html"
        html.write_text(env.get_template(tpl).render(so_capa=False, **ctx), encoding="utf-8")
        capa = None
        if tem_capa:
            capa = BASE / f".{nome}-capa.html"
            capa.write_text(env.get_template(tpl).render(so_capa=True, **ctx), encoding="utf-8")
        alvos.append((html, out / f"{nome}.pdf", corrido, titulo, capa))

    async def imprime():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page()
            for html, pdf, corrido, titulo, capa in alvos:
                await pg.goto(html.as_uri())
                await pg.evaluate("document.fonts.ready")
                kw = dict(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
                if corrido:
                    h, f = faixa_html(titulo, rodape, logo)
                    kw.update(display_header_footer=True, header_template=h, footer_template=f)
                await pg.pdf(**kw)
                html.unlink()
                if capa:
                    import pikepdf
                    tmp = pdf.with_suffix(".capa.pdf")
                    await pg.goto(capa.as_uri())
                    await pg.evaluate("document.fonts.ready")
                    await pg.pdf(path=str(tmp), format="A4", print_background=True, prefer_css_page_size=True)
                    capa.unlink()
                    with pikepdf.open(pdf, allow_overwriting_input=True) as doc, pikepdf.open(tmp) as cv:
                        doc.pages[0] = cv.pages[0]
                        doc.save(pdf)
                    tmp.unlink()
                print(pdf)
            await b.close()
    asyncio.run(imprime())


if __name__ == "__main__":
    args = sys.argv[1:]
    mods = ("resumo", "dossie")
    if "--modelos" in args:
        i = args.index("--modelos"); mods = tuple(args[i + 1].split(",")); del args[i:i + 2]
    render(args[0], args[1] if len(args) > 1 else "out", mods)
