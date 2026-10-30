# Classificação do tipo de produto educacional

## Regra de decisão

O tipo principal descreve o formato educacional específico do produto. A coleção eduCAPES e `dc.type` são metadados do repositório e podem ser mais amplos que esse formato.

1. Leia a descrição do produto na dissertação e, se houver, a ficha ou o próprio produto.
2. Registre o texto do formato exatamente como a fonte o apresenta e guarde página ou campo de origem.
3. Compare com `dc.description.abstract`, `dc.type` e coleção eduCAPES. Não deixe uma categoria ampla sobrescrever uma declaração específica.
4. Normalize o formato declarado para o vocabulário canônico. Se houver conflito entre fontes específicas, mantenha o tipo sem confirmação e encaminhe para revisão.
5. Não infira um tipo por título, palavra-chave ou extensão do arquivo isoladamente.

## Vocabulário inicial

| Rótulo observado | Tipo canônico | Condição |
| --- | --- | --- |
| Portal | `portal` | Formato/plataforma nomeado no produto. |
| Aula Digital | `guia_tutorial` | Usar a equivalência acordada para guia/tutorial. |
| Áudio / Áudios | `podcast` | Usar quando a fonte apresentar o produto como áudio/podcast. |
| Animação / Vídeos | `video_audiovisual` | Confirmar que o objeto é o produto audiovisual, não apenas uma coleção do repositório. |
| E-book / livro digital | `ebook` | “Livro digital” de coleção ou `dc.type` isoladamente não basta para distinguir o formato específico. |
| Cartilha | `cartilha` | Preservar a designação explícita. |
| História em quadrinhos / HQ | `historia_em_quadrinhos` | Preservar a designação explícita. |
| Infográfico | `infografico` | Preservar a designação explícita. |

O vocabulário é extensível. Não criar equivalência automática para rótulo novo sem comparar exemplos e verificar se ele descreve formato, recurso pedagógico, suporte ou coleção.

## Primeira aplicação aos cinco produtos pareados

As propostas da amostra estão em `dados/revisao/classificacao_produtos_5_v1.json`. O usuário confirmou confiança alta e os cinco formatos específicos: Cartilha (EPT-0001), E-book (EPT-0003), Infográfico (EPT-0005), História em quadrinhos (EPT-0008) e E-book (EPT-0010). Em EPT-0005 a coleção recuperada é “Vídeos”, mas a dissertação chama o produto de infográfico; a divergência permanece na proveniência, sem alterar o tipo confirmado. EPT-0008 não tem metadados eduCAPES recuperados, então a classificação confirmada se apoia na evidência explícita do PDF.

Esta é uma classificação de amostra, não uma equivalência global de coleções. Na próxima rodada, revisar os casos ambíguos/discordantes e só então ampliar o dicionário. GPT pode auxiliar a localizar e comparar trechos, mas não deve inferir o tipo apenas de palavras-chave ou do título.

## Integração futura

Na planilha, separar colunas para rótulo declarado, tipo canônico proposto, `dc.type`, coleção, evidência/localizador, confiança, conflito e decisão humana. O JSON final recebe o tipo canônico somente após a regra de confiança e revisão definida no contrato; dados originais do repositório permanecem em campos próprios.
