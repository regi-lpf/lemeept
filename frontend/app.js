(function () {
    const raiz = document.getElementById("leme-painel-ept");
    if (!raiz || raiz.dataset.lemeInit === "1") return;
    raiz.dataset.lemeInit = "1";

    const I18N = {
        linha_pesquisa: {
            LP1: "LP1 – Práticas Educativas em EPT",
            LP2: "LP2 – Organização e Memórias de Espaços Pedagógicos"
        },
        macroprojeto: {
            MP1: "MP1 – Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT",
            MP2: "MP2 – Inclusão e diversidade em espaços formais e não formais de ensino na EPT",
            MP3: "MP3 – Práticas educativas no currículo integrado",
            MP4: "MP4 – História e memórias no contexto da EPT",
            MP5: "MP5 – Organização do currículo integrado na EPT",
            MP6: "MP6 – Organização de espaços pedagógicos na EPT"
        },
        tipo_produto: {
            material_didatico_instrucional: "Material Didático ou Instrucional",
            curso_oficina: "Curso ou Oficina de Formação Profissional",
            tecnologia_social: "Tecnologia Social",
            software_aplicativo: "Software ou Aplicativo",
            eventos_organizados: "Evento Organizado",
            acervo: "Acervo",
            produto_comunicacao: "Produto de Comunicação",
            manual_protocolo: "Manual ou Protocolo",
            carta_mapa: "Carta, Mapa ou Similar"
        },
        publico_alvo: {
            docentes_professores: "Docentes e Professores",
            estudantes_alunos: "Estudantes e Alunos",
            gestores_coordenadores: "Gestores e Coordenadores Escolares",
            tecnicos_profissionais_educacao: "Técnicos e Profissionais da Educação",
            comunidade_externa: "Comunidade Externa"
        },
        fonte_tipo: {
            dissertacao_ficha: "Ficha / texto da dissertação",
            educapes_dc_type: "Metadado dc.type (eduCAPES)",
            inferencia_llm: "Inferência assistida (LLM)"
        }
    };

    const HTML_ESCAPE_MAP = {
        "&": "\u0026amp;",
        "<": "\u0026lt;",
        ">": "\u0026gt;",
        '"': "\u0026quot;",
        "'": "\u0026#39;"
    };

    const FACET_FIELDS = [
        "ano", "linha_pesquisa", "macroprojeto", "orientador", "coorientador",
        "base_epistemologica", "autor_referenciado",
        "tipo_produto", "formato_produto", "publico_alvo", "nivel_aplicacao"
    ];
    const EMPTY_SET = new Set();

    let dados = [];
    let dadosPorId = new Map();
    let orientadoresPorChave = new Map();
    let coorientadoresPorChave = new Map();
    let indiceFacetas = new Map();
    let metaRaiz = { total_defesas: 0, total_producoes: 0, gerado_em: "" };
    let resultadosAtuais = [];
    let escopo = "todas";
    let ordenacao = "ano_desc";
    let modo = "cards";
    const MULTI_SELECT_SENTINEL = "__leme_multi__";
    const filtrosSelecionados = new Map(FACET_FIELDS.map(c => [c, new Set()]));
    let modoCardOrientador = "orientador";
    let modoCardTipoProduto = "tipo_produto";
    let paginaAtual = 1;
    let debounceTimer = null;
    let ultimoFocoAntesModal = null;
    let bodyOverflowAnterior = "";
    const itensPorPagina = 12;
    const rankingPorPagina = 30; // Paginação do modal de ranking (ajustável para 30 ou 50)
    const RANKING_CORTES = [1, 2, 5, 10];
    let estadoModalRanking = null;
    const mqMobile = window.matchMedia("(max-width: 720px)");

    const busca = raiz.querySelector("#leme-busca");
    const limpar = raiz.querySelector("#leme-limpar");
    const ordenarSelect = raiz.querySelector("#leme-ordenar");
    const resultados = raiz.querySelector("#leme-resultados");
    const paginacao = raiz.querySelector("#leme-paginacao");
    const contador = raiz.querySelector("#leme-contador");
    const periodoEl = raiz.querySelector("#leme-periodo");
    const geradoEmEl = raiz.querySelector("#leme-gerado-em");
    const statTotalEl = raiz.querySelector("#leme-stat-total");
    const statProducoesEl = raiz.querySelector("#leme-stat-producoes");
    const statOrientadoresEl = raiz.querySelector("#leme-stat-orientadores");
    const statCoorientadoresEl = raiz.querySelector("#leme-stat-coorientadores");
    const statMacroprojetosEl = raiz.querySelector("#leme-stat-macroprojetos");
    const filtros = Array.from(raiz.querySelectorAll("select[data-campo]"));
    const botoesEscopo = Array.from(raiz.querySelectorAll(".leme-scope button[data-escopo]"));
    const chartsGridEl = raiz.querySelector(".leme-charts-grid");
    const chartCards = Array.from(raiz.querySelectorAll(".leme-chart-card[data-chart-scope]"));
    const chartAnoEl = raiz.querySelector("#leme-chart-ano");
    const chartLinhaEl = raiz.querySelector("#leme-chart-linha");
    const chartMacroEl = raiz.querySelector("#leme-chart-macro");
    const chartOrientadorEl = raiz.querySelector("#leme-chart-orientador");
    const chartOrientadorSubtitleEl = raiz.querySelector("#leme-chart-orientador-subtitle");
    const tabCoorCountEl = raiz.querySelector("#leme-tab-coor-count");
    const botoesTabOrientador = Array.from(raiz.querySelectorAll(".leme-chart-tab[data-orientador-tab]"));
    const chartBaseEl = raiz.querySelector("#leme-chart-base");
    const chartAutoresRefEl = raiz.querySelector("#leme-chart-autores-ref");
    const chartTipoEl = raiz.querySelector("#leme-chart-tipo");
    const chartTipoTitleEl = raiz.querySelector("#leme-chart-tipo-title");
    const chartTipoHeadEl = raiz.querySelector("#leme-chart-tipo-head");
    const chartTipoSubtitleEl = raiz.querySelector("#leme-chart-tipo-subtitle");
    const botoesTabTipoProduto = Array.from(raiz.querySelectorAll(".leme-chart-tab[data-tipo-tab]"));
    const chartPublicoEl = raiz.querySelector("#leme-chart-publico");
    const chartNivelEl = raiz.querySelector("#leme-chart-nivel");
    const chartFormatoEl = raiz.querySelector("#leme-chart-formato");
    const graficosFiltrosEl = raiz.querySelector("#leme-graficos-filtros");
    const filtrosAtivos = raiz.querySelector("#leme-filtros-ativos");
    const graficosNota = raiz.querySelector("#leme-graficos-nota");
    const graficosDesc = raiz.querySelector("#leme-graficos-desc");
    const chartAnoTitle = raiz.querySelector("#leme-chart-ano-title");
    const insights = raiz.querySelector("#leme-insights");
    const exportarCsv = raiz.querySelector("#leme-exportar-csv");
    const btnCards = raiz.querySelector("#leme-view-cards");
    const btnTable = raiz.querySelector("#leme-view-table");
    const modalBackdrop = raiz.querySelector("#leme-modal-backdrop");
    const modalEl = raiz.querySelector(".leme-modal");
    const modalContent = raiz.querySelector("#leme-modal-content");
    const modalTitle = raiz.querySelector("#leme-modal-title");
    const modalClose = raiz.querySelector("#leme-modal-close");
    const botoesExpandirRanking = Array.from(raiz.querySelectorAll(".leme-chart-expand-btn[data-open-ranking]"));
    const btnExpandOrientador = raiz.querySelector('.leme-chart-expand-btn[data-open-ranking="orientador"]');
    const btnExpandAutoresRef = raiz.querySelector('.leme-chart-expand-btn[data-open-ranking="autor_referenciado"]');
    const btnExpandTipoFormato = raiz.querySelector("#leme-expand-tipo-formato");
    const btnExpandFormato = raiz.querySelector("#leme-expand-formato");

    function normalizarBusca(valor) {
        return String(valor || "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function termosBusca() {
        const termo = normalizarBusca(busca.value || "");
        return termo ? termo.split(" ").filter(Boolean) : [];
    }

    function escapeHtml(valor) {
        if (valor === null || valor === undefined) return "";
        return String(valor).replace(/[&<>"']/g, ch => HTML_ESCAPE_MAP[ch]);
    }

    function sanitizarUrl(valor) {
        const texto = String(valor || "").trim();
        if (!texto) return "";
        try {
            const parsed = new URL(texto);
            return (parsed.protocol === "https:" || parsed.protocol === "http:") ? parsed.href : "";
        } catch (_) {
            return "";
        }
    }

    function ehValorPublico(valor) {
        if (valor === null || valor === undefined) return false;
        const texto = String(valor).replace(/\s+/g, " ").trim();
        return Boolean(texto && texto !== "---" && normalizarBusca(texto) !== "a revisar");
    }

    function limparRotulo(valor) {
        return String(valor || "").replace(/\s+/g, " ").trim();
    }

    function limparNomePessoa(valor) {
        return limparRotulo(valor).replace(/^[:;.,\-\s]+|[:;.,\-\s]+$/g, "").trim();
    }

    function valorPublico(valor, fallback) {
        return ehValorPublico(valor) ? limparRotulo(valor) : (fallback || "Não informado");
    }

    function traduzirSlug(grupo, slug) {
        if (!ehValorPublico(slug)) return "";
        const mapa = I18N[grupo] || {};
        return mapa[slug] || limparRotulo(slug);
    }

    function labelCurto(valor, limite) {
        const texto = limparRotulo(valor);
        return texto.length > limite ? texto.slice(0, limite - 1).trim() + "…" : texto;
    }

    function formatarInstituicaoCampus(instituicao, campus) {
        const inst = limparRotulo(instituicao);
        let camp = limparRotulo(campus);
        if (!inst && !camp) return "Não informada";
        if (!camp) return inst;
        if (!inst) return camp;
        if (normalizarBusca(inst) === normalizarBusca(camp)) return inst;
        if (/\bIFC\b/i.test(inst)) {
            camp = camp.replace(/^IFC\s*[-–—:]?\s*/i, "").trim();
        }
        if (camp && !/^campus\b/i.test(camp)) {
            camp = "Campus " + camp;
        }
        return camp ? inst + " – " + camp : inst;
    }

    function formatarDataIsoBr(valor) {
        const texto = String(valor || "").trim();
        if (!texto) return "";
        const dt = new Date(texto);
        if (Number.isNaN(dt.getTime())) return "";
        return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(dt);
    }

    function formatarDataPublicacao(valor) {
        const texto = String(valor || "").trim();
        if (!texto) return "";
        if (/^\d{4}-\d{2}-\d{2}$/.test(texto)) {
            const p = texto.split("-");
            return p[2] + "/" + p[1] + "/" + p[0];
        }
        if (/^\d{4}-\d{2}$/.test(texto)) {
            const p = texto.split("-");
            return p[1] + "/" + p[0];
        }
        return texto;
    }

    function normalizarRegistroV4(d) {
        const diss = d.dissertacao || {};
        const prod = d.produto || {};
        const baseObj = diss.base_epistemologica || {};
        const indice = d.indice_busca || {};
        const prov = prod.proveniencia || {};

        const revisaoPendente = Boolean(baseObj.revisao_pendente);
        const curadoHumano = Boolean(baseObj.curado_humano);
        const baseAprovada = !revisaoPendente && ehValorPublico(baseObj.valor)
            ? limparRotulo(baseObj.valor)
            : "";
        const baseStatusLabel = baseAprovada || (revisaoPendente ? "Em curadoria" : "Não declarada explicitamente");

        const evidencias = baseAprovada && Array.isArray(baseObj.evidencias)
            ? baseObj.evidencias
                .filter(ev => ev && ehValorPublico(ev.trecho))
                .map(ev => ({
                    secao: limparRotulo(ev.secao),
                    pagina: ev.pagina,
                    trecho: limparRotulo(ev.trecho),
                    referencia_correspondente: ehValorPublico(ev.referencia_correspondente) ? limparRotulo(ev.referencia_correspondente) : ""
                }))
            : [];

        const publicosSlugs = Array.isArray(prod.publico_alvo)
            ? prod.publico_alvo.filter(ehValorPublico)
            : [];
        const publicosLabels = publicosSlugs.map(s => traduzirSlug("publico_alvo", s));

        const autoresRef = Array.isArray(diss.autores_referenciados)
            ? diss.autores_referenciados.map(limparRotulo).filter(ehValorPublico)
            : [];

        const termosUnificados = (Array.isArray(indice.termos_unificados) && indice.termos_unificados.length
            ? indice.termos_unificados
            : Array.from(new Set([...(diss.palavras_chave || []), ...(prod.palavras_chave || [])]))
        ).map(limparRotulo).filter(ehValorPublico);

        const autorLimpo = limparNomePessoa(d.autor);
        const orientadorLimpo = limparNomePessoa(d.orientador);
        const coorientadoresMap = new Map();
        if (Array.isArray(d.coorientadores)) {
            d.coorientadores.forEach(nomeBruto => {
                const limpo = limparNomePessoa(nomeBruto);
                if (!ehValorPublico(limpo)) return;
                const chave = normalizarBusca(limpo);
                if (chave && !coorientadoresMap.has(chave)) {
                    coorientadoresMap.set(chave, limpo);
                }
            });
        }
        const coorientadores = Array.from(coorientadoresMap.values());
        const coorientadoresChaves = Array.from(coorientadoresMap.keys());

        const linhaSlug = ehValorPublico(d.linha_pesquisa) ? String(d.linha_pesquisa).trim() : "";
        const linhaLabel = traduzirSlug("linha_pesquisa", linhaSlug);
        const macroSlug = ehValorPublico(d.macroprojeto) ? String(d.macroprojeto).trim() : "";
        const macroLabel = traduzirSlug("macroprojeto", macroSlug);
        const tipoSlug = ehValorPublico(prod.tipo) ? String(prod.tipo).trim() : "";
        const tipoLabel = traduzirSlug("tipo_produto", tipoSlug);
        const formatoProduto = ehValorPublico(prod.formato) ? limparRotulo(prod.formato) : "";
        const nivelAplicacao = ehValorPublico(prod.nivel_aplicacao) ? limparRotulo(prod.nivel_aplicacao) : "";
        const instituicaoCampus = formatarInstituicaoCampus(d.instituicao, d.campus);

        const extrasBusca = normalizarBusca([
            d.instituicao,
            d.campus,
            instituicaoCampus,
            orientadorLimpo,
            coorientadores.join(" "),
            linhaSlug,
            linhaLabel,
            macroSlug,
            macroLabel,
            tipoSlug,
            tipoLabel,
            formatoProduto,
            publicosSlugs.join(" "),
            publicosLabels.join(" "),
            baseAprovada,
            nivelAplicacao
        ].join(" "));

        let textoBuscaNorm = String(indice.texto_busca_normalizado || "").trim();
        if (!textoBuscaNorm) {
            textoBuscaNorm = normalizarBusca([
                d.id, d.ano, autorLimpo, orientadorLimpo,
                coorientadores.join(" "),
                d.instituicao, d.campus, instituicaoCampus,
                linhaSlug, linhaLabel,
                macroSlug, macroLabel,
                diss.titulo, diss.resumo, autoresRef.join(" "), baseAprovada,
                prod.titulo, tipoSlug, tipoLabel, formatoProduto,
                publicosSlugs.join(" "), publicosLabels.join(" "),
                nivelAplicacao, termosUnificados.join(" ")
            ].join(" "));
        } else if (extrasBusca) {
            textoBuscaNorm = textoBuscaNorm + " " + extrasBusca;
        }

        const identificadores = Array.isArray(prod.identificadores)
            ? prod.identificadores
                .filter(i => i && ehValorPublico(i.valor))
                .map(i => ({
                    esquema: limparRotulo(i.esquema),
                    valor: limparRotulo(i.valor),
                    url: sanitizarUrl(i.url)
                }))
            : [];

        const autoresColaboradores = Array.isArray(prod.autores_colaboradores)
            ? prod.autores_colaboradores
                .filter(a => a && ehValorPublico(a.nome))
                .map(a => ({
                    nome: limparRotulo(a.nome),
                    papel: ehValorPublico(a.papel) ? limparRotulo(a.papel) : ""
                }))
            : [];

        return {
            id: limparRotulo(d.id),
            ano: d.ano != null ? String(d.ano) : "",
            anoNum: Number.isFinite(Number(d.ano)) ? Number(d.ano) : 0,
            autor: autorLimpo,
            orientador: orientadorLimpo,
            orientadorChave: normalizarBusca(orientadorLimpo),
            coorientadores: coorientadores,
            coorientadoresChaves: coorientadoresChaves,
            instituicaoCampus: instituicaoCampus,
            linha_pesquisa: linhaSlug,
            linha_pesquisa_label: linhaLabel,
            macroprojeto: macroSlug,
            macroprojeto_label: macroLabel,
            dissertacao_titulo: limparRotulo(diss.titulo),
            dissertacao_link: sanitizarUrl(diss.link),
            dissertacao_resumo: limparRotulo(diss.resumo),
            autores_referenciados: autoresRef,
            base_epistemologica: baseAprovada,
            base_revisao_pendente: revisaoPendente,
            base_curado_humano: curadoHumano,
            base_status_label: baseStatusLabel,
            base_justificativa: baseAprovada && ehValorPublico(baseObj.justificativa) ? limparRotulo(baseObj.justificativa) : "",
            base_evidencias: evidencias,
            produto_titulo: limparRotulo(prod.titulo),
            tipo_produto: tipoSlug,
            tipo_produto_label: tipoLabel,
            formato_produto: formatoProduto,
            produto_link: sanitizarUrl(prod.link),
            publico_alvo: publicosSlugs,
            publico_alvo_labels: publicosLabels,
            nivel_aplicacao: nivelAplicacao,
            data_publicacao: limparRotulo(prod.data_publicacao),
            autores_colaboradores: autoresColaboradores,
            identificadores: identificadores,
            proveniencia: {
                fonte_tipo_escolhida: limparRotulo(prov.fonte_tipo_escolhida),
                rotulo_original_declarado: ehValorPublico(prov.rotulo_original_declarado) ? limparRotulo(prov.rotulo_original_declarado) : "",
                colecao_educapes: ehValorPublico(prov.colecao_educapes) ? limparRotulo(prov.colecao_educapes) : "",
                dc_type_educapes: Array.isArray(prov.dc_type_educapes) ? prov.dc_type_educapes.map(limparRotulo).filter(ehValorPublico) : []
            },
            termos_unificados: termosUnificados,
            texto_busca_normalizado: textoBuscaNorm
        };
    }

    function registrarGrafia(contagens, chave, nome) {
        if (!chave || !ehValorPublico(nome)) return;
        if (!contagens.has(chave)) contagens.set(chave, new Map());
        const mapaGrafias = contagens.get(chave);
        mapaGrafias.set(nome, (mapaGrafias.get(nome) || 0) + 1);
    }

    function resolverMapaCanonico(contagens) {
        const saida = new Map();
        contagens.forEach((mapaGrafias, chave) => {
            const melhor = Array.from(mapaGrafias.entries())
                .sort((a, b) => b[1] - a[1] || a[0].length - b[0].length)[0][0];
            saida.set(chave, melhor);
        });
        return saida;
    }

    function consolidarOrientadores(lista) {
        const contagensOri = new Map();
        const contagensCoor = new Map();
        lista.forEach(item => {
            registrarGrafia(contagensOri, item.orientadorChave, item.orientador);
            for (let j = 0; j < item.coorientadoresChaves.length; j++) {
                registrarGrafia(contagensCoor, item.coorientadoresChaves[j], item.coorientadores[j]);
            }
        });

        orientadoresPorChave = resolverMapaCanonico(contagensOri);
        coorientadoresPorChave = resolverMapaCanonico(contagensCoor);

        lista.forEach(item => {
            if (item.orientadorChave && orientadoresPorChave.has(item.orientadorChave)) {
                item.orientador = orientadoresPorChave.get(item.orientadorChave);
            }
            if (item.coorientadoresChaves.length) {
                item.coorientadores = item.coorientadoresChaves.map((ch, idx) =>
                    coorientadoresPorChave.get(ch) || item.coorientadores[idx]
                );
            }
        });
    }

    function highlightText(valor, termos) {
        const textoOriginal = String(valor || "");
        const listaTermos = termos || termosBusca();
        if (!listaTermos.length || !textoOriginal) return escapeHtml(textoOriginal);

        const normRapido = normalizarBusca(textoOriginal);
        if (!listaTermos.some(t => normRapido.includes(t))) {
            return escapeHtml(textoOriginal);
        }

        const chars = Array.from(textoOriginal);
        let normStr = "";
        const charMap = [];

        chars.forEach((ch, origIdx) => {
            const normCh = ch.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9\s]/g, " ");
            for (let i = 0; i < normCh.length; i++) {
                normStr += normCh[i];
                charMap.push(origIdx);
            }
        });

        const ranges = [];
        listaTermos.forEach(termo => {
            let inicio = 0;
            while (inicio < normStr.length) {
                const idx = normStr.indexOf(termo, inicio);
                if (idx === -1) break;
                const origStart = charMap[idx];
                const origEnd = charMap[idx + termo.length - 1] + 1;
                ranges.push([origStart, origEnd]);
                inicio = idx + termo.length;
            }
        });

        if (!ranges.length) return escapeHtml(textoOriginal);
        ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1]);

        const mesclados = [];
        ranges.forEach(range => {
            const ultimo = mesclados[mesclados.length - 1];
            if (!ultimo || range[0] > ultimo[1]) mesclados.push(range);
            else ultimo[1] = Math.max(ultimo[1], range[1]);
        });

        let saida = "";
        let cursor = 0;
        mesclados.forEach(([ini, fim]) => {
            saida += escapeHtml(chars.slice(cursor, ini).join(""));
            saida += '<mark class="leme-highlight">' + escapeHtml(chars.slice(ini, fim).join("")) + '</mark>';
            cursor = fim;
        });
        saida += escapeHtml(chars.slice(cursor).join(""));
        return saida;
    }

    function trechoResumoCard(resumo, termos, limite) {
        const texto = limparRotulo(resumo);
        const max = limite || 380;
        if (!texto || texto.length <= max) return texto;
        if (!termos || !termos.length) return labelCurto(texto, max);

        const norm = normalizarBusca(texto);
        let menorPos = -1;
        termos.forEach(t => {
            const pos = norm.indexOf(t);
            if (pos !== -1 && (menorPos === -1 || pos < menorPos)) menorPos = pos;
        });

        if (menorPos === -1 || menorPos < Math.floor(max * 0.65)) {
            return labelCurto(texto, max);
        }

        const approxOrig = Math.floor((menorPos / Math.max(norm.length, 1)) * texto.length);
        let ini = Math.max(0, approxOrig - 110);
        if (ini > 0) {
            const espaco = texto.lastIndexOf(" ", ini);
            if (espaco > ini - 30) ini = espaco + 1;
        }
        const fim = Math.min(texto.length, ini + max);
        const miolo = texto.slice(ini, fim).trim();
        return (ini > 0 ? "… " : "") + miolo + (fim < texto.length ? "…" : "");
    }

    function multiplicadorEscopo() {
        return escopo === "todas" ? 2 : 1;
    }

    function contarDefesasComCoorientacao(lista) {
        let total = 0;
        for (let i = 0; i < lista.length; i++) {
            if (lista[i].coorientadoresChaves.length) total++;
        }
        return total;
    }

    function atualizarIndicadores() {
        const anos = dados.map(item => item.anoNum).filter(n => n > 0);
        const periodo = anos.length ? Math.min(...anos) + "–" + Math.max(...anos) : "Sem ano informado";
        const totalDefesas = metaRaiz.total_defesas || dados.length;
        const totalProducoes = metaRaiz.total_producoes || (totalDefesas * 2);
        const dataGeracao = formatarDataIsoBr(metaRaiz.gerado_em);

        periodoEl.textContent = periodo;
        geradoEmEl.textContent = dataGeracao ? ("Atualizado em " + dataGeracao) : "";
        statTotalEl.textContent = totalDefesas.toLocaleString("pt-BR");
        statProducoesEl.textContent = totalProducoes.toLocaleString("pt-BR");
        statOrientadoresEl.textContent = orientadoresPorChave.size.toLocaleString("pt-BR");
        if (statCoorientadoresEl) {
            const totalCoor = coorientadoresPorChave.size;
            const defsCoor = contarDefesasComCoorientacao(dados);
            statCoorientadoresEl.textContent = totalCoor > 0
                ? ("+ " + totalCoor.toLocaleString("pt-BR") + (totalCoor === 1 ? " coorientador" : " coorientadores") + " (" + defsCoor.toLocaleString("pt-BR") + (defsCoor === 1 ? " defesa" : " defesas") + ")")
                : "0 coorientadores";
        }
        statMacroprojetosEl.textContent = new Set(
            dados.map(item => item.macroprojeto).filter(ehValorPublico)
        ).size.toLocaleString("pt-BR");
    }

    function construirIndiceFacetas(lista) {
        indiceFacetas = new Map(FACET_FIELDS.map(c => [c, new Map()]));
        const adicionar = (campo, chave, idx) => {
            const mapa = indiceFacetas.get(campo);
            let set = mapa.get(chave);
            if (!set) {
                set = new Set();
                mapa.set(chave, set);
            }
            set.add(idx);
        };

        for (let i = 0; i < lista.length; i++) {
            const item = lista[i];
            item._idx = i;
            if (ehValorPublico(item.ano)) adicionar("ano", item.ano, i);
            if (ehValorPublico(item.linha_pesquisa)) adicionar("linha_pesquisa", item.linha_pesquisa, i);
            if (ehValorPublico(item.macroprojeto)) adicionar("macroprojeto", item.macroprojeto, i);
            if (item.orientadorChave) adicionar("orientador", item.orientadorChave, i);
            for (let j = 0; j < item.coorientadoresChaves.length; j++) {
                adicionar("coorientador", item.coorientadoresChaves[j], i);
            }
            if (ehValorPublico(item.base_epistemologica)) adicionar("base_epistemologica", item.base_epistemologica, i);
            for (let j = 0; j < item.autores_referenciados.length; j++) {
                const a = item.autores_referenciados[j];
                if (ehValorPublico(a)) adicionar("autor_referenciado", a, i);
            }
            if (ehValorPublico(item.tipo_produto)) adicionar("tipo_produto", item.tipo_produto, i);
            if (ehValorPublico(item.formato_produto)) adicionar("formato_produto", item.formato_produto, i);
            for (let j = 0; j < item.publico_alvo.length; j++) {
                const p = item.publico_alvo[j];
                if (ehValorPublico(p)) adicionar("publico_alvo", p, i);
            }
            if (ehValorPublico(item.nivel_aplicacao)) adicionar("nivel_aplicacao", item.nivel_aplicacao, i);
        }
    }

    function intersecarSets(sets) {
        if (!sets.length) return null;
        for (let i = 0; i < sets.length; i++) {
            if (!sets[i] || !sets[i].size) return [];
        }
        const ordenados = sets.slice().sort((a, b) => a.size - b.size);
        const menor = ordenados[0];
        const resultado = [];
        menor.forEach(idx => {
            for (let j = 1; j < ordenados.length; j++) {
                if (!ordenados[j].has(idx)) return;
            }
            resultado.push(idx);
        });
        return resultado;
    }

    function obterValoresFiltroAtivo(campo) {
        return (campo && filtrosSelecionados.get(campo)) || EMPTY_SET;
    }

    function prefixoAcaoFiltro(ativo, qtdAtivos) {
        if (ativo) return "Remover filtro: ";
        return qtdAtivos > 0 ? "Adicionar filtro: " : "Filtrar por ";
    }

    function temAlgumFiltroFaceta(ignorarCampo) {
        for (let i = 0; i < FACET_FIELDS.length; i++) {
            const campo = FACET_FIELDS[i];
            if (ignorarCampo && campo === ignorarCampo) continue;
            const set = filtrosSelecionados.get(campo);
            if (set && set.size > 0) return true;
        }
        return false;
    }

    function obterUniaoIndicesFaceta(campo, valoresSet) {
        if (!valoresSet || !valoresSet.size) return EMPTY_SET;
        const mapaCampo = indiceFacetas.get(campo);
        if (!mapaCampo) return EMPTY_SET;
        if (valoresSet.size === 1) {
            const unico = valoresSet.values().next().value;
            return mapaCampo.get(unico) || EMPTY_SET;
        }
        const uniao = new Set();
        valoresSet.forEach(val => {
            const s = mapaCampo.get(val);
            if (s) s.forEach(idx => uniao.add(idx));
        });
        return uniao;
    }

    function limparTodosFiltros() {
        busca.value = "";
        filtrosSelecionados.forEach(set => set.clear());
        aplicarFiltros(true);
    }

    function filtrarIndicesPorFacetas(ignorarCampo) {
        const sets = [];
        for (let i = 0; i < FACET_FIELDS.length; i++) {
            const campo = FACET_FIELDS[i];
            if (ignorarCampo && campo === ignorarCampo) continue;
            const selecionados = filtrosSelecionados.get(campo);
            if (!selecionados || !selecionados.size) continue;
            const s = obterUniaoIndicesFaceta(campo, selecionados);
            if (!s.size) return [];
            sets.push(s);
        }
        if (!sets.length) return null;
        return intersecarSets(sets);
    }

    function obterListaGraficoFaceta(campo, listaPadrao, termos, indicesBuscaSet) {
        if (!campo || obterValoresFiltroAtivo(campo).size === 0) return listaPadrao;
        return filtrarDados(campo, termos, indicesBuscaSet);
    }

    function calcularIndicesBuscaSet(listaTermos) {
        if (!listaTermos || !listaTermos.length) return null;
        const set = new Set();
        for (let i = 0; i < dados.length; i++) {
            const tb = dados[i].texto_busca_normalizado;
            let ok = true;
            for (let t = 0; t < listaTermos.length; t++) {
                if (!tb.includes(listaTermos[t])) { ok = false; break; }
            }
            if (ok) set.add(i);
        }
        return set;
    }

    function itemCorrespondeTermos(item, listaTermos) {
        for (let t = 0; t < listaTermos.length; t++) {
            if (!item.texto_busca_normalizado.includes(listaTermos[t])) return false;
        }
        return true;
    }

    function filtrarDados(ignorarCampo, termosPreCalculados, indicesBuscaSet) {
        const listaTermos = termosPreCalculados || termosBusca();
        const indicesFac = filtrarIndicesPorFacetas(ignorarCampo);

        if (indicesFac !== null) {
            if (!indicesFac.length) return [];
            if (!listaTermos.length) return indicesFac.map(idx => dados[idx]);
            const out = [];
            for (let i = 0; i < indicesFac.length; i++) {
                const idx = indicesFac[i];
                if (indicesBuscaSet ? indicesBuscaSet.has(idx) : itemCorrespondeTermos(dados[idx], listaTermos)) {
                    out.push(dados[idx]);
                }
            }
            return out;
        }

        if (!listaTermos.length) return dados;
        if (indicesBuscaSet) return Array.from(indicesBuscaSet, idx => dados[idx]);
        return dados.filter(item => itemCorrespondeTermos(item, listaTermos));
    }

    function formatarOpcaoFiltro(campo, valor) {
        if (campo === "linha_pesquisa") return traduzirSlug("linha_pesquisa", valor);
        if (campo === "macroprojeto") return traduzirSlug("macroprojeto", valor);
        if (campo === "tipo_produto") return traduzirSlug("tipo_produto", valor);
        if (campo === "publico_alvo") return traduzirSlug("publico_alvo", valor);
        if (campo === "orientador") return orientadoresPorChave.get(valor) || valor;
        if (campo === "coorientador") return coorientadoresPorChave.get(valor) || valor;
        return valor;
    }

    function ordenarOpcoesFiltro(campo, entradas) {
        if (campo === "ano") {
            return entradas.sort((a, b) => Number(b[0]) - Number(a[0]));
        }
        return entradas.sort((a, b) =>
            formatarOpcaoFiltro(campo, a[0]).localeCompare(formatarOpcaoFiltro(campo, b[0]), "pt-BR")
        );
    }

    function contarOpcoes(lista, campo) {
        const mapa = new Map();
        lista.forEach(item => {
            if (campo === "publico_alvo") {
                item.publico_alvo.forEach(slug => {
                    if (!ehValorPublico(slug)) return;
                    mapa.set(slug, (mapa.get(slug) || 0) + 1);
                });
                return;
            }
            if (campo === "orientador") {
                if (!item.orientadorChave) return;
                mapa.set(item.orientadorChave, (mapa.get(item.orientadorChave) || 0) + 1);
                return;
            }
            const valor = item[campo];
            if (!ehValorPublico(valor)) return;
            mapa.set(valor, (mapa.get(valor) || 0) + 1);
        });
        return ordenarOpcoesFiltro(campo, Array.from(mapa.entries()));
    }

    function popularFiltrosDinamicos(termos, indicesBuscaSet) {
        const listaTermos = termos || termosBusca();
        const temFiltroAtivo = temAlgumFiltroFaceta();
        const baseSemFiltros = (!temFiltroAtivo && listaTermos.length)
            ? Array.from(indicesBuscaSet || calcularIndicesBuscaSet(listaTermos), idx => dados[idx])
            : null;

        filtros.forEach(select => {
            const campo = select.dataset.campo;
            const selecionados = obterValoresFiltroAtivo(campo);
            const semOutrosFiltros = !temAlgumFiltroFaceta(campo) && !listaTermos.length;
            let base = null;
            let opcoes;
            if (semOutrosFiltros) {
                const mapaCampo = indiceFacetas.get(campo) || new Map();
                opcoes = ordenarOpcoesFiltro(campo, Array.from(mapaCampo.entries(), ([k, s]) => [k, s.size]));
            } else {
                base = baseSemFiltros || filtrarDados(campo, listaTermos, indicesBuscaSet);
                opcoes = contarOpcoes(base, campo);
            }
            const mapaContagem = new Map(opcoes);
            const padrao = select.dataset.default || "Todos";

            let html = '<option value="">' + escapeHtml(padrao) + '</option>';
            if (selecionados.size > 1) {
                html += '<option value="' + MULTI_SELECT_SENTINEL + '">' + selecionados.size + ' ' + (padrao === "Todas" ? "selecionadas" : "selecionados") + '</option>';
            }

            opcoes.forEach(([chave]) => {
                const rotulo = formatarOpcaoFiltro(campo, chave);
                const prefixo = (selecionados.size > 1 && selecionados.has(chave)) ? "✓ " : "";
                html += '<option value="' + escapeHtml(chave) + '">' + escapeHtml(prefixo + rotulo) + '</option>';
            });

            selecionados.forEach(valor => {
                if (!mapaContagem.has(valor)) {
                    const prefixo = selecionados.size > 1 ? "✓ " : "";
                    html += '<option value="' + escapeHtml(valor) + '">' + escapeHtml(prefixo + formatarOpcaoFiltro(campo, valor)) + '</option>';
                }
            });

            select.innerHTML = html;
            if (selecionados.size === 0) {
                select.value = "";
            } else if (selecionados.size === 1) {
                select.value = selecionados.values().next().value;
            } else {
                select.value = MULTI_SELECT_SENTINEL;
            }
            select.disabled = opcoes.length === 0 && selecionados.size === 0;

            const field = select.closest(".leme-field");
            if (field) {
                let countEl = field.querySelector(".leme-field-count");
                if (!countEl) {
                    countEl = document.createElement("div");
                    countEl.className = "leme-field-count";
                    field.appendChild(countEl);
                }
                countEl.classList.toggle("is-selected", selecionados.size > 0);
                if (selecionados.size === 0) {
                    countEl.textContent = opcoes.length + " opção(ões) disponível(is)";
                } else if (selecionados.size === 1) {
                    const unico = selecionados.values().next().value;
                    countEl.textContent = (mapaContagem.get(unico) || 0) + " registro(s) nesta opção";
                } else {
                    const uniao = obterUniaoIndicesFaceta(campo, selecionados);
                    const qtdUniao = semOutrosFiltros
                        ? uniao.size
                        : base.reduce((acc, it) => acc + (uniao.has(it._idx) ? 1 : 0), 0);
                    countEl.textContent = selecionados.size + " opções · " + qtdUniao + " registro(s)";
                }
            }
        });
    }

    function renderFiltrosAtivos() {
        const chips = [];
        if (busca.value.trim()) {
            const val = busca.value.trim();
            chips.push(
                '<span class="leme-chip">Busca: ' + escapeHtml(val) +
                '<button type="button" data-clear-search="1" aria-label="Remover busca ' + escapeHtml(val) + '">×</button></span>'
            );
        }

        const adicionarChipsFaceta = (campo, nomeFiltro) => {
            const valores = obterValoresFiltroAtivo(campo);
            if (!valores.size) return;
            valores.forEach(valor => {
                const rotuloValor = formatarOpcaoFiltro(campo, valor);
                chips.push(
                    '<span class="leme-chip">' +
                    escapeHtml(nomeFiltro) + ': ' +
                    escapeHtml(labelCurto(rotuloValor, 46)) +
                    '<button type="button" data-clear-filter-campo="' + escapeHtml(campo) +
                    '" data-clear-filter-valor="' + escapeHtml(valor) +
                    '" aria-label="Remover filtro ' + escapeHtml(nomeFiltro + ": " + rotuloValor) + '">×</button></span>'
                );
            });
        };

        adicionarChipsFaceta("autor_referenciado", "Autor referenciado");
        adicionarChipsFaceta("coorientador", "Coorientador");
        adicionarChipsFaceta("formato_produto", "Formato do produto");
        filtros.forEach(filtro => {
            const label = raiz.querySelector('label[for="' + filtro.id + '"]');
            const nomeFiltro = label ? label.textContent : filtro.dataset.campo;
            adicionarChipsFaceta(filtro.dataset.campo, nomeFiltro);
        });

        const htmlChips = chips.join("");
        filtrosAtivos.innerHTML = htmlChips;
        if (graficosFiltrosEl) {
            graficosFiltrosEl.innerHTML = chips.length
                ? (htmlChips + '<button type="button" class="leme-chip-clear-all" data-clear-all-filters="1">Limpar filtros</button>')
                : "";
        }
    }

    function ordenarResultados(lista) {
        const copia = lista.slice();
        if (ordenacao === "ano_asc") {
            return copia.sort((a, b) => (a.anoNum - b.anoNum) || a.id.localeCompare(b.id, "pt-BR"));
        }
        if (ordenacao === "titulo_asc") {
            return copia.sort((a, b) => {
                const ta = escopo === "produtos" ? (a.produto_titulo || a.dissertacao_titulo) : a.dissertacao_titulo;
                const tb = escopo === "produtos" ? (b.produto_titulo || b.dissertacao_titulo) : b.dissertacao_titulo;
                return ta.localeCompare(tb, "pt-BR");
            });
        }
        if (ordenacao === "autor_asc") {
            return copia.sort((a, b) => (a.autor || "").localeCompare(b.autor || "", "pt-BR"));
        }
        return copia.sort((a, b) => (b.anoNum - a.anoNum) || b.id.localeCompare(a.id, "pt-BR"));
    }

    function alternarFiltroInterativo(campo, valor) {
        if (!campo || !valor) return;
        const set = filtrosSelecionados.get(campo);
        if (!set) return;
        if (set.has(valor)) set.delete(valor);
        else set.add(valor);
        aplicarFiltros(true);
    }

    function contarAgregado(lista, extratorChave, peso, formatadorRotulo) {
        const fator = peso || 1;
        const mapa = new Map();
        lista.forEach(item => {
            const valores = extratorChave(item);
            const arr = Array.isArray(valores) ? valores : [valores];
            arr.forEach(v => {
                if (!ehValorPublico(v)) return;
                const key = limparRotulo(v);
                if (!mapa.has(key)) {
                    const label = formatadorRotulo ? limparRotulo(formatadorRotulo(key)) : key;
                    mapa.set(key, { key: key, label: label || key, valor: 0 });
                }
                mapa.get(key).valor += fator;
            });
        });
        return Array.from(mapa.values())
            .sort((a, b) => b.valor - a.valor || String(a.label).localeCompare(String(b.label), "pt-BR"));
    }

    function ordenarRankingMapa(mapa, limite) {
        const ordenado = Array.from(mapa.values())
            .sort((a, b) => b.valor - a.valor || String(a.label).localeCompare(String(b.label), "pt-BR"));
        return limite ? ordenado.slice(0, limite) : ordenado;
    }

    function contarOrientadores(lista, limite) {
        const mapa = new Map();
        lista.forEach(item => {
            if (!item.orientadorChave || !ehValorPublico(item.orientador)) return;
            const chave = item.orientadorChave;
            if (!mapa.has(chave)) mapa.set(chave, { key: chave, label: item.orientador, valor: 0 });
            mapa.get(chave).valor += 1;
        });
        return ordenarRankingMapa(mapa, limite);
    }

    function contarCoorientadores(lista, limite) {
        const mapa = new Map();
        lista.forEach(item => {
            for (let j = 0; j < item.coorientadoresChaves.length; j++) {
                const chave = item.coorientadoresChaves[j];
                const nome = coorientadoresPorChave.get(chave) || item.coorientadores[j];
                if (!chave || !ehValorPublico(nome)) continue;
                if (!mapa.has(chave)) mapa.set(chave, { key: chave, label: nome, valor: 0 });
                mapa.get(chave).valor += 1;
            }
        });
        return ordenarRankingMapa(mapa, limite);
    }

    function agruparTop(lista, limite, valoresAtivos) {
        if (lista.length <= limite) return lista;
        const top = lista.slice(0, limite);
        const extrasAtivos = [];
        let outras = 0;
        for (let i = limite; i < lista.length; i++) {
            const item = lista[i];
            if (valoresAtivos && item.key && valoresAtivos.has(item.key)) {
                extrasAtivos.push(item);
            } else {
                outras += item.valor;
            }
        }
        const saida = extrasAtivos.length ? top.concat(extrasAtivos) : top;
        if (outras) saida.push({ key: "", label: "Outras", valor: outras });
        return saida;
    }

    function renderInsightCard(titulo, itemOuTexto, campoFiltro) {
        if (itemOuTexto && typeof itemOuTexto === "object") {
            const key = itemOuTexto.key || "";
            const label = itemOuTexto.label || "—";
            if (campoFiltro && key) {
                const ativosCampo = obterValoresFiltroAtivo(campoFiltro);
                const ativo = ativosCampo.has(key);
                const acao = prefixoAcaoFiltro(ativo, ativosCampo.size);
                return '<button type="button" class="leme-insight-card is-clickable' + (ativo ? ' is-active' : '') +
                    '" data-filter-campo="' + escapeHtml(campoFiltro) +
                    '" data-filter-valor="' + escapeHtml(key) +
                    '" aria-pressed="' + (ativo ? 'true' : 'false') +
                    '" title="' + acao + escapeHtml(label) + '">' +
                    '<strong>' + escapeHtml(label) + '</strong><span>' + escapeHtml(titulo) + '</span></button>';
            }
            return '<div class="leme-insight-card"><strong>' + escapeHtml(label) + '</strong><span>' + escapeHtml(titulo) + '</span></div>';
        }
        return '<div class="leme-insight-card"><strong>' + escapeHtml(itemOuTexto || "—") + '</strong><span>' + escapeHtml(titulo) + '</span></div>';
    }

    function primeiroItem(lista) {
        return lista && lista[0] ? lista[0] : null;
    }

    function renderInsights(lista) {
        if (!lista.length) {
            insights.innerHTML = '<div class="leme-insight-card"><strong>0</strong><span>Nenhum resultado neste recorte. Limpe algum filtro ou use uma busca mais ampla.</span></div>';
            return;
        }

        if (escopo === "dissertacoes") {
            insights.innerHTML = [
                renderInsightCard("dissertações no recorte", lista.length.toLocaleString("pt-BR")),
                renderInsightCard("base epistemológica predominante", primeiroItem(contarAgregado(lista, i => i.base_epistemologica, 1)), "base_epistemologica"),
                renderInsightCard("autor mais referenciado", primeiroItem(contarAgregado(lista, i => i.autores_referenciados, 1)), "autor_referenciado"),
                renderInsightCard("orientador em destaque", primeiroItem(contarOrientadores(lista, 1)), "orientador")
            ].join("");
            return;
        }

        if (escopo === "produtos") {
            insights.innerHTML = [
                renderInsightCard("produtos educacionais no recorte", lista.length.toLocaleString("pt-BR")),
                renderInsightCard("tipo de produto mais comum", primeiroItem(contarAgregado(lista, i => i.tipo_produto, 1, k => traduzirSlug("tipo_produto", k))), "tipo_produto"),
                renderInsightCard("público-alvo principal", primeiroItem(contarAgregado(lista, i => i.publico_alvo, 1, k => traduzirSlug("publico_alvo", k))), "publico_alvo"),
                renderInsightCard("nível de aplicação predominante", primeiroItem(contarAgregado(lista, i => i.nivel_aplicacao, 1)), "nivel_aplicacao")
            ].join("");
            return;
        }

        insights.innerHTML = [
            renderInsightCard("produções (dissertações + produtos)", (lista.length * 2).toLocaleString("pt-BR")),
            renderInsightCard("tipo de produto mais comum", primeiroItem(contarAgregado(lista, i => i.tipo_produto, 1, k => traduzirSlug("tipo_produto", k))), "tipo_produto"),
            renderInsightCard("autor mais referenciado", primeiroItem(contarAgregado(lista, i => i.autores_referenciados, 1)), "autor_referenciado"),
            renderInsightCard("orientador em destaque", primeiroItem(contarOrientadores(lista, 1)), "orientador")
        ].join("");
    }

    function rotuloMacroCurto(valor) {
        const texto = limparRotulo(valor);
        const partes = texto.split(/\s+[–—-]\s+/);
        if (partes.length < 2) return texto;
        return partes[0] + " · " + partes.slice(1).join(" – ");
    }

    function renderHorizontalChart(el, dadosGrafico, limite, opcoes) {
        const config = opcoes || {};
        const dadosValidos = dadosGrafico.filter(d => d.valor > 0);
        const limiteReal = limite || 8;
        const campoFiltro = config.campoFiltro || "";
        const valoresAtivos = campoFiltro ? obterValoresFiltroAtivo(campoFiltro) : EMPTY_SET;

        let lista;
        let extrasCount = 0;
        if (config.agruparOutras === false) {
            lista = dadosValidos.slice(0, limiteReal);
            if (valoresAtivos.size > 0) {
                for (let i = limiteReal; i < dadosValidos.length; i++) {
                    const d = dadosValidos[i];
                    if (d.key && valoresAtivos.has(d.key)) {
                        lista.push(d);
                        extrasCount++;
                    }
                }
            }
        } else {
            lista = agruparTop(dadosValidos, limiteReal, valoresAtivos);
        }

        if (!lista.length) {
            el.innerHTML = '<div class="leme-empty-chart">' + escapeHtml(config.emptyText || "Limpe algum filtro ou faça uma busca mais ampla para comparar categorias.") + '</div>';
            return;
        }

        let barsEl = el.querySelector(".leme-bars");
        if (!barsEl) {
            el.innerHTML = '<div class="leme-bars"></div>';
            barsEl = el.firstElementChild;
        }

        const temAlgumAtivoVisivel = Boolean(campoFiltro && valoresAtivos.size > 0 && lista.some(d => d.key && valoresAtivos.has(d.key)));
        barsEl.classList.toggle("is-filtered", temAlgumAtivoVisivel);
        const max = Math.max(...lista.map(d => d.valor), 1);

        const chavesNovas = new Set();
        const existentes = new Map();
        Array.from(barsEl.children).forEach(ch => {
            if (ch.dataset && ch.dataset.barKey) existentes.set(ch.dataset.barKey, ch);
        });

        lista.forEach(d => {
            chavesNovas.add(d.key ? ("k:" + d.key) : ("l:" + d.label));
        });
        existentes.forEach((node, key) => {
            if (!chavesNovas.has(key)) {
                node.remove();
                existentes.delete(key);
            }
        });

        const novos = [];
        lista.forEach((d, idx) => {
            const barKey = d.key ? ("k:" + d.key) : ("l:" + d.label);
            const ehClicavel = Boolean(campoFiltro && d.key);
            const expectedTag = ehClicavel ? "BUTTON" : "DIV";
            const rotulo = config.formatarRotulo ? config.formatarRotulo(d.label) : limparRotulo(d.label);
            const scale = Math.max(0.04, d.valor / max);
            const scaleStr = "scaleX(" + scale.toFixed(4) + ")";

            let row = existentes.get(barKey);
            if (row && row.tagName !== expectedTag) {
                row.remove();
                row = null;
            }

            let fill;
            if (!row) {
                row = document.createElement(ehClicavel ? "button" : "div");
                if (ehClicavel) row.type = "button";
                row.className = "leme-bar-row" + (ehClicavel ? " is-clickable" : "") + " is-entering";
                row.dataset.barKey = barKey;

                const labelEl = document.createElement("span");
                labelEl.className = "leme-bar-label";
                const trackEl = document.createElement("span");
                trackEl.className = "leme-bar-track";
                fill = document.createElement("span");
                fill.className = "leme-bar-fill";
                fill.style.transform = "scaleX(0)";
                trackEl.appendChild(fill);
                const valEl = document.createElement("span");
                valEl.className = "leme-bar-value";

                row.appendChild(labelEl);
                row.appendChild(trackEl);
                row.appendChild(valEl);
                novos.push({ row, fill, scaleStr });
            } else {
                fill = row.querySelector(".leme-bar-fill");
                row.classList.remove("is-entering");
                fill.style.transform = scaleStr;
            }

            const labelSpan = row.querySelector(".leme-bar-label");
            const valSpan = row.querySelector(".leme-bar-value");
            labelSpan.textContent = rotulo;
            valSpan.textContent = String(d.valor);

            if (ehClicavel) {
                const ativo = valoresAtivos.has(d.key);
                row.classList.toggle("is-active", ativo);
                row.dataset.filterCampo = campoFiltro;
                row.dataset.filterValor = d.key;
                row.setAttribute("aria-pressed", ativo ? "true" : "false");
                row.title = prefixoAcaoFiltro(ativo, valoresAtivos.size) + d.label;
            } else {
                labelSpan.title = d.label;
            }

            const ref = barsEl.children[idx] || null;
            if (ref !== row) barsEl.insertBefore(row, ref);
        });

        if (novos.length) {
            void barsEl.offsetWidth;
            for (let i = 0; i < novos.length; i++) {
                novos[i].row.classList.remove("is-entering");
                novos[i].fill.style.transform = novos[i].scaleStr;
            }
        }

        const footnoteText = config.footnote || ((config.agruparOutras === false && dadosValidos.length > limiteReal)
            ? (extrasCount > 0
                ? ("Exibindo os " + limiteReal + " primeiros + " + extrasCount + " selecionado(s) de " + dadosValidos.length + " itens distintos neste recorte.")
                : ("Exibindo os " + limiteReal + " primeiros de " + dadosValidos.length + " itens distintos neste recorte."))
            : "");
        let footnoteEl = el.querySelector(".leme-chart-footnote");
        if (footnoteText) {
            if (!footnoteEl) {
                footnoteEl = document.createElement("p");
                footnoteEl.className = "leme-chart-footnote";
                el.appendChild(footnoteEl);
            }
            footnoteEl.textContent = footnoteText;
        } else if (footnoteEl) {
            footnoteEl.remove();
        }
    }

    function renderCompositionChart(el, dadosGrafico, opcoes) {
        const config = opcoes || {};
        const lista = dadosGrafico.filter(d => d.valor > 0);
        if (!lista.length) {
            el.innerHTML = '<div class="leme-empty-chart">Limpe algum filtro ou faça uma busca mais ampla para comparar as linhas.</div>';
            return;
        }

        let compEl = el.querySelector(".leme-composition");
        if (!compEl) {
            el.innerHTML = '<div class="leme-composition"><div class="leme-composition-track" aria-hidden="true"></div><div class="leme-composition-legend"></div></div>';
            compEl = el.firstElementChild;
        }
        const trackEl = compEl.querySelector(".leme-composition-track");
        const legendEl = compEl.querySelector(".leme-composition-legend");

        const campoFiltro = config.campoFiltro || "";
        const valoresAtivos = campoFiltro ? obterValoresFiltroAtivo(campoFiltro) : EMPTY_SET;
        const temAlgumAtivoVisivel = Boolean(campoFiltro && valoresAtivos.size > 0 && lista.some(d => d.key && valoresAtivos.has(d.key)));
        compEl.classList.toggle("is-filtered", temAlgumAtivoVisivel);
        const cores = ["#3b47e5", "#7b359c", "#d62849", "#1f7a49"];
        const total = lista.reduce((soma, item) => soma + item.valor, 0) || 1;

        const chavesNovas = new Set();
        const segsExist = new Map();
        const legExist = new Map();
        Array.from(trackEl.children).forEach(ch => {
            if (ch.dataset && ch.dataset.barKey) segsExist.set(ch.dataset.barKey, ch);
        });
        Array.from(legendEl.children).forEach(ch => {
            if (ch.dataset && ch.dataset.barKey) legExist.set(ch.dataset.barKey, ch);
        });

        lista.forEach(d => chavesNovas.add(d.key ? ("k:" + d.key) : ("l:" + d.label)));
        segsExist.forEach((node, key) => { if (!chavesNovas.has(key)) { node.remove(); segsExist.delete(key); } });
        legExist.forEach((node, key) => { if (!chavesNovas.has(key)) { node.remove(); legExist.delete(key); } });

        const novosSegs = [];
        lista.forEach((d, idx) => {
            const barKey = d.key ? ("k:" + d.key) : ("l:" + d.label);
            const cor = cores[idx % cores.length];
            const pctStr = ((d.valor / total) * 100).toFixed(2) + "%";
            const percentual = ((d.valor / total) * 100).toFixed(1).replace(".0", "");
            const ehClicavel = Boolean(campoFiltro && d.key);
            const ativo = Boolean(ehClicavel && valoresAtivos.has(d.key));
            const prefixoTooltip = prefixoAcaoFiltro(ativo, valoresAtivos.size);

            let seg = segsExist.get(barKey);
            if (!seg) {
                seg = document.createElement("div");
                seg.dataset.barKey = barKey;
                seg.style.width = "0%";
                novosSegs.push({ seg, pctStr });
            } else {
                seg.style.width = pctStr;
            }
            seg.className = "leme-composition-segment" + (ehClicavel ? " is-clickable" : "") + (ativo ? " is-active" : "");
            seg.style.background = cor;
            if (ehClicavel) {
                seg.dataset.filterCampo = campoFiltro;
                seg.dataset.filterValor = d.key;
                seg.title = prefixoTooltip + d.label + " (" + d.valor + ")";
            } else {
                seg.removeAttribute("data-filter-campo");
                seg.removeAttribute("data-filter-valor");
                seg.title = d.label + ": " + d.valor;
            }
            const refSeg = trackEl.children[idx] || null;
            if (refSeg !== seg) trackEl.insertBefore(seg, refSeg);

            const expectedTag = ehClicavel ? "BUTTON" : "DIV";
            let leg = legExist.get(barKey);
            if (leg && leg.tagName !== expectedTag) {
                leg.remove();
                leg = null;
            }
            if (!leg) {
                leg = document.createElement(ehClicavel ? "button" : "div");
                if (ehClicavel) leg.type = "button";
                leg.className = "leme-composition-item" + (ehClicavel ? " is-clickable" : "");
                leg.dataset.barKey = barKey;

                const dotEl = document.createElement("span");
                dotEl.className = "leme-composition-dot";
                const labelEl = document.createElement("span");
                labelEl.className = "leme-composition-label";
                const valEl = document.createElement("span");
                valEl.className = "leme-composition-value";

                leg.appendChild(dotEl);
                leg.appendChild(labelEl);
                leg.appendChild(valEl);
            }
            leg.querySelector(".leme-composition-dot").style.background = cor;
            const legLabel = leg.querySelector(".leme-composition-label");
            legLabel.textContent = d.label;
            leg.querySelector(".leme-composition-value").textContent = d.valor + " · " + percentual + "%";
            if (ehClicavel) {
                leg.classList.toggle("is-active", ativo);
                leg.dataset.filterCampo = campoFiltro;
                leg.dataset.filterValor = d.key;
                leg.setAttribute("aria-pressed", ativo ? "true" : "false");
                leg.title = prefixoTooltip + d.label;
            } else {
                legLabel.title = d.label;
            }
            const refLeg = legendEl.children[idx] || null;
            if (refLeg !== leg) legendEl.insertBefore(leg, refLeg);
        });

        if (novosSegs.length) {
            void trackEl.offsetWidth;
            for (let i = 0; i < novosSegs.length; i++) {
                novosSegs[i].seg.style.width = novosSegs[i].pctStr;
            }
        }
    }

    function renderYearChart(el, lista) {
        const peso = multiplicadorEscopo();
        const valoresAtivos = obterValoresFiltroAtivo("ano");
        const dadosAno = contarAgregado(lista, i => i.ano, peso)
            .sort((a, b) => Number(a.label) - Number(b.label));

        if (!dadosAno.length) {
            el.innerHTML = '<div class="leme-empty-chart">Limpe algum filtro ou faça uma busca mais ampla para comparar os anos.</div>';
            return;
        }

        let chartEl = el.querySelector(".leme-year-chart");
        if (!chartEl) {
            el.innerHTML = '<div class="leme-year-chart"></div>';
            chartEl = el.firstElementChild;
        }
        chartEl.classList.toggle("is-single", dadosAno.length === 1);
        const temAlgumAtivoVisivel = Boolean(valoresAtivos.size > 0 && dadosAno.some(d => d.key && valoresAtivos.has(d.key)));
        chartEl.classList.toggle("is-filtered", temAlgumAtivoVisivel);

        const max = Math.max(...dadosAno.map(d => d.valor), 1);
        const alturaMaxBarra = 86;

        const chavesNovas = new Set(dadosAno.map(d => d.key));
        const existentes = new Map();
        Array.from(chartEl.children).forEach(ch => {
            if (ch.dataset && ch.dataset.barKey) existentes.set(ch.dataset.barKey, ch);
        });
        existentes.forEach((node, key) => {
            if (!chavesNovas.has(key)) {
                node.remove();
                existentes.delete(key);
            }
        });

        const novos = [];
        dadosAno.forEach((d, idx) => {
            const hStr = Math.max(8, Math.round((d.valor / max) * alturaMaxBarra)) + "px";
            const ativo = valoresAtivos.has(d.key);
            let col = existentes.get(d.key);
            let barEl;

            if (!col) {
                col = document.createElement("button");
                col.type = "button";
                col.className = "leme-year-col is-clickable";
                col.dataset.barKey = d.key;
                col.dataset.filterCampo = "ano";
                col.dataset.filterValor = d.key;

                const valEl = document.createElement("span");
                valEl.className = "leme-year-value";
                barEl = document.createElement("span");
                barEl.className = "leme-year-bar";
                barEl.style.height = "6px";
                const labelEl = document.createElement("span");
                labelEl.className = "leme-year-label";

                col.appendChild(valEl);
                col.appendChild(barEl);
                col.appendChild(labelEl);
                novos.push({ barEl, hStr });
            } else {
                barEl = col.querySelector(".leme-year-bar");
                barEl.style.height = hStr;
            }

            col.classList.toggle("is-active", ativo);
            col.setAttribute("aria-pressed", ativo ? "true" : "false");
            col.title = prefixoAcaoFiltro(ativo, valoresAtivos.size) + "ano " + d.label;
            col.querySelector(".leme-year-value").textContent = String(d.valor);
            col.querySelector(".leme-year-label").textContent = d.label;

            const ref = chartEl.children[idx] || null;
            if (ref !== col) chartEl.insertBefore(col, ref);
        });

        if (novos.length) {
            void chartEl.offsetWidth;
            for (let i = 0; i < novos.length; i++) {
                novos[i].barEl.style.height = novos[i].hStr;
            }
        }
    }

    function atualizarVisibilidadeGraficos() {
        if (chartsGridEl) chartsGridEl.classList.toggle("is-scope-produtos", escopo === "produtos");
        chartCards.forEach(card => {
            const permitidos = (card.dataset.chartScope || "").split(/\s+/);
            card.classList.toggle("is-hidden", !permitidos.includes(escopo));
        });

        const dica = " Clique em um ou mais itens nos gráficos para combinar filtros.";
        if (escopo === "dissertacoes") {
            chartAnoTitle.textContent = "Dissertações defendidas por ano";
            graficosDesc.textContent = "Indicadores específicos das dissertações defendidas no programa ProfEPT." + dica;
        } else if (escopo === "produtos") {
            chartAnoTitle.textContent = "Produtos educacionais por ano";
            graficosDesc.textContent = "Indicadores específicos dos produtos educacionais vinculados às defesas." + dica;
        } else {
            chartAnoTitle.textContent = "Produções por ano (Dissertações + Produtos)";
            graficosDesc.textContent = "Visão panorâmica: cada defesa contabiliza 1 dissertação e 1 produto educacional." + dica;
        }
    }

    function renderCardOrientadores(lista, termos, indicesBuscaSet) {
        const listaOri = obterListaGraficoFaceta("orientador", lista, termos, indicesBuscaSet);
        const listaCoor = obterListaGraficoFaceta("coorientador", lista, termos, indicesBuscaSet);
        const dadosOrientadores = contarOrientadores(listaOri);
        const dadosCoor = contarCoorientadores(listaCoor);
        const defsCoor = contarDefesasComCoorientacao(listaCoor);

        if (tabCoorCountEl) {
            tabCoorCountEl.textContent = "(" + dadosCoor.length.toLocaleString("pt-BR") + ")";
        }
        botoesTabOrientador.forEach(btn => {
            const ativo = btn.dataset.orientadorTab === modoCardOrientador;
            btn.classList.toggle("is-active", ativo);
            btn.setAttribute("aria-pressed", ativo ? "true" : "false");
        });

        if (modoCardOrientador === "coorientador") {
            const subCoor = dadosCoor.length > 0
                ? (dadosCoor.length.toLocaleString("pt-BR") +
                    (dadosCoor.length === 1 ? " coorientador" : " coorientadores") +
                    " em " + defsCoor.toLocaleString("pt-BR") +
                    (defsCoor === 1 ? " defesa" : " defesas") + " do recorte.")
                : "Nenhuma coorientação registrada neste recorte.";
            if (chartOrientadorSubtitleEl) {
                chartOrientadorSubtitleEl.textContent = subCoor;
                chartOrientadorSubtitleEl.title = subCoor;
            }
            renderHorizontalChart(
                chartOrientadorEl,
                dadosCoor,
                10,
                {
                    agruparOutras: false,
                    campoFiltro: "coorientador",
                    emptyText: "Nenhuma coorientação registrada neste recorte."
                }
            );
            if (btnExpandOrientador) {
                btnExpandOrientador.dataset.openRanking = "coorientador";
                btnExpandOrientador.setAttribute("aria-label", "Expandir ranking completo de coorientadores");
                btnExpandOrientador.disabled = dadosCoor.length === 0;
            }
            return;
        }

        if (chartOrientadorSubtitleEl) {
            chartOrientadorSubtitleEl.textContent = "Top 10 por defesas orientadas.";
            chartOrientadorSubtitleEl.title = "Top 10 orientadores principais por número de defesas orientadas.";
        }
        renderHorizontalChart(
            chartOrientadorEl,
            dadosOrientadores,
            10,
            { agruparOutras: false, campoFiltro: "orientador" }
        );
        if (btnExpandOrientador) {
            btnExpandOrientador.dataset.openRanking = "orientador";
            btnExpandOrientador.setAttribute("aria-label", "Expandir ranking completo de orientadores");
            btnExpandOrientador.disabled = dadosOrientadores.length === 0;
        }
    }

    function renderGraficoFormato(el, lista, termos, indicesBuscaSet, btnExpand) {
        const listaFormato = obterListaGraficoFaceta("formato_produto", lista, termos, indicesBuscaSet);
        const dadosFormato = contarAgregado(listaFormato, i => i.formato_produto, 1);
        renderHorizontalChart(
            el,
            dadosFormato,
            10,
            { agruparOutras: false, campoFiltro: "formato_produto" }
        );
        if (btnExpand) btnExpand.disabled = dadosFormato.length === 0;
    }

    function renderCardTipoProduto(lista, termos, indicesBuscaSet) {
        const mostrarSwitch = escopo === "todas";
        const modoEfetivo = mostrarSwitch ? modoCardTipoProduto : "tipo_produto";

        if (chartTipoHeadEl) chartTipoHeadEl.classList.toggle("is-hidden", !mostrarSwitch);
        if (btnExpandTipoFormato) {
            btnExpandTipoFormato.classList.toggle("is-hidden", !mostrarSwitch || modoEfetivo !== "formato_produto");
        }
        if (chartTipoTitleEl) {
            chartTipoTitleEl.classList.toggle("leme-sr-only", mostrarSwitch);
            chartTipoTitleEl.classList.toggle("leme-chart-title", !mostrarSwitch);
            chartTipoTitleEl.textContent = mostrarSwitch ? "Tipo e formato do produto" : "Tipo de produto (CAPES)";
        }

        botoesTabTipoProduto.forEach(btn => {
            const ativo = btn.dataset.tipoTab === modoEfetivo;
            btn.classList.toggle("is-active", ativo);
            btn.setAttribute("aria-pressed", ativo ? "true" : "false");
        });

        if (modoEfetivo === "formato_produto") {
            if (chartTipoSubtitleEl) {
                chartTipoSubtitleEl.textContent = "Top 10 formatos específicos.";
                chartTipoSubtitleEl.title = "Top 10 formatos específicos declarados ou identificados para os produtos educacionais.";
            }
            renderGraficoFormato(chartTipoEl, lista, termos, indicesBuscaSet, btnExpandTipoFormato);
            return;
        }

        if (chartTipoSubtitleEl) {
            chartTipoSubtitleEl.textContent = "Classificação tipológica dos produtos.";
            chartTipoSubtitleEl.title = "Classificação tipológica dos produtos educacionais.";
        }
        const listaTipo = obterListaGraficoFaceta("tipo_produto", lista, termos, indicesBuscaSet);
        renderHorizontalChart(
            chartTipoEl,
            contarAgregado(listaTipo, i => i.tipo_produto, 1, k => traduzirSlug("tipo_produto", k)),
            9,
            { campoFiltro: "tipo_produto" }
        );
    }

    function atualizarGraficos(lista, termos, indicesBuscaSet) {
        atualizarVisibilidadeGraficos();
        renderInsights(lista);
        const listaAno = obterListaGraficoFaceta("ano", lista, termos, indicesBuscaSet);
        renderYearChart(chartAnoEl, listaAno);

        if (escopo === "todas" || escopo === "dissertacoes") {
            const listaLinha = obterListaGraficoFaceta("linha_pesquisa", lista, termos, indicesBuscaSet);
            renderCompositionChart(
                chartLinhaEl,
                contarAgregado(listaLinha, i => i.linha_pesquisa, 1, k => traduzirSlug("linha_pesquisa", k)),
                { campoFiltro: "linha_pesquisa" }
            );
            const listaMacro = obterListaGraficoFaceta("macroprojeto", lista, termos, indicesBuscaSet);
            renderHorizontalChart(
                chartMacroEl,
                contarAgregado(listaMacro, i => i.macroprojeto, 1, k => traduzirSlug("macroprojeto", k)),
                6,
                { formatarRotulo: rotuloMacroCurto, campoFiltro: "macroprojeto" }
            );
            renderCardOrientadores(lista, termos, indicesBuscaSet);

            const listaBase = obterListaGraficoFaceta("base_epistemologica", lista, termos, indicesBuscaSet);
            const totalRecorte = listaBase.length;
            const pendentes = listaBase.filter(i => i.base_revisao_pendente).length;
            const naoDeclaradas = listaBase.filter(i => !i.base_epistemologica && !i.base_revisao_pendente).length;
            const consolidadas = totalRecorte - pendentes - naoDeclaradas;
            const partesNota = [];
            if (totalRecorte > 0 && (pendentes > 0 || naoDeclaradas > 0)) {
                partesNota.push(consolidadas + " de " + totalRecorte + " defesas consolidadas");
                if (pendentes > 0) partesNota.push(pendentes + " em curadoria pendente");
                if (naoDeclaradas > 0) partesNota.push(naoDeclaradas + " sem base declarada");
            }
            const footnoteBase = partesNota.length ? (partesNota.join(" · ") + ".") : "";
            const emptyBase = pendentes > 0
                ? "Nenhuma base consolidada neste recorte (" + pendentes + " registro(s) em curadoria pendente)."
                : "Nenhuma base epistemológica consolidada neste recorte.";

            renderHorizontalChart(chartBaseEl, contarAgregado(listaBase, i => i.base_epistemologica, 1), 8, {
                footnote: footnoteBase,
                emptyText: emptyBase,
                campoFiltro: "base_epistemologica"
            });

            const listaAutoresRef = obterListaGraficoFaceta("autor_referenciado", lista, termos, indicesBuscaSet);
            const dadosAutoresRef = contarAgregado(listaAutoresRef, i => i.autores_referenciados, 1);
            renderHorizontalChart(chartAutoresRefEl, dadosAutoresRef, 12, {
                agruparOutras: false,
                campoFiltro: "autor_referenciado"
            });
            if (btnExpandAutoresRef) btnExpandAutoresRef.disabled = dadosAutoresRef.length === 0;
        }

        if (escopo === "todas" || escopo === "produtos") {
            renderCardTipoProduto(lista, termos, indicesBuscaSet);
            const listaPublico = obterListaGraficoFaceta("publico_alvo", lista, termos, indicesBuscaSet);
            renderHorizontalChart(
                chartPublicoEl,
                contarAgregado(listaPublico, i => i.publico_alvo, 1, k => traduzirSlug("publico_alvo", k)),
                6,
                { agruparOutras: false, campoFiltro: "publico_alvo" }
            );
            const listaNivel = obterListaGraficoFaceta("nivel_aplicacao", lista, termos, indicesBuscaSet);
            renderHorizontalChart(
                chartNivelEl,
                contarAgregado(listaNivel, i => i.nivel_aplicacao, 1),
                8,
                { campoFiltro: "nivel_aplicacao" }
            );
        }

        if (escopo === "produtos") {
            renderGraficoFormato(chartFormatoEl, lista, termos, indicesBuscaSet, btnExpandFormato);
        }

        const totalItensEscopo = lista.length * multiplicadorEscopo();
        const rotuloUnidade = escopo === "dissertacoes"
            ? "dissertação(ões)"
            : escopo === "produtos"
                ? "produto(s) educacional(is)"
                : "produção(ões) (" + lista.length + " defesas)";

        graficosNota.textContent = totalItensEscopo.toLocaleString("pt-BR") + " " + rotuloUnidade;
    }

    function renderBadgesCard(item) {
        const badges = [];
        if (ehValorPublico(item.ano)) badges.push('<span class="leme-badge">' + escapeHtml(item.ano) + '</span>');

        if (escopo === "produtos") {
            if (ehValorPublico(item.tipo_produto_label)) badges.push('<span class="leme-badge red">' + escapeHtml(item.tipo_produto_label) + '</span>');
            if (ehValorPublico(item.formato_produto)) badges.push('<span class="leme-badge">' + escapeHtml(item.formato_produto) + '</span>');
            if (ehValorPublico(item.nivel_aplicacao)) badges.push('<span class="leme-badge green">' + escapeHtml(item.nivel_aplicacao) + '</span>');
            item.publico_alvo_labels.slice(0, 2).forEach(pub => {
                badges.push('<span class="leme-badge">' + escapeHtml(pub) + '</span>');
            });
            return badges.join("");
        }

        if (escopo === "dissertacoes") {
            if (ehValorPublico(item.linha_pesquisa)) badges.push('<span class="leme-badge" title="' + escapeHtml(item.linha_pesquisa_label) + '">' + escapeHtml(item.linha_pesquisa) + '</span>');
            if (ehValorPublico(item.macroprojeto)) badges.push('<span class="leme-badge" title="' + escapeHtml(item.macroprojeto_label) + '">' + escapeHtml(item.macroprojeto) + '</span>');
            if (item.base_epistemologica) {
                badges.push('<span class="leme-badge green">' + escapeHtml(item.base_epistemologica) + '</span>');
            } else if (item.base_revisao_pendente) {
                badges.push('<span class="leme-badge pending">Em curadoria</span>');
            }
            return badges.join("");
        }

        if (ehValorPublico(item.linha_pesquisa)) badges.push('<span class="leme-badge" title="' + escapeHtml(item.linha_pesquisa_label) + '">' + escapeHtml(item.linha_pesquisa) + '</span>');
        if (ehValorPublico(item.nivel_aplicacao)) badges.push('<span class="leme-badge green">' + escapeHtml(item.nivel_aplicacao) + '</span>');
        if (ehValorPublico(item.tipo_produto_label)) badges.push('<span class="leme-badge red">' + escapeHtml(item.tipo_produto_label) + '</span>');
        return badges.join("");
    }

    function renderActions(item) {
        const links = [];
        if ((escopo === "todas" || escopo === "dissertacoes") && item.dissertacao_link) {
            links.push('<a class="leme-link pdf" href="' + escapeHtml(item.dissertacao_link) + '" target="_blank" rel="noopener noreferrer" aria-label="Abrir dissertação em nova aba">Dissertação</a>');
        }
        if ((escopo === "todas" || escopo === "produtos") && item.produto_link) {
            links.push('<a class="leme-link produto" href="' + escapeHtml(item.produto_link) + '" target="_blank" rel="noopener noreferrer" aria-label="Abrir produto educacional no eduCAPES em nova aba">Produto educacional</a>');
        }
        return links.length ? '<div class="leme-actions">' + links.join("") + '</div>' : "";
    }

    function renderCards(lista, termos) {
        if (!lista.length) {
            resultados.innerHTML = '<div class="leme-empty">Nenhum registro encontrado com os filtros selecionados.</div>';
            return;
        }

        resultados.innerHTML = lista.map(item => {
            const ehProduto = escopo === "produtos";
            const tituloPrincipal = ehProduto ? (item.produto_titulo || item.dissertacao_titulo) : item.dissertacao_titulo;
            const eyebrow = ehProduto
                ? 'PRODUTO EDUCACIONAL' + (ehValorPublico(item.ano) ? ' · ' + escapeHtml(item.ano) : '')
                : (escopo === "dissertacoes" ? 'DISSERTAÇÃO · ' + escapeHtml(item.id) : 'DEFESA · ' + escapeHtml(item.id)) + (ehValorPublico(item.ano) ? ' · ' + escapeHtml(item.ano) : '');

            let metaHtml = '<div><b>Autor(a):</b> ' + highlightText(valorPublico(item.autor), termos) + '</div>' +
                '<div><b>Orientador(a):</b> ' + highlightText(valorPublico(item.orientador), termos) + '</div>';

            if (ehProduto) {
                metaHtml += '<div><b>Público-alvo:</b> ' + highlightText(item.publico_alvo_labels.join(", ") || "Não informado", termos) + '</div>';
            } else if (escopo === "dissertacoes") {
                metaHtml += '<div><b>Base epistemológica:</b> ' + highlightText(item.base_status_label, termos) + '</div>';
            } else {
                metaHtml += '<div><b>Produto:</b> ' + highlightText(labelCurto(item.produto_titulo, 72) || "Não informado", termos) + '</div>';
            }

            const corpoTexto = ehProduto
                ? ('Dissertação vinculada: ' + (item.dissertacao_titulo || "Não informada") + (item.termos_unificados.length ? ' · Palavras-chave: ' + item.termos_unificados.slice(0, 5).join(", ") : ''))
                : (trechoResumoCard(item.dissertacao_resumo, termos, 380) || "Resumo não disponível.");

            return '<article class="leme-card">' +
                '<div class="leme-eyebrow">' + eyebrow + '</div>' +
                '<h3 class="leme-card-title">' + highlightText(tituloPrincipal, termos) + '</h3>' +
                '<div class="leme-meta">' + metaHtml + '</div>' +
                '<div class="leme-badges">' + renderBadgesCard(item) + '</div>' +
                '<p class="leme-summary">' + highlightText(corpoTexto, termos) + '</p>' +
                '<div class="leme-card-footer"><button type="button" class="leme-card-detail-btn" data-id="' + escapeHtml(item.id) + '" aria-label="Ver detalhes de ' + escapeHtml(labelCurto(tituloPrincipal, 80)) + '">Ver detalhes</button>' + renderActions(item) + '</div>' +
                '</article>';
        }).join("");
    }

    function renderTable(lista, termos) {
        if (!lista.length) {
            resultados.innerHTML = '<div class="leme-empty">Nenhum registro encontrado com os filtros selecionados.</div>';
            return;
        }

        const btnDetalhes = (item, titulo) =>
            '<button type="button" class="leme-table-detail-btn" data-id="' + escapeHtml(item.id) + '" aria-label="Ver detalhes de ' + escapeHtml(labelCurto(titulo, 80)) + '">Ver detalhes</button>';

        if (escopo === "produtos") {
            resultados.innerHTML = '<table class="leme-table">' +
                '<caption>Produtos Educacionais filtrados</caption>' +
                '<thead><tr><th scope="col">Produto Educacional</th><th scope="col">Tipo (CAPES)</th><th scope="col">Formato</th><th scope="col">Público-Alvo</th><th scope="col">Nível de Aplicação</th><th scope="col">Autor(a)</th><th scope="col">Ano</th><th scope="col">Ações</th></tr></thead>' +
                '<tbody>' + lista.map(item => {
                    const titulo = item.produto_titulo || item.dissertacao_titulo || "Não informado";
                    return '<tr>' +
                        '<td><div class="leme-table-title">' + highlightText(titulo, termos) + '</div></td>' +
                        '<td>' + escapeHtml(valorPublico(item.tipo_produto_label)) + '</td>' +
                        '<td>' + escapeHtml(valorPublico(item.formato_produto)) + '</td>' +
                        '<td>' + escapeHtml(item.publico_alvo_labels.join(", ") || "Não informado") + '</td>' +
                        '<td>' + escapeHtml(valorPublico(item.nivel_aplicacao)) + '</td>' +
                        '<td>' + highlightText(valorPublico(item.autor), termos) + '</td>' +
                        '<td>' + escapeHtml(valorPublico(item.ano)) + '</td>' +
                        '<td><div class="leme-table-actions">' + btnDetalhes(item, titulo) + renderActions(item) + '</div></td>' +
                        '</tr>';
                }).join("") + '</tbody></table>';
            return;
        }

        if (escopo === "dissertacoes") {
            resultados.innerHTML = '<table class="leme-table">' +
                '<caption>Dissertações filtradas</caption>' +
                '<thead><tr><th scope="col">Dissertação</th><th scope="col">Autor(a)</th><th scope="col">Orientador(a)</th><th scope="col">Ano</th><th scope="col">Linha</th><th scope="col">Macroprojeto</th><th scope="col">Base Epistemológica</th><th scope="col">Ações</th></tr></thead>' +
                '<tbody>' + lista.map(item =>
                    '<tr>' +
                    '<td><div class="leme-table-title">' + highlightText(item.dissertacao_titulo, termos) + '</div></td>' +
                    '<td>' + highlightText(valorPublico(item.autor), termos) + '</td>' +
                    '<td>' + highlightText(valorPublico(item.orientador), termos) + '</td>' +
                    '<td>' + escapeHtml(valorPublico(item.ano)) + '</td>' +
                    '<td>' + escapeHtml(valorPublico(item.linha_pesquisa_label)) + '</td>' +
                    '<td title="' + escapeHtml(item.macroprojeto_label) + '">' + escapeHtml(valorPublico(item.macroprojeto)) + '</td>' +
                    '<td>' + escapeHtml(item.base_status_label) + '</td>' +
                    '<td><div class="leme-table-actions">' + btnDetalhes(item, item.dissertacao_titulo) + renderActions(item) + '</div></td>' +
                    '</tr>'
                ).join("") + '</tbody></table>';
            return;
        }

        resultados.innerHTML = '<table class="leme-table">' +
            '<caption>Resultados filtrados do painel</caption>' +
            '<thead><tr><th scope="col">Dissertação / Produto</th><th scope="col">Autor(a)</th><th scope="col">Orientador(a)</th><th scope="col">Ano</th><th scope="col">Linha</th><th scope="col">Macroprojeto</th><th scope="col">Base Epistemológica</th><th scope="col">Tipo de Produto</th><th scope="col">Ações</th></tr></thead>' +
            '<tbody>' + lista.map(item =>
                '<tr>' +
                '<td><div class="leme-table-title">' + highlightText(item.dissertacao_titulo, termos) + '</div>' +
                (item.produto_titulo ? '<div class="leme-table-sub"><b>Produto:</b> ' + highlightText(labelCurto(item.produto_titulo, 90), termos) + '</div>' : '') + '</td>' +
                '<td>' + highlightText(valorPublico(item.autor), termos) + '</td>' +
                '<td>' + highlightText(valorPublico(item.orientador), termos) + '</td>' +
                '<td>' + escapeHtml(valorPublico(item.ano)) + '</td>' +
                '<td>' + escapeHtml(valorPublico(item.linha_pesquisa_label)) + '</td>' +
                '<td title="' + escapeHtml(item.macroprojeto_label) + '">' + escapeHtml(valorPublico(item.macroprojeto)) + '</td>' +
                '<td>' + escapeHtml(item.base_status_label) + '</td>' +
                '<td>' + escapeHtml(valorPublico(item.tipo_produto_label)) + '</td>' +
                '<td><div class="leme-table-actions">' + btnDetalhes(item, item.dissertacao_titulo) + renderActions(item) + '</div></td>' +
                '</tr>'
            ).join("") + '</tbody></table>';
    }

    function paginaLista(lista) {
        const totalPaginas = Math.max(1, Math.ceil(lista.length / itensPorPagina));
        if (paginaAtual > totalPaginas) paginaAtual = totalPaginas;
        const inicio = (paginaAtual - 1) * itensPorPagina;
        return lista.slice(inicio, inicio + itensPorPagina);
    }

    function paginasVisiveis(totalPaginas, paginaRef) {
        const atual = paginaRef || paginaAtual;
        const paginas = new Set([1, totalPaginas, atual - 1, atual, atual + 1]);
        if (atual <= 3) [1, 2, 3, 4].forEach(p => paginas.add(p));
        if (atual >= totalPaginas - 2) [totalPaginas - 3, totalPaginas - 2, totalPaginas - 1, totalPaginas].forEach(p => paginas.add(p));
        return [...paginas].filter(p => p >= 1 && p <= totalPaginas).sort((a, b) => a - b);
    }

    function botaoPagina(rotulo, pagina, classe, disabled, ariaLabel, dataAttr) {
        const atual = classe && classe.includes("is-active");
        const attr = dataAttr || "data-pagina";
        return '<button type="button" class="leme-page-btn ' + (classe || "") + '" ' + attr + '="' + pagina + '" ' + (disabled ? "disabled" : "") + (atual ? ' aria-current="page"' : '') + ' aria-label="' + escapeHtml(ariaLabel || ("Página " + rotulo)) + '">' + escapeHtml(rotulo) + '</button>';
    }

    function montarHtmlPaginacao(totalItens, paginaCorrente, porPagina, dataAttr, sufixoInfo) {
        const totalPaginas = Math.max(1, Math.ceil(totalItens / porPagina));
        if (!totalItens || totalPaginas <= 1) return "";
        let html = botaoPagina("Anterior", Math.max(1, paginaCorrente - 1), "", paginaCorrente === 1, "Página anterior", dataAttr);
        const visiveis = paginasVisiveis(totalPaginas, paginaCorrente);
        let anterior = 0;
        visiveis.forEach(p => {
            if (anterior && p - anterior > 1) html += '<span class="leme-pagination-ellipsis" aria-hidden="true">…</span>';
            html += botaoPagina(String(p), p, p === paginaCorrente ? "is-active" : "", false, "Página " + p, dataAttr);
            anterior = p;
        });
        html += botaoPagina("Próximo", Math.min(totalPaginas, paginaCorrente + 1), "", paginaCorrente === totalPaginas, "Próxima página", dataAttr);
        const inicio = (paginaCorrente - 1) * porPagina + 1;
        const fim = Math.min(paginaCorrente * porPagina, totalItens);
        html += '<div class="leme-pagination-info">Exibindo ' + inicio + '–' + fim + ' de ' + totalItens + ' ' + escapeHtml(sufixoInfo || "registros") + '</div>';
        return html;
    }

    function renderPaginacao(totalItens) {
        paginacao.innerHTML = montarHtmlPaginacao(totalItens, paginaAtual, itensPorPagina, "data-pagina", "registros");
    }

    function atualizarContador(total) {
        if (escopo === "dissertacoes") {
            contador.innerHTML = '<strong>' + total + '</strong> dissertação(ões) encontrada(s)';
        } else if (escopo === "produtos") {
            contador.innerHTML = '<strong>' + total + '</strong> produto(s) educacional(is) encontrado(s)';
        } else {
            contador.innerHTML = '<strong>' + total + '</strong> defesa(s) encontrada(s) · <strong>' + (total * 2) + '</strong> produções';
        }
    }

    function atualizarVisualizacao(termosPreCalculados) {
        const termos = termosPreCalculados || termosBusca();
        const modoEfetivo = mqMobile.matches ? "cards" : modo;
        resultados.classList.toggle("is-table", modoEfetivo === "table");
        btnCards.classList.toggle("is-active", modoEfetivo === "cards");
        btnTable.classList.toggle("is-active", modoEfetivo === "table");
        btnCards.setAttribute("aria-pressed", modoEfetivo === "cards" ? "true" : "false");
        btnTable.setAttribute("aria-pressed", modoEfetivo === "table" ? "true" : "false");
        const pagina = paginaLista(resultadosAtuais);
        if (modoEfetivo === "cards") renderCards(pagina, termos);
        else renderTable(pagina, termos);
        renderPaginacao(resultadosAtuais.length);
    }

    function aplicarFiltros(resetPagina) {
        if (resetPagina) paginaAtual = 1;
        const termos = termosBusca();
        const indicesBuscaSet = calcularIndicesBuscaSet(termos);
        popularFiltrosDinamicos(termos, indicesBuscaSet);
        resultadosAtuais = ordenarResultados(filtrarDados(null, termos, indicesBuscaSet));
        atualizarContador(resultadosAtuais.length);
        exportarCsv.disabled = resultadosAtuais.length === 0;
        renderFiltrosAtivos();
        atualizarGraficos(resultadosAtuais, termos, indicesBuscaSet);
        atualizarVisualizacao(termos);
    }

    function renderTags(tags, termos) {
        if (!tags || !tags.length) return "";
        return '<div class="leme-tags">' + tags.map(t => '<span class="leme-tag">' + highlightText(t, termos) + '</span>').join("") + '</div>';
    }

    function renderSecaoDetalhesRecolhivel(item, termos) {
        const blocos = [];

        if (item.base_epistemologica && item.base_evidencias.length) {
            const itensEv = item.base_evidencias.map(ev => {
                const cab = [ev.secao, ev.pagina != null ? ("p. " + ev.pagina) : ""].filter(Boolean).join(" · ");
                return '<li class="leme-evidence-item">' +
                    (cab ? '<b>' + escapeHtml(cab) + ':</b> ' : '') +
                    '“' + highlightText(ev.trecho, termos) + '”' +
                    (ev.referencia_correspondente ? ' <span class="leme-table-sub">(' + highlightText(ev.referencia_correspondente, termos) + ')</span>' : '') +
                    '</li>';
            }).join("");
            blocos.push('<div><b>Evidências textuais da base epistemológica:</b><ul class="leme-evidence-list">' + itensEv + '</ul></div>');
        }

        const metaProd = [];
        if (item.data_publicacao) {
            metaProd.push('<li><b>Data de publicação do produto:</b> ' + escapeHtml(formatarDataPublicacao(item.data_publicacao)) + '</li>');
        }
        if (item.proveniencia.fonte_tipo_escolhida) {
            metaProd.push('<li><b>Fonte da tipologia do produto:</b> ' + escapeHtml(traduzirSlug("fonte_tipo", item.proveniencia.fonte_tipo_escolhida)) + '</li>');
        }
        if (item.proveniencia.rotulo_original_declarado &&
            normalizarBusca(item.proveniencia.rotulo_original_declarado) !== normalizarBusca(item.produto_titulo)) {
            metaProd.push('<li><b>Rótulo original declarado:</b> ' + escapeHtml(item.proveniencia.rotulo_original_declarado) + '</li>');
        }
        if (item.proveniencia.colecao_educapes) {
            metaProd.push('<li><b>Coleção eduCAPES:</b> ' + escapeHtml(item.proveniencia.colecao_educapes) + '</li>');
        }
        if (item.proveniencia.dc_type_educapes.length) {
            metaProd.push('<li><b>dc.type (eduCAPES):</b> ' + escapeHtml(item.proveniencia.dc_type_educapes.join(", ")) + '</li>');
        }
        if (item.autores_colaboradores.length) {
            const colabs = item.autores_colaboradores
                .map(c => c.nome + (c.papel ? " (" + c.papel + ")" : ""))
                .join("; ");
            metaProd.push('<li><b>Autores e colaboradores (eduCAPES):</b> ' + escapeHtml(colabs) + '</li>');
        }
        if (item.identificadores.length) {
            const idsHtml = item.identificadores.map(idObj => {
                const rot = (idObj.esquema ? idObj.esquema + ": " : "") + idObj.valor;
                return idObj.url
                    ? '<a href="' + escapeHtml(idObj.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(rot) + '</a>'
                    : escapeHtml(rot);
            }).join(" · ");
            metaProd.push('<li><b>Identificadores:</b> ' + idsHtml + '</li>');
        }

        if (metaProd.length) {
            blocos.push('<div><b>Proveniência e metadados do produto:</b><ul class="leme-meta-list">' + metaProd.join("") + '</ul></div>');
        }

        if (!blocos.length) return "";
        return '<div class="leme-detail-item is-wide"><details class="leme-details">' +
            '<summary class="leme-details-summary">Evidências e metadados técnicos (v4)</summary>' +
            '<div class="leme-details-body">' + blocos.join("") + '</div>' +
            '</details></div>';
    }

    const RANKING_CONFIGS = {
        autor_referenciado: {
            titulo: "Autores referenciados: ranking completo",
            campoFiltro: "autor_referenciado",
            corteInicial: 5,
            rotuloOrdenacaoFreq: "Mais citados",
            placeholderBusca: "Pesquisar autor por nome...",
            entidadePlural: "autores",
            entidadeSingular: "autor",
            acaoDescricao: "que citam o autor",
            colunaCsv: "Autor referenciado",
            arquivoCsv: "ranking-autores-referenciados-leme-ept.csv",
            coletarBase: () => obterListaGraficoFaceta("autor_referenciado", resultadosAtuais),
            coletarDados: base => contarAgregado(base, i => i.autores_referenciados, 1)
        },
        orientador: {
            titulo: "Orientadores principais: ranking completo",
            campoFiltro: "orientador",
            corteInicial: 1,
            rotuloOrdenacaoFreq: "Mais orientações",
            placeholderBusca: "Pesquisar orientador por nome...",
            entidadePlural: "orientadores",
            entidadeSingular: "orientador",
            acaoDescricao: "orientadas",
            colunaCsv: "Orientador",
            arquivoCsv: "ranking-orientadores-leme-ept.csv",
            coletarBase: () => obterListaGraficoFaceta("orientador", resultadosAtuais),
            coletarDados: base => contarOrientadores(base),
            parAlternavel: "coorientador"
        },
        coorientador: {
            titulo: "Coorientadores: ranking completo",
            campoFiltro: "coorientador",
            corteInicial: 1,
            rotuloOrdenacaoFreq: "Mais coorientações",
            placeholderBusca: "Pesquisar coorientador por nome...",
            entidadePlural: "coorientadores",
            entidadeSingular: "coorientador",
            acaoDescricao: "coorientadas",
            colunaCsv: "Coorientador",
            arquivoCsv: "ranking-coorientadores-leme-ept.csv",
            coletarBase: () => obterListaGraficoFaceta("coorientador", resultadosAtuais),
            coletarDados: base => contarCoorientadores(base),
            parAlternavel: "orientador"
        },
        formato_produto: {
            titulo: "Formatos de produto: ranking completo",
            campoFiltro: "formato_produto",
            corteInicial: 1,
            rotuloOrdenacaoFreq: "Mais frequentes",
            placeholderBusca: "Pesquisar formato por nome...",
            entidadePlural: "formatos",
            entidadeSingular: "formato",
            acaoDescricao: "neste formato",
            colunaCsv: "Formato do produto",
            arquivoCsv: "ranking-formatos-produto-leme-ept.csv",
            coletarBase: () => obterListaGraficoFaceta("formato_produto", resultadosAtuais),
            coletarDados: base => contarAgregado(base, i => i.formato_produto, 1)
        }
    };

    function formatarPercentualPtBr(valor, total) {
        return ((valor / (total || 1)) * 100).toFixed(1).replace(".", ",") + "%";
    }

    function contarItensPorCorte(dadosBrutos, corte) {
        let total = 0;
        for (let i = 0; i < dadosBrutos.length; i++) {
            if (dadosBrutos[i].valor >= corte) total++;
        }
        return total;
    }

    function escolherCorteAdaptavel(dadosBrutos, corteDesejado) {
        if (corteDesejado <= 1) return 1;
        const desc = RANKING_CORTES.filter(c => c <= corteDesejado).sort((a, b) => b - a);
        for (let i = 0; i < desc.length; i++) {
            if (contarItensPorCorte(dadosBrutos, desc[i]) > 0) return desc[i];
        }
        return 1;
    }

    function obterItensModalRankingFiltrados(estado, corteOverride) {
        const corte = corteOverride !== undefined ? corteOverride : estado.corte;
        const termos = estado.buscaTermos;
        const filtrados = estado.dadosBrutos.filter(d => {
            if (d.valor < corte) return false;
            if (!termos.length) return true;
            for (let i = 0; i < termos.length; i++) {
                if (!d.norm.includes(termos[i])) return false;
            }
            return true;
        });
        if (estado.ordenacao === "az") {
            filtrados.sort((a, b) => a.label.localeCompare(b.label, "pt-BR") || (b.valor - a.valor));
        } else {
            filtrados.sort((a, b) => (b.valor - a.valor) || a.label.localeCompare(b.label, "pt-BR"));
        }
        return filtrados;
    }

    function montarHtmlSelecaoModalRanking(campo) {
        const selecionados = obterValoresFiltroAtivo(campo);
        if (!selecionados.size) return "";
        return ' · <strong class="leme-ranking-selected-count">' + selecionados.size +
            ' selecionado(s)</strong> <button type="button" class="leme-ranking-clear-btn" data-clear-ranking-campo="' +
            escapeHtml(campo) + '">Limpar</button>';
    }

    function sincronizarEstadoModalRanking() {
        if (!estadoModalRanking) return;
        const cfg = estadoModalRanking.cfg;
        const valoresAtivos = obterValoresFiltroAtivo(cfg.campoFiltro);
        const infoEl = modalContent.querySelector("#leme-ranking-selecao-info");
        if (infoEl) infoEl.innerHTML = montarHtmlSelecaoModalRanking(cfg.campoFiltro);

        const barsEl = modalContent.querySelector("#leme-ranking-lista .leme-bars");
        if (barsEl) {
            const rows = Array.from(barsEl.querySelectorAll("button.leme-ranking-row[data-filter-valor]"));
            const temVisivelAtivo = valoresAtivos.size > 0 && rows.some(r => valoresAtivos.has(r.dataset.filterValor));
            barsEl.classList.toggle("is-filtered", temVisivelAtivo);
            rows.forEach(row => {
                const val = row.dataset.filterValor;
                const ativo = valoresAtivos.has(val);
                row.classList.toggle("is-active", ativo);
                row.setAttribute("aria-pressed", ativo ? "true" : "false");
                const label = row.dataset.rankingLabel || val;
                const info = row.dataset.rankingInfo || "";
                row.title = prefixoAcaoFiltro(ativo, valoresAtivos.size) + label + info;
            });
        }

        if (cfg.parAlternavel) {
            const qtdOri = contarOrientadores(obterListaGraficoFaceta("orientador", resultadosAtuais)).length;
            const qtdCoor = contarCoorientadores(obterListaGraficoFaceta("coorientador", resultadosAtuais)).length;
            const btnOri = modalContent.querySelector('[data-modal-ranking-tipo="orientador"]');
            const btnCoor = modalContent.querySelector('[data-modal-ranking-tipo="coorientador"]');
            if (btnOri) {
                btnOri.textContent = "Orientação principal (" + qtdOri.toLocaleString("pt-BR") + ")";
                btnOri.disabled = qtdOri === 0;
            }
            if (btnCoor) {
                btnCoor.textContent = "Coorientação (" + qtdCoor.toLocaleString("pt-BR") + ")";
                btnCoor.disabled = qtdCoor === 0;
            }
        }
    }

    function renderModalRankingLista() {
        if (!estadoModalRanking) return;
        const estado = estadoModalRanking;
        const cfg = estado.cfg;
        const cortesEl = modalContent.querySelector("#leme-ranking-cortes");
        const statusEl = modalContent.querySelector("#leme-ranking-status");
        const listaEl = modalContent.querySelector("#leme-ranking-lista");
        const pagEl = modalContent.querySelector("#leme-ranking-paginacao");
        const exportarBtn = modalContent.querySelector("#leme-ranking-exportar");
        if (!cortesEl || !statusEl || !listaEl || !pagEl || !exportarBtn) return;

        Array.from(cortesEl.querySelectorAll("button[data-ranking-corte]")).forEach(btn => {
            const corteBtn = Number(btn.dataset.rankingCorte || 1);
            const qtdCorte = contarItensPorCorte(estado.dadosBrutos, corteBtn);
            const ativo = estado.corte === corteBtn;
            const rotuloBase = corteBtn === 1 ? "Todos" : ("≥ " + corteBtn);
            btn.textContent = rotuloBase + " (" + qtdCorte.toLocaleString("pt-BR") + ")";
            btn.classList.toggle("is-active", ativo);
            btn.setAttribute("aria-pressed", ativo ? "true" : "false");
            btn.disabled = qtdCorte === 0 && !ativo;
            btn.title = corteBtn === 1
                ? "Mostrar todos com pelo menos 1 defesa"
                : ("Filtrar com " + corteBtn + " ou mais defesas");
        });

        const filtrados = obterItensModalRankingFiltrados(estado);
        const totalFiltrado = filtrados.length;
        exportarBtn.disabled = totalFiltrado === 0;

        const entidadeResumo = totalFiltrado === 1 ? cfg.entidadeSingular : cfg.entidadePlural;
        const totalPaginas = Math.max(1, Math.ceil(totalFiltrado / rankingPorPagina));
        if (estado.pagina > totalPaginas) estado.pagina = totalPaginas;

        if (!totalFiltrado) {
            statusEl.innerHTML = '<span>0 ' + escapeHtml(cfg.entidadePlural) +
                ' exibidos<span id="leme-ranking-selecao-info">' + montarHtmlSelecaoModalRanking(cfg.campoFiltro) + '</span></span>' +
                '<span>Contagem: defesas ' + escapeHtml(cfg.acaoDescricao) + ' (% sobre ' + escapeHtml(estado.totalDefesas) + ')</span>';
            pagEl.innerHTML = "";

            const emTodos = (estado.corte > 1 && estado.buscaTermos.length > 0)
                ? obterItensModalRankingFiltrados(estado, 1).length
                : 0;
            if (emTodos > 0) {
                listaEl.innerHTML = '<div class="leme-ranking-empty">' +
                    '<div>Nenhum ' + escapeHtml(cfg.entidadeSingular) + ' encontrado para "' + escapeHtml(estado.busca.trim()) + '" no corte ≥ ' + estado.corte + ' (' + emTodos.toLocaleString("pt-BR") + ' correspondência(s) em Todos).</div>' +
                    '<button type="button" class="leme-ranking-rescue-btn" data-ranking-corte="1">Mostrar em Todos (≥ 1)</button>' +
                    '</div>';
            } else if (estado.buscaTermos.length > 0) {
                listaEl.innerHTML = '<div class="leme-ranking-empty"><div>Nenhum ' + escapeHtml(cfg.entidadeSingular) + ' encontrado para "' + escapeHtml(estado.busca.trim()) + '".</div></div>';
            } else {
                listaEl.innerHTML = '<div class="leme-ranking-empty"><div>Nenhum item disponível para o corte selecionado.</div></div>';
            }
            return;
        }

        const inicio = (estado.pagina - 1) * rankingPorPagina;
        const fim = Math.min(inicio + rankingPorPagina, totalFiltrado);
        const paginaItens = filtrados.slice(inicio, fim);

        const textoExibindo = totalFiltrado.toLocaleString("pt-BR") + " de " +
            estado.dadosBrutos.length.toLocaleString("pt-BR") + " " + entidadeResumo +
            (totalPaginas > 1 ? (" · pág. " + estado.pagina + " de " + totalPaginas) : "");

        statusEl.innerHTML = '<span>' + escapeHtml(textoExibindo) +
            '<span id="leme-ranking-selecao-info">' + montarHtmlSelecaoModalRanking(cfg.campoFiltro) + '</span></span>' +
            '<span>Contagem: defesas ' + escapeHtml(cfg.acaoDescricao) + ' (% sobre ' + escapeHtml(estado.totalDefesas) + ')</span>';

        listaEl.innerHTML = '<div class="leme-bars"></div>';
        const barsEl = listaEl.firstElementChild;
        const valoresAtivos = obterValoresFiltroAtivo(cfg.campoFiltro);
        const temVisivelAtivo = valoresAtivos.size > 0 && paginaItens.some(d => valoresAtivos.has(d.key));
        barsEl.classList.toggle("is-filtered", temVisivelAtivo);
        const novos = [];

        paginaItens.forEach(d => {
            const ativo = valoresAtivos.has(d.key);
            const pct = formatarPercentualPtBr(d.valor, estado.totalDefesas);
            const infoPct = " (" + d.valor + " · " + pct + ")";
            const scale = Math.max(0.03, d.valor / estado.maxGlobal);
            const scaleStr = "scaleX(" + scale.toFixed(4) + ")";

            const row = document.createElement("button");
            row.type = "button";
            row.className = "leme-bar-row leme-ranking-row is-clickable is-entering" + (ativo ? " is-active" : "");
            row.dataset.filterCampo = cfg.campoFiltro;
            row.dataset.filterValor = d.key;
            row.dataset.modalRankingRow = "1";
            row.dataset.rankingLabel = d.label;
            row.dataset.rankingInfo = infoPct;
            row.setAttribute("aria-pressed", ativo ? "true" : "false");
            row.title = prefixoAcaoFiltro(ativo, valoresAtivos.size) + d.label + infoPct;

            const rankEl = document.createElement("span");
            rankEl.className = "leme-ranking-rank";
            rankEl.textContent = "#" + d.rankOriginal;

            const labelEl = document.createElement("span");
            labelEl.className = "leme-bar-label";
            labelEl.title = d.label;
            labelEl.innerHTML = highlightText(d.label, estado.buscaTermos);

            const trackEl = document.createElement("span");
            trackEl.className = "leme-bar-track";
            const fill = document.createElement("span");
            fill.className = "leme-bar-fill";
            fill.style.transform = "scaleX(0)";
            trackEl.appendChild(fill);

            const valEl = document.createElement("span");
            valEl.className = "leme-bar-value";
            valEl.innerHTML = escapeHtml(d.valor) + ' <span class="leme-ranking-pct">(' + escapeHtml(pct) + ')</span>';

            row.appendChild(rankEl);
            row.appendChild(labelEl);
            row.appendChild(trackEl);
            row.appendChild(valEl);
            barsEl.appendChild(row);
            novos.push({ row, fill, scaleStr });
        });

        if (novos.length) {
            void barsEl.offsetWidth;
            for (let i = 0; i < novos.length; i++) {
                novos[i].row.classList.remove("is-entering");
                novos[i].fill.style.transform = novos[i].scaleStr;
            }
        }

        pagEl.innerHTML = montarHtmlPaginacao(
            totalFiltrado,
            estado.pagina,
            rankingPorPagina,
            "data-ranking-pagina",
            cfg.entidadePlural
        );
    }

    function exibirBackdropModal(elementoFoco) {
        if (!modalBackdrop.classList.contains("is-open")) {
            bodyOverflowAnterior = document.body.style.overflow;
            document.body.style.overflow = "hidden";
        }
        modalBackdrop.classList.add("is-open");
        modalBackdrop.setAttribute("aria-hidden", "false");
        if (elementoFoco && typeof elementoFoco.focus === "function") {
            elementoFoco.focus();
        }
    }

    function abrirModalRanking(tipo) {
        const cfg = RANKING_CONFIGS[tipo];
        if (!cfg) return;
        const baseRanking = cfg.coletarBase();
        const brutos = cfg.coletarDados(baseRanking);
        if (!brutos.length) return;

        if (!modalBackdrop.classList.contains("is-open")) {
            ultimoFocoAntesModal = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        }

        const dadosBrutos = brutos.map((d, idx) => ({
            key: d.key,
            label: d.label,
            valor: d.valor,
            rankOriginal: idx + 1,
            norm: normalizarBusca(d.label)
        }));
        const totalDefesas = baseRanking.length;
        const corteInicial = escolherCorteAdaptavel(dadosBrutos, cfg.corteInicial);

        estadoModalRanking = {
            tipo: tipo,
            cfg: cfg,
            dadosBrutos: dadosBrutos,
            totalDefesas: totalDefesas,
            maxGlobal: dadosBrutos[0] ? dadosBrutos[0].valor : 1,
            corte: corteInicial,
            busca: "",
            buscaTermos: [],
            ordenacao: "freq",
            pagina: 1
        };

        modalEl.classList.add("is-ranking");
        modalTitle.textContent = cfg.titulo;

        const instrucaoModal = " Clique em um ou mais itens para combinar filtros no painel (feche quando terminar).";
        let resumo;
        if (tipo === "coorientador") {
            const defsCoor = contarDefesasComCoorientacao(baseRanking);
            resumo = dadosBrutos.length.toLocaleString("pt-BR") + " " +
                (dadosBrutos.length === 1 ? "coorientador distinto" : "coorientadores distintos") +
                " em " + defsCoor.toLocaleString("pt-BR") + (defsCoor === 1 ? " defesa com coorientação" : " defesas com coorientação") +
                " (de " + totalDefesas.toLocaleString("pt-BR") + (totalDefesas === 1 ? " defesa" : " defesas") +
                " no recorte atual)." + instrucaoModal;
        } else {
            resumo = dadosBrutos.length.toLocaleString("pt-BR") + " " +
                (dadosBrutos.length === 1 ? cfg.entidadeSingular + " distinto" : cfg.entidadePlural + " distintos") +
                " em " + totalDefesas.toLocaleString("pt-BR") + (totalDefesas === 1 ? " defesa" : " defesas") +
                " do recorte atual." + instrucaoModal;
        }

        const qtdOriModal = cfg.parAlternavel ? contarOrientadores(obterListaGraficoFaceta("orientador", resultadosAtuais)).length : 0;
        const qtdCoorModal = cfg.parAlternavel ? contarCoorientadores(obterListaGraficoFaceta("coorientador", resultadosAtuais)).length : 0;
        const modeTabsHtml = cfg.parAlternavel
            ? '<div class="leme-ranking-mode-tabs" role="group" aria-label="Alternar entre orientação principal e coorientação">' +
            '<button type="button" class="leme-ranking-mode-tab' + (tipo === "orientador" ? " is-active" : "") + '" data-modal-ranking-tipo="orientador" aria-pressed="' + (tipo === "orientador" ? "true" : "false") + '"' + (qtdOriModal === 0 ? " disabled" : "") + '>Orientação principal (' + qtdOriModal.toLocaleString("pt-BR") + ')</button>' +
            '<button type="button" class="leme-ranking-mode-tab' + (tipo === "coorientador" ? " is-active" : "") + '" data-modal-ranking-tipo="coorientador" aria-pressed="' + (tipo === "coorientador" ? "true" : "false") + '"' + (qtdCoorModal === 0 ? " disabled" : "") + '>Coorientação (' + qtdCoorModal.toLocaleString("pt-BR") + ')</button>' +
            '</div>'
            : "";

        const cortesHtml = RANKING_CORTES.map(c =>
            '<button type="button" class="leme-ranking-pill" data-ranking-corte="' + c + '" aria-pressed="false"></button>'
        ).join("");

        modalContent.innerHTML =
            '<p class="leme-ranking-summary">' + escapeHtml(resumo) + '</p>' +
            modeTabsHtml +
            '<div class="leme-ranking-toolbar">' +
            '<label class="leme-sr-only" for="leme-ranking-busca">' + escapeHtml(cfg.placeholderBusca) + '</label>' +
            '<input id="leme-ranking-busca" class="leme-ranking-search" type="search" placeholder="' + escapeHtml(cfg.placeholderBusca) + '" aria-label="' + escapeHtml(cfg.placeholderBusca) + '" />' +
            '<label class="leme-sr-only" for="leme-ranking-ordenar">Ordenar ranking</label>' +
            '<select id="leme-ranking-ordenar" class="leme-sort-select" aria-label="Ordenar ranking">' +
            '<option value="freq">' + escapeHtml(cfg.rotuloOrdenacaoFreq) + '</option>' +
            '<option value="az">Ordem alfabética (A–Z)</option>' +
            '</select>' +
            '<button id="leme-ranking-exportar" class="leme-export-btn" type="button">Exportar ranking (.CSV)</button>' +
            '</div>' +
            '<div id="leme-ranking-cortes" class="leme-ranking-cortes" role="group" aria-label="Corte mínimo de defesas">' + cortesHtml + '</div>' +
            '<div id="leme-ranking-status" class="leme-ranking-status" aria-live="polite"></div>' +
            '<div id="leme-ranking-lista" class="leme-ranking-list"></div>' +
            '<nav id="leme-ranking-paginacao" class="leme-pagination" aria-label="Paginação do ranking"></nav>';

        const buscaModalInput = modalContent.querySelector("#leme-ranking-busca");
        const ordenarModalSelect = modalContent.querySelector("#leme-ranking-ordenar");
        const listaModalEl = modalContent.querySelector("#leme-ranking-lista");

        if (buscaModalInput) {
            buscaModalInput.addEventListener("input", () => {
                if (!estadoModalRanking) return;
                estadoModalRanking.busca = buscaModalInput.value || "";
                const norm = normalizarBusca(estadoModalRanking.busca);
                estadoModalRanking.buscaTermos = norm ? norm.split(" ").filter(Boolean) : [];
                estadoModalRanking.pagina = 1;
                renderModalRankingLista();
                if (listaModalEl) listaModalEl.scrollTop = 0;
            });
        }

        if (ordenarModalSelect) {
            ordenarModalSelect.addEventListener("change", () => {
                if (!estadoModalRanking) return;
                estadoModalRanking.ordenacao = ordenarModalSelect.value || "freq";
                estadoModalRanking.pagina = 1;
                renderModalRankingLista();
                if (listaModalEl) listaModalEl.scrollTop = 0;
            });
        }

        renderModalRankingLista();
        exibirBackdropModal(buscaModalInput || modalClose);
    }

    function abrirModal(item) {
        if (!item) return;
        estadoModalRanking = null;
        modalEl.classList.remove("is-ranking");
        const termos = termosBusca();
        if (!modalBackdrop.classList.contains("is-open")) {
            ultimoFocoAntesModal = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        }

        const textoBase = item.base_epistemologica
            ? highlightText(item.base_epistemologica, termos) +
            (item.base_curado_humano ? '<span class="leme-badge curated">Validado por curadoria</span>' : '')
            : '<span class="leme-badge pending">' + escapeHtml(item.base_status_label) + '</span>';

        const justificativaHtml = item.base_epistemologica && item.base_justificativa
            ? '<div class="leme-evidence-box"><b>Fundamentação identificada:</b> ' + highlightText(item.base_justificativa, termos) + '</div>'
            : "";

        const autoresRefHtml = item.autores_referenciados.length
            ? item.autores_referenciados.map(a => '<span class="leme-tag">' + highlightText(a, termos) + '</span>').join("")
            : "Não extraídos";

        const linksModal = [];
        if (item.dissertacao_link) {
            linksModal.push('<a class="leme-link pdf" href="' + escapeHtml(item.dissertacao_link) + '" target="_blank" rel="noopener noreferrer">Abrir Dissertação</a>');
        }
        if (item.produto_link) {
            linksModal.push('<a class="leme-link produto" href="' + escapeHtml(item.produto_link) + '" target="_blank" rel="noopener noreferrer">Abrir Produto no eduCAPES</a>');
        }

        const tituloModal = escopo === "produtos"
            ? (item.produto_titulo || item.dissertacao_titulo || "Detalhes do produto")
            : (item.dissertacao_titulo || "Detalhes da defesa");

        const blocoDissertacaoVinculada = escopo === "produtos"
            ? '<div class="leme-detail-item is-wide"><b>Dissertação vinculada:</b><br>' + highlightText(valorPublico(item.dissertacao_titulo), termos) + '</div>'
            : '';

        modalTitle.innerHTML = highlightText(tituloModal, termos);
        modalContent.innerHTML = '<div class="leme-detail-grid">' +
            '<div class="leme-detail-item"><b>Identificador / Ano:</b><br>' + escapeHtml(item.id) + ' · ' + escapeHtml(valorPublico(item.ano)) + '</div>' +
            '<div class="leme-detail-item"><b>Instituição / Campus:</b><br>' + highlightText(item.instituicaoCampus, termos) + '</div>' +
            '<div class="leme-detail-item"><b>Autor(a):</b><br>' + highlightText(valorPublico(item.autor), termos) + '</div>' +
            '<div class="leme-detail-item"><b>Orientador(a):</b><br>' + highlightText(valorPublico(item.orientador), termos) + (item.coorientadores.length ? '<br><small>Coorientação: ' + highlightText(item.coorientadores.join(", "), termos) + '</small>' : '') + '</div>' +
            blocoDissertacaoVinculada +
            '<div class="leme-detail-item is-wide"><b>Linha de pesquisa:</b><br>' + highlightText(valorPublico(item.linha_pesquisa_label), termos) + '</div>' +
            '<div class="leme-detail-item is-wide"><b>Macroprojeto:</b><br>' + highlightText(valorPublico(item.macroprojeto_label), termos) + '</div>' +
            '<div class="leme-detail-item is-wide"><b>Base epistemológica:</b><br>' + textoBase + justificativaHtml + '</div>' +
            '<div class="leme-detail-item is-wide"><b>Autores referenciados:</b><div class="leme-tags">' + autoresRefHtml + '</div></div>' +
            '<div class="leme-detail-item is-wide"><b>Produto educacional:</b><br>' + highlightText(valorPublico(item.produto_titulo), termos) + '</div>' +
            '<div class="leme-detail-item"><b>Tipo de produto (CAPES):</b><br>' + highlightText(valorPublico(item.tipo_produto_label), termos) + '</div>' +
            '<div class="leme-detail-item"><b>Formato do produto:</b><br>' + highlightText(valorPublico(item.formato_produto), termos) + '</div>' +
            '<div class="leme-detail-item"><b>Nível de aplicação:</b><br>' + highlightText(valorPublico(item.nivel_aplicacao), termos) + '</div>' +
            '<div class="leme-detail-item"><b>Público-alvo:</b><br>' + highlightText(item.publico_alvo_labels.join(", ") || "Não informado", termos) + '</div>' +
            '<div class="leme-detail-item is-wide"><b>Resumo da dissertação:</b><br>' + highlightText(item.dissertacao_resumo || "Resumo não disponível.", termos) + renderTags(item.termos_unificados, termos) + (linksModal.length ? '<div class="leme-actions">' + linksModal.join("") + '</div>' : '') + '</div>' +
            renderSecaoDetalhesRecolhivel(item, termos) +
            '</div>';

        exibirBackdropModal(modalClose);
    }

    function fecharModal() {
        if (!modalBackdrop.classList.contains("is-open")) return;
        estadoModalRanking = null;
        modalEl.classList.remove("is-ranking");
        modalBackdrop.classList.remove("is-open");
        modalBackdrop.setAttribute("aria-hidden", "true");
        document.body.style.overflow = bodyOverflowAnterior;
        if (ultimoFocoAntesModal && ultimoFocoAntesModal.isConnected) {
            ultimoFocoAntesModal.focus();
        }
        ultimoFocoAntesModal = null;
    }

    function manterFocoNoModal(e) {
        const focaveis = Array.from(modalEl.querySelectorAll(
            'a[href], button:not([disabled]), summary, input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )).filter(el => el.offsetParent !== null);
        if (!focaveis.length) return;
        const primeiro = focaveis[0];
        const ultimo = focaveis[focaveis.length - 1];
        if (e.shiftKey && (document.activeElement === primeiro || !modalEl.contains(document.activeElement))) {
            e.preventDefault();
            ultimo.focus();
        } else if (!e.shiftKey && (document.activeElement === ultimo || !modalEl.contains(document.activeElement))) {
            e.preventDefault();
            primeiro.focus();
        }
    }

    function csvEscape(valor) {
        let texto = String(valor == null ? "" : valor).replace(/\r\n|\r|\n/g, " ");
        if (/^[=+\-@\t\r]/.test(texto)) {
            texto = "'" + texto;
        }
        return '"' + texto.replace(/"/g, '""') + '"';
    }

    function baixarCsv() {
        if (!resultadosAtuais.length) return;
        let cols = [];
        if (escopo === "dissertacoes") {
            cols = [
                ["id", "ID"], ["ano", "Ano"], ["dissertacao_titulo", "Título da Dissertação"],
                ["autor", "Autor"], ["orientador", "Orientador"], ["coorientadores_str", "Coorientadores"],
                ["instituicaoCampus", "Instituição / Campus"],
                ["linha_pesquisa_label", "Linha de Pesquisa"], ["macroprojeto_label", "Macroprojeto"],
                ["base_status_label", "Base Epistemológica"],
                ["autores_ref_str", "Autores Referenciados"], ["dissertacao_link", "Link Dissertação"]
            ];
        } else if (escopo === "produtos") {
            cols = [
                ["id", "ID"], ["ano", "Ano"], ["produto_titulo", "Título do Produto Educacional"],
                ["tipo_produto_label", "Tipo de Produto"], ["formato_produto", "Formato do Produto"],
                ["publico_alvo_str", "Público-Alvo"],
                ["nivel_aplicacao", "Nível de Aplicação"], ["data_publicacao", "Data de Publicação"],
                ["autor", "Autor"], ["orientador", "Orientador"], ["produto_link", "Link eduCAPES"]
            ];
        } else {
            cols = [
                ["id", "ID"], ["ano", "Ano"], ["dissertacao_titulo", "Dissertação"],
                ["produto_titulo", "Produto Educacional"], ["autor", "Autor"],
                ["orientador", "Orientador"], ["coorientadores_str", "Coorientadores"],
                ["instituicaoCampus", "Instituição / Campus"],
                ["linha_pesquisa_label", "Linha de Pesquisa"], ["macroprojeto_label", "Macroprojeto"],
                ["base_status_label", "Base Epistemológica"], ["autores_ref_str", "Autores Referenciados"],
                ["tipo_produto_label", "Tipo de Produto"], ["formato_produto", "Formato do Produto"],
                ["publico_alvo_str", "Público-Alvo"],
                ["nivel_aplicacao", "Nível de Aplicação"], ["data_publicacao", "Data de Publicação"],
                ["dissertacao_link", "Link Dissertação"], ["produto_link", "Link eduCAPES"]
            ];
        }

        const linhas = [cols.map(c => csvEscape(c[1])).join(";")].concat(
            resultadosAtuais.map(item => {
                const serializado = {
                    ...item,
                    autor: valorPublico(item.autor),
                    orientador: valorPublico(item.orientador),
                    formato_produto: valorPublico(item.formato_produto),
                    coorientadores_str: item.coorientadores.join(", "),
                    autores_ref_str: item.autores_referenciados.join(", "),
                    publico_alvo_str: item.publico_alvo_labels.join(", ")
                };
                return cols.map(c => csvEscape(serializado[c[0]])).join(";");
            })
        );

        dispararDownloadCsv(linhas, "painel-leme-ept-" + escopo + "-v4.csv");
    }

    function dispararDownloadCsv(linhas, nomeArquivo) {
        const blob = new Blob(["\ufeff" + linhas.join("\n")], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = nomeArquivo;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function baixarCsvRanking() {
        if (!estadoModalRanking) return;
        const estado = estadoModalRanking;
        const cfg = estado.cfg;
        const itens = obterItensModalRankingFiltrados(estado);
        if (!itens.length) return;
        const cabecalho = ["Posição", cfg.colunaCsv, "Defesas", "Percentual (%)"].map(csvEscape).join(";");
        const linhas = [cabecalho].concat(
            itens.map(d => [
                d.rankOriginal,
                d.label,
                d.valor,
                formatarPercentualPtBr(d.valor, estado.totalDefesas)
            ].map(csvEscape).join(";"))
        );
        dispararDownloadCsv(linhas, cfg.arquivoCsv);
    }

    function definirControlesDesabilitados(disabled) {
        busca.disabled = disabled;
        limpar.disabled = disabled;
        ordenarSelect.disabled = disabled;
        btnCards.disabled = disabled;
        btnTable.disabled = disabled;
        botoesEscopo.forEach(b => { b.disabled = disabled; });
        filtros.forEach(f => { f.disabled = disabled; });
        botoesTabOrientador.forEach(b => { b.disabled = disabled; });
        botoesTabTipoProduto.forEach(b => { b.disabled = disabled; });
        botoesExpandirRanking.forEach(b => { b.disabled = disabled; });
        exportarCsv.disabled = disabled || resultadosAtuais.length === 0;
    }

    function resolverUrlsDados() {
        const urlProd = (raiz.dataset.jsonUrl || "").trim();
        const urlLocal = (raiz.dataset.jsonUrlLocal || "").trim();
        const host = (window.location && window.location.hostname || "").toLowerCase();
        const proto = (window.location && window.location.protocol || "").toLowerCase();
        const ehLocal = proto === "file:" || host === "localhost" || host === "127.0.0.1" || host === "[::1]" || host === "::1";
        const candidatos = ehLocal ? [urlLocal, urlProd] : [urlProd];
        return candidatos.filter((u, idx, arr) => Boolean(u) && arr.indexOf(u) === idx);
    }

    raiz.addEventListener("click", function (e) {
        const retryBtn = e.target.closest("[data-retry-load]");
        if (retryBtn) {
            iniciarPainel();
            return;
        }

        const scopeBtn = e.target.closest(".leme-scope button[data-escopo]");
        if (scopeBtn && !scopeBtn.disabled) {
            escopo = scopeBtn.dataset.escopo || "todas";
            botoesEscopo.forEach(btn => {
                const ativo = btn === scopeBtn;
                btn.classList.toggle("is-active", ativo);
                btn.setAttribute("aria-pressed", ativo ? "true" : "false");
            });
            aplicarFiltros(true);
            return;
        }

        const tabOriBtn = e.target.closest("[data-orientador-tab]");
        if (tabOriBtn && !tabOriBtn.disabled) {
            modoCardOrientador = tabOriBtn.dataset.orientadorTab || "orientador";
            renderCardOrientadores(resultadosAtuais);
            return;
        }

        const tabTipoBtn = e.target.closest("[data-tipo-tab]");
        if (tabTipoBtn && !tabTipoBtn.disabled) {
            modoCardTipoProduto = tabTipoBtn.dataset.tipoTab || "tipo_produto";
            renderCardTipoProduto(resultadosAtuais);
            return;
        }

        const openRankingBtn = e.target.closest("[data-open-ranking]");
        if (openRankingBtn && !openRankingBtn.disabled) {
            abrirModalRanking(openRankingBtn.dataset.openRanking);
            return;
        }

        const modalModeBtn = e.target.closest("[data-modal-ranking-tipo]");
        if (modalModeBtn && !modalModeBtn.disabled && estadoModalRanking) {
            const novoTipo = modalModeBtn.dataset.modalRankingTipo;
            if (novoTipo && novoTipo !== estadoModalRanking.tipo) {
                abrirModalRanking(novoTipo);
            }
            return;
        }

        const corteBtn = e.target.closest("[data-ranking-corte]");
        if (corteBtn && !corteBtn.disabled && estadoModalRanking) {
            estadoModalRanking.corte = Number(corteBtn.dataset.rankingCorte || 1);
            estadoModalRanking.pagina = 1;
            renderModalRankingLista();
            const listaEl = modalContent.querySelector("#leme-ranking-lista");
            if (listaEl) listaEl.scrollTop = 0;
            if (corteBtn.classList.contains("leme-ranking-rescue-btn")) {
                const buscaEl = modalContent.querySelector("#leme-ranking-busca");
                if (buscaEl) buscaEl.focus();
            }
            return;
        }

        const rankingPageBtn = e.target.closest(".leme-page-btn[data-ranking-pagina]");
        if (rankingPageBtn && !rankingPageBtn.disabled && estadoModalRanking) {
            estadoModalRanking.pagina = Number(rankingPageBtn.dataset.rankingPagina || 1);
            renderModalRankingLista();
            const listaEl = modalContent.querySelector("#leme-ranking-lista");
            if (listaEl) listaEl.scrollTop = 0;
            const ativoPag = modalContent.querySelector("#leme-ranking-paginacao .leme-page-btn.is-active");
            if (ativoPag) ativoPag.focus();
            return;
        }

        const exportRankingBtn = e.target.closest("#leme-ranking-exportar");
        if (exportRankingBtn && !exportRankingBtn.disabled && estadoModalRanking) {
            baixarCsvRanking();
            return;
        }

        const filterTrigger = e.target.closest("[data-filter-campo][data-filter-valor]");
        if (filterTrigger) {
            alternarFiltroInterativo(filterTrigger.dataset.filterCampo, filterTrigger.dataset.filterValor);
            if (filterTrigger.dataset.modalRankingRow === "1" && estadoModalRanking) {
                sincronizarEstadoModalRanking();
            }
            return;
        }

        const pageBtn = e.target.closest(".leme-page-btn[data-pagina]");
        if (pageBtn && !pageBtn.disabled) {
            paginaAtual = Number(pageBtn.dataset.pagina || 1);
            atualizarVisualizacao();
            raiz.querySelector("#leme-resultados-area").scrollIntoView({ behavior: "smooth", block: "start" });
            return;
        }

        const detailBtn = e.target.closest("[data-id].leme-card-detail-btn, [data-id].leme-table-detail-btn");
        if (detailBtn) {
            abrirModal(dadosPorId.get(detailBtn.dataset.id));
            return;
        }

        const clearRankingCampo = e.target.closest("[data-clear-ranking-campo]");
        if (clearRankingCampo && estadoModalRanking) {
            const set = filtrosSelecionados.get(clearRankingCampo.dataset.clearRankingCampo);
            if (set) set.clear();
            aplicarFiltros(true);
            sincronizarEstadoModalRanking();
            return;
        }

        const clearFilterBtn = e.target.closest("[data-clear-filter-campo][data-clear-filter-valor]");
        if (clearFilterBtn) {
            const set = filtrosSelecionados.get(clearFilterBtn.dataset.clearFilterCampo);
            if (set) set.delete(clearFilterBtn.dataset.clearFilterValor);
            aplicarFiltros(true);
            return;
        }

        const clearAllBtn = e.target.closest("[data-clear-all-filters]");
        if (clearAllBtn) {
            limparTodosFiltros();
            return;
        }

        const clearSearch = e.target.closest("[data-clear-search]");
        if (clearSearch) {
            busca.value = "";
            aplicarFiltros(true);
            busca.focus();
        }
    });

    filtros.forEach(filtro => filtro.addEventListener("change", () => {
        if (filtro.value === MULTI_SELECT_SENTINEL) return;
        const set = filtrosSelecionados.get(filtro.dataset.campo);
        if (set) {
            set.clear();
            if (filtro.value) set.add(filtro.value);
        }
        aplicarFiltros(true);
    }));
    ordenarSelect.addEventListener("change", () => {
        ordenacao = ordenarSelect.value || "ano_desc";
        paginaAtual = 1;
        resultadosAtuais = ordenarResultados(resultadosAtuais);
        atualizarVisualizacao();
    });
    busca.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => aplicarFiltros(true), 200);
    });
    busca.addEventListener("keydown", e => {
        if (e.key === "Escape") { busca.value = ""; aplicarFiltros(true); }
    });
    limpar.addEventListener("click", limparTodosFiltros);
    btnCards.addEventListener("click", () => { modo = "cards"; atualizarVisualizacao(); });
    btnTable.addEventListener("click", () => { modo = "table"; atualizarVisualizacao(); });
    exportarCsv.addEventListener("click", baixarCsv);
    modalClose.addEventListener("click", fecharModal);
    modalBackdrop.addEventListener("click", e => { if (e.target === modalBackdrop) fecharModal(); });
    if (typeof mqMobile.addEventListener === "function") {
        mqMobile.addEventListener("change", () => { if (dados.length) atualizarVisualizacao(); });
    } else if (typeof mqMobile.addListener === "function") {
        mqMobile.addListener(() => { if (dados.length) atualizarVisualizacao(); });
    }
    document.addEventListener("keydown", e => {
        if (!raiz.isConnected || !modalBackdrop.classList.contains("is-open")) return;
        if (e.key === "Escape") {
            e.preventDefault();
            fecharModal();
        } else if (e.key === "Tab") {
            manterFocoNoModal(e);
        }
    });

    async function carregarPayloadJson(urls) {
        let ultimoErro = null;
        for (let i = 0; i < urls.length; i++) {
            try {
                const resposta = await fetch(urls[i], { cache: "no-cache" });
                if (!resposta.ok) throw new Error("Falha HTTP " + resposta.status + " em " + urls[i]);
                return await resposta.json();
            } catch (err) {
                ultimoErro = err;
            }
        }
        throw ultimoErro || new Error("Nenhuma URL de dados configurada.");
    }

    async function iniciarPainel() {
        definirControlesDesabilitados(true);
        contador.textContent = "Carregando resultados...";
        graficosNota.textContent = "Carregando indicadores...";
        try {
            const urls = resolverUrlsDados();
            if (!urls.length) throw new Error("A URL do JSON não foi configurada.");

            const payload = await carregarPayloadJson(urls);
            if (!payload || typeof payload !== "object") {
                throw new Error("O JSON v4 retornou um formato inválido.");
            }
            const defesas = Array.isArray(payload) ? payload : payload.defesas;
            if (!Array.isArray(defesas)) throw new Error("O JSON v4 não contém a lista 'defesas'.");

            const totalDefesasNum = Number(payload.total_defesas);
            const totalProducoesNum = Number(payload.total_producoes);
            metaRaiz = {
                total_defesas: Number.isFinite(totalDefesasNum) ? totalDefesasNum : defesas.length,
                total_producoes: Number.isFinite(totalProducoesNum) ? totalProducoesNum : (defesas.length * 2),
                gerado_em: typeof payload.gerado_em === "string" ? payload.gerado_em : ""
            };

            dados = defesas.map(normalizarRegistroV4);
            consolidarOrientadores(dados);
            construirIndiceFacetas(dados);
            dadosPorId = new Map(dados.map(item => [item.id, item]));

            definirControlesDesabilitados(false);
            atualizarIndicadores();
            aplicarFiltros(true);
        } catch (erro) {
            console.error("Falha ao carregar o painel ProfEPT v4:", erro);
            definirControlesDesabilitados(true);
            periodoEl.textContent = "Indisponível";
            geradoEmEl.textContent = "";
            if (statCoorientadoresEl) statCoorientadoresEl.textContent = "";
            contador.textContent = "Não foi possível carregar os dados.";
            graficosNota.textContent = "Dados indisponíveis";
            insights.innerHTML = '<div class="leme-insight-card"><strong>Indisponível</strong><span>Não foi possível carregar os indicadores bibliométricos.</span></div>';
            [chartAnoEl, chartLinhaEl, chartMacroEl, chartOrientadorEl, chartBaseEl, chartAutoresRefEl, chartTipoEl, chartPublicoEl, chartNivelEl, chartFormatoEl]
                .forEach(el => {
                    if (el) el.innerHTML = '<div class="leme-empty-chart">Dados indisponíveis no momento.</div>';
                });
            paginacao.innerHTML = "";
            resultados.innerHTML = '<div class="leme-empty"><p>O catálogo está temporariamente indisponível. Verifique a disponibilidade do arquivo JSON v4.</p><button type="button" class="leme-retry-btn" data-retry-load="1">Tentar novamente</button></div>';
        }
    }

    iniciarPainel();
})();

