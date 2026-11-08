# Kit do relatório de crédito da Planner

Transforma a consulta da Concentre em PDFs com a identidade da Planner:

- **Resumo** (1 página): envio pelo WhatsApp e convite para a reunião de entrega.
- **Dossiê de Crédito** (cerca de 13 páginas): leitura da Planner, plano de prioridades e o relatório técnico completo.

Modelos opcionais: `diagnostico` (versão enxuta de 7 páginas) e `rating` (layout em cartões).

```
pip install jinja2 playwright pikepdf   # se faltar
python3 extrair_operacoes.py dossie-concentre.pdf > operacoes.json
python3 render.py dados.json saida/                      # resumo + dossiê
python3 render.py dados.json saida/ --modelos resumo,dossie,diagnostico,rating
```

O formato do JSON está em `exemplo.json` (dados 100% fictícios). Nunca versionar dados de cliente real neste repositório.
