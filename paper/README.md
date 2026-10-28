# Paper draft

Build with `latexmk -pdf main.tex`, or upload this folder to Overleaf.

The tables and figure in `generated/` come from the package. Regenerate them from a site table with

    python -m nycped paper --sites site_dataset.csv --poverty-moe tract_poverty_moe.csv \
        --crashes ped_harm_crashes.csv --tract-table tract_table.csv --out paper/generated

The files now in `generated/` hold numbers copied from `docs/CHECKS_LOG.md` and `docs/research_log.md`.
They are placeholders until that command has run on the final site table.
Text in `main.tex` quotes numbers by hand, so recheck it against `generated/numbers.json` after each regeneration.
Open items are marked TODO in `main.tex` and VERIFY in `references.bib`.
