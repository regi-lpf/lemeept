# Project Overview & Universal Rules — LEME EPT

## 1. High-Level Architecture & Goal
- **System**: LEME is a WordPress (Elementor) portal preserving Professional & Technological Education (EPT) history and memory.
- **This Repository**: Contains two coupled fronts:
  1. **The Bibliometric Dashboard (`lemeept/index.html`)**: An embedded Elementor HTML/CSS/JS component (handling `fetch`, search filters, and metrics rendering) backed by static JSON databases (`painel-ept.json` legacy and `painel-ept-v2.json`).
  2. **The Extraction Pipeline (`lemeept/pipeline/` & root scripts)**: Python scripts that extract metadata from ProfEPT dissertations and eduCAPES.
- **Core Objective**: Transition from the legacy OCR + Generative AI (GPT) extraction workflow to a **deterministic, modular Python extraction pipeline** (native PDF text extraction + eduCAPES Handle API + heuristic classifiers + human review spreadsheets), reducing generative AI dependency to a strict fallback.
- **Modularity Principle**: Keep logic split into small, single-responsibility modules so local LLM agents can load and edit specific components within a strict 12k token context budget.

## 2. Domain & Pipeline Invariants
- **Discovery Source**: ProfEPT site API is the primary source for defenses (`defesas`), triggered manually.
- **New Review Flow**: Extracts native PDF text, queries eduCAPES Handle, and outputs JSON/spreadsheets. It MUST NOT run GPT/OCR automatically or auto-merge spreadsheet reviews into the final JSON. Use OCR strictly when native PDF text is missing. Keep the legacy OCR/GPT path available during transition.
- **Classification Contract**: Every classification requires `valor`, `confianca`, localizable `evidencia`, and `metodo`. Auto-accept ONLY `alta` (high) confidence; route medium/low or missing evidence to human review.
- **Epistemological Base (`base_epistemologica`)**: Requires conceptual evidence in the body text; mere presence in the bibliography is NOT proof.
- **Abstract & Keywords (`resumo`, `palavras-chave`)**: Flag extraction gaps (`falha/lacuna de extracao`) for PDF inspection rather than assuming absence.
- **Product Type (`tipo_produto`)**: Follow `GUIA_CLASSIFICACAO_PRODUTOS.md`. Preserve original labels/sources and log conflicts without destructive normalization.

## 3. Strict File & Data Safety Constraints
- **JSON Integrity**: Maintain the 220 production records linked to 110 defenses in `painel-ept-v2.json`. NEVER modify legacy `painel-ept.json` as a side effect. Never load full `.json`, `.csv`, or `.xlsx` data files into the LLM chat context.
- **Elementor Block (`lemeept/index.html`)**: Apply minimal surgical diffs. Preserve `<p>`, `<br>`, DOM IDs, CSS selectors, and fetch structure.
- **Artifact Protection**: Never auto-delete PDFs, spreadsheets, or human-reviewed files (`LIMPEZA_TEMPORARIOS.md`). Never `git push` without explicit confirmation.

## 4. On-Demand Documentation Map (Read Only When Needed)
- Data contract & provenance: `CONTRATO_DADOS.md`
- Current state & next steps: `CONTINUIDADE_TRABALHO.md`
- Architecture flows: `DIAGRAMAS.md`
- Product classification: `GUIA_CLASSIFICACAO_PRODUTOS.md`
- Pipeline execution: `GUIA_PIPELINE.md`
- Spreadsheet review: `GUIA_REVISAO.md`
