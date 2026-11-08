# Kit do relatório de crédito da Planner

Gera o **Diagnóstico de Crédito** (7 páginas) e o **Resumo** (1 página) na identidade da Planner a partir de um JSON com os dados da consulta.

```
pip install jinja2 playwright   # se faltar
python3 render.py exemplo.json saida/
```

O formato do JSON está em `exemplo.json` (dados fictícios). Nunca versionar JSON de cliente real neste repositório.
