# Documentation Overview

This directory contains all the documentation for the LEME EPT project. The documentation is organized into several files, each covering a specific aspect of the project.

## Files

- `CONTRATO_DADOS.md`: Describes the rules and provenance of the data.
- `DIAGRAMAS.md`: Describes the implemented and planned workflows.
- `CONTINUIDADE_TRABALHO.md`: Describes the current state of the work, recent decisions, and the next steps.
- `LIMPEZA_TEMPORARIOS.md`: Describes the inventory and retention policy.
- `GUIA_REVISAO.md`: Describes the manual review process.
- `GUIA_CLASSIFICACAO_PRODUTOS.md`: Describes the classification process for product types.
- `GUIA_PIPELINE.md`: Describes the pipeline transformation from the revised spreadsheet to the panel.

## Contributing

When making changes to the documentation, please follow these guidelines:

1. **Order of Reading**: Read the documents in the following order:
   1. `CONTRATO_DADOS.md`
   2. `DIAGRAMAS.md`
   3. `CONTINUIDADE_TRABALHO.md`
   4. `LIMPEZA_TEMPORARIOS.md`
   5. The specific guide for the task you are working on (`GUIA_REVISAO.md`, `GUIA_CLASSIFICACAO_PRODUTOS.md`, or `GUIA_PIPELINE.md`).

2. **Rules of Work**: Ensure that the API of the ProfEPT website is the source of discovery for defenses. The collection is initiated manually; there is no continuous automatic monitoring.
3. **OCR and GPT**: Use OCR only as a fallback when the native text does not cover the field. The legacy OCR/GPT flow should continue during the transition.
4. **Classification**: Classifications must have a value, confidence, evidence locatable, and method. For interpretative fields, accept only the high-confidence candidate; forward medium/below or lack of evidence for human review.
5. **Epistemological Basis**: Requires concept-based evidence in the text. Use bibliographic references to corroborate cited authors in the theoretical framework; the mere presence of a work in the bibliography does not prove the basis.
6. **Resumos and Keywords**: Expected according to the academic structure. If the extraction does not find them, flag failure/lack of extraction and forward to the PDF; do not conclude that they are absent from the dissertation without inspection.
7. **eduCAPES `dc.type` and Collection**: Are supplementary evidence. Do not automatically substitute the specific format declared in the dissertation/ficha do produto.
8. **Product Type**: Consult `GUIA_CLASSIFICACAO_PRODUTOS.md`; preserve the source and original label and register conflicts without forcing normalization.
9. **JSON and HTML**: Maintain the 220 independent records of production linked to 110 defenses in the JSON v2; do not alter the JSON consumed by the panel as a side effect.
10. **Elementor Shell**: Ensure minimal diffs and preserve its structure, especially `<p>`, `<br>`, IDs, selectors, and JSON loading.
11. **Inventory and Cleanup**: Consult `LIMPEZA_TEMPORARIOS.md` before removing any file. Do not delete PDFs, review spreadsheets, or historical artifacts with evidence/review human automatically.
12. **Publishing**: Publish `lemeept/index.html` in the Elementor widget. Host `lemeept/painel-ept.json` in an HTTPS URL that accepts anonymous GET, preferably on the same domain, and configure this URL in the `data-json-url` attribute of the shell. For another domain, the JSON server must allow CORS. In subsequent updates, replace only the JSON and invalidate the cache/CDN if necessary.

## Sources of Truth

- **Contract and Rules**: `CONTRATO_DADOS.md`.
- **Model and Workflow**: `DIAGRAMAS.md`.
- **Procedure and Work Status**: `CONTINUIDADE_TRABALHO.md`.
- **Inventory/Cleanup**: `LIMPEZA_TEMPORARIOS.md`.
- **Spreadsheet Review Execution**: `GUIA_REVISAO.md`.
