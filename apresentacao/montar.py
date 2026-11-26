"""Gera apresentacao/apresentacao.pptx do T4 no mesmo padrao visual do T2/T3:
  - Tela widescreen 13,333 x 7,5 pol, cabecalho navy 34 pt, paginacao no topo
    direito, glossario no rodape esquerdo, prosa natural sem travessoes/hifens
    artificiais e explicacao explicita de todas as figuras e graficos.
  - Os primeiros slides cobrem os 2 minutos iniciais explicando o problema
    de Planchon-Darboux para a turma."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "relatorio"))
import dados
import gerar_graficos

FIG = RAIZ / "apresentacao" / "figuras"
SAIDA = RAIZ / "apresentacao" / "apresentacao.pptx"

NAVY = RGBColor(0x1E, 0x3A, 0x5F)
INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x4B, 0x55, 0x63)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

CHAVES = (
    "MPI_Allreduce", "MPI_Scatterv", "MPI_Sendrecv", "MPI_Isend", "MPI_Irecv",
    "MPI_Waitall", "MPI_Bcast", "MPI_Reduce", "MPI_Barrier", "MPI_Wtime",
    "MPI_PROC_NULL", "Planchon e Darboux", "Planchon Darboux", "Amdahl",
    "fases paralelas", "computação local", "verificação", "troca de bordas",
    "verif_min", "verif_med", "espera", "hyperthreading", "speedup",
    "eficiência", "linhas fantasmas", "halo", "soleira",
)


def set_run(run, size: float, bold: bool, color: RGBColor, name: str = "Calibri") -> None:
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = name


def shade(cell, rgb_tuple: tuple[int, int, int]) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("a:solidFill")):
        tc_pr.remove(old)
    solid = etree.SubElement(tc_pr, qn("a:solidFill"))
    srgb = etree.SubElement(solid, qn("a:srgbClr"))
    srgb.set("val", f"{rgb_tuple[0]:02X}{rgb_tuple[1]:02X}{rgb_tuple[2]:02X}")


def blocos(text: str) -> list[str]:
    itens, atual = [], []
    for ln in text.split("\n"):
        s = ln.strip()
        if s == "":
            if atual:
                itens.append(" ".join(atual))
                atual = []
        else:
            atual.append(s)
    if atual:
        itens.append(" ".join(atual))
    return itens


def escrever(paragraph, text: str, size: float, bold: bool, color: RGBColor, nome: str = "Calibri") -> None:
    padrao = re.compile("(" + "|".join(re.escape(c) for c in sorted(CHAVES, key=len, reverse=True)) + ")")
    for parte in padrao.split(text) or [text]:
        if parte == "":
            continue
        run = paragraph.add_run()
        run.text = parte
        if parte in CHAVES:
            set_run(run, size, True, NAVY, nome)
        else:
            set_run(run, size, bold, color, nome)


def add_text(slide, x: float, y: float, w: float, h: float, text: str,
             size: float = 15, bold: bool = False, color: RGBColor = INK,
             align=PP_ALIGN.LEFT, lista: bool = False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    linhas = blocos(text) if lista else text.split("\n")
    for i, line in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(3 if lista else 2)
        p.space_before = Pt(0)
        if lista:
            p_pr = p._p.get_or_add_pPr()
            p_pr.set("marL", str(int(Inches(0.28))))
            p_pr.set("indent", str(int(Inches(-0.22))))
            bu_font = etree.SubElement(p_pr, qn("a:buFont"))
            bu_font.set("typeface", "Arial")
            bu_clr = etree.SubElement(p_pr, qn("a:buClr"))
            bu_rgb = etree.SubElement(bu_clr, qn("a:srgbClr"))
            bu_rgb.set("val", "1E3A5F")
            bu = etree.SubElement(p_pr, qn("a:buChar"))
            bu.set("char", "●")
        escrever(p, line, size, bold, color)
    return box


def chrome(slide, title: str, page: int, total: int) -> None:
    add_text(slide, 0.36, 0.08, 10.6, 1.10, title, 31, True, NAVY)
    add_text(slide, 11.1, 0.12, 1.9, 0.36, f"{page} / {total}", 16, False, MUTED, PP_ALIGN.RIGHT)


def legenda(slide, linhas: list[str], escuro: bool = False) -> None:
    n = len(linhas)
    quebras = sum(1 for ln in linhas if len(ln) > 58)
    altura = 0.20 * n + 0.12 * quebras + 0.05
    y = 7.5 - 0.08 - altura
    box = slide.shapes.add_textbox(Inches(0.28), Inches(y), Inches(12.6), Inches(altura))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    palavra_cor = RGBColor(0xD6, 0xE4, 0xF5) if escuro else NAVY
    texto_cor = RGBColor(0xE8, 0xEE, 0xF6) if escuro else MUTED
    for i, linha in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(0)
        p.space_before = Pt(0)
        if ":" in linha:
            palavra, resto = linha.split(":", 1)
            r1 = p.add_run()
            r1.text = palavra + ":"
            set_run(r1, 10, True, palavra_cor)
            r2 = p.add_run()
            r2.text = resto
            set_run(r2, 10, False, texto_cor)
        else:
            r = p.add_run()
            r.text = linha
            set_run(r, 10, False, texto_cor)


def codigo(slide, x: float, y: float, w: float, h: float, texto: str):
    caixa = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    caixa.fill.solid()
    caixa.fill.fore_color.rgb = RGBColor(0xF3, 0xF0, 0xE8)
    caixa.line.color.rgb = RGBColor(0xD2, 0xCB, 0xBE)
    caixa.line.width = Pt(0.75)
    tf = caixa.text_frame
    tf.word_wrap = False
    tf.auto_size = None
    tf.margin_left = Inches(0.12)
    tf.margin_top = Inches(0.08)
    for i, linha in enumerate(texto.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(0)
        run = p.add_run()
        run.text = linha if linha else " "
        set_run(run, 11.5, False, MUTED if linha.strip().startswith("//") else INK, "Consolas")
    return caixa


def table(slide, x: float, y: float, w: float, h: float, data: list[list[str]],
          sizes: list[float] | None = None, fonte: float = 12) -> None:
    rows, cols = len(data), len(data[0])
    shape = slide.shapes.add_table(rows, cols, Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = shape.table
    if sizes:
        for i, s in enumerate(sizes):
            tbl.columns[i].width = Inches(s)
    row_h = Inches(h / rows)
    for r, row in enumerate(data):
        tbl.rows[r].height = row_h
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = ""
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = str(val)
            if r == 0:
                set_run(run, fonte, True, WHITE)
                shade(cell, (0x1E, 0x3A, 0x5F))
            else:
                set_run(run, fonte, c == 0, INK)
                if r % 2 == 0:
                    shade(cell, (0xEE, 0xF2, 0xF7))


def build() -> None:
    gerar_graficos.main()
    ctx = dados.carregar()

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "T4 fases paralelas com MPI"
    prs.core_properties.author = "Bernardo Klein Heitz"
    blank = prs.slide_layouts[6]

    total = 12
    page = 1

    def next_page() -> int:
        nonlocal page
        page += 1
        return page

    p1 = ctx["por_p"][1]
    p8 = ctx["por_p"][8]
    p16 = ctx["por_p"][16]
    p32 = ctx["por_p"][32]
    p64 = ctx["por_p"][64]
    bc32 = ctx["bcast_por_p"][32]
    bc64 = ctx["bcast_por_p"][64]
    fator_bc64 = bc64["verif_min"] / max(p64["verif_min"], 1e-9)

    # 1. Capa
    s = prs.slides.add_slide(blank)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    add_text(s, 0.7, 1.45, 12, 0.4, "Computação Paralela  ·  Trabalho 4", 16, False, RGBColor(0xC5, 0xD4, 0xE8))
    add_text(s, 0.7, 2.05, 12, 1.5, "Preenchimento de depressões em relevo\nno modelo de fases paralelas com MPI", 36, True, WHITE)
    add_text(
        s, 0.7, 4.05, 11, 1.5,
        "Aluno: Bernardo Klein Heitz\n"
        "github.com/bengo501/Trabalho4-Computacao-Paralela\n"
        "Cluster Atlântica, nós atlantica07 a atlantica10 exclusivos",
        16, False, RGBColor(0xC5, 0xD4, 0xE8),
    )
    legenda(
        s,
        [
            "fases paralelas: computação local, verificação coletiva de parada e troca de bordas",
            "Planchon e Darboux: algoritmo hidrológico que nivela depressões em modelos de elevação",
            "parada pelos dados: termina apenas quando nenhuma altitude da água muda em nenhum processo",
        ],
        escuro=True,
    )

    # 2. Explicacao do problema para a turma (primeiros 2 minutos - parte 1)
    s = prs.slides.add_slide(blank)
    chrome(s, "O problema: preencher depressões em mapas de relevo", next_page(), total)
    add_text(
        s, 0.4, 1.35, 12.5, 5.1,
        "Em hidrologia e geoprocessamento, um Modelo Digital de Elevação representa o terreno como "
        "uma matriz de altitudes Z. Quando simulamos para onde a água da chuva escoa, crateras "
        "naturais e ruídos de satélite prendem o fluxo em buracos sem saída e interrompem os rios.\n\n"
        "O algoritmo de Planchon e Darboux resolve esse problema simulando uma inundação completa. "
        "No início, as bordas externas do mapa mantêm a altura real Z por onde a água pode sair, "
        "enquanto todo o interior começa coberto por uma coluna de água muito alta W.\n\n"
        "A cada iteração, cada célula compara seu nível de água W com os 8 vizinhos ao redor. "
        "Se os vizinhos forem mais baixos, o excesso escoa, respeitando sempre o piso da rocha Z: "
        "a nova cota passa a ser o maior valor entre Z e o menor nível W dos vizinhos.\n\n"
        "Onde existe caminho aberto até a borda do mapa, toda a água vai embora e sobra W igual a Z. "
        "Onde existe uma cratera fechada, a água desce até a altura exata da borda mais baixa daquela "
        "bacia, chamada de soleira, formando uma superfície plana pronta para escoar.\n\n"
        "Não existe um número fixo de passos: um terreno plano drena rápido, enquanto bacias com "
        "canais sinuosos exigem milhares de passos. O algoritmo só para quando nenhuma célula muda.",
        14.5, False, INK, lista=True,
    )
    legenda(s, [
        "DEM (Z): matriz com a altitude original da rocha em cada ponto do terreno",
        "superfície W: nível atual da água sobre o terreno, que vai baixando a cada iteração",
        "soleira: ponto mais baixo da borda de uma cratera, que define o nível final do lago retido",
    ])

    # 3. Explicacao visual do problema para a turma (primeiros 2 minutos - parte 2)
    s = prs.slides.add_slide(blank)
    chrome(s, "O relevo antes e depois do nivelamento das bacias", next_page(), total)
    s.shapes.add_picture(str(FIG / "relevo_lagos.png"), Inches(0.28), Inches(1.28), Inches(12.75))
    add_text(
        s, 0.4, 5.28, 12.5, 1.45,
        "Os três painéis acima foram gerados diretamente pela nossa execução no cluster. "
        "À esquerda vemos o terreno original Z com colinas, bacia central encaixada, crateras e as "
        "linhas tracejadas brancas mostrando como o mapa é fatiado em faixas horizontais entre os "
        "processos MPI. No centro, os tons de azul mostram a água retida onde W ficou maior que Z "
        "após o escoamento. À direita, o corte na linha amarela mostra a rocha marrom e a água azul "
        "estabilizada exatamente na altura da soleira de saída.",
        14, False, INK, lista=True,
    )
    legenda(s, [
        "faixas 1/P: cada processo MPI recebe um bloco contíguo de linhas horizontais do mapa",
        "água retida (W menos Z): volume acumulado dentro das depressões fechadas após convergir",
    ])

    # 4. Modelo de fases paralelas
    s = prs.slides.add_slide(blank)
    chrome(s, "As três fases paralelas sincronizadas a cada iteração", next_page(), total)
    s.shapes.add_picture(str(FIG / "modelo_fases.png"), Inches(0.35), Inches(1.25), Inches(12.5))
    add_text(
        s, 0.4, 5.20, 12.5, 1.55,
        "A figura ilustra uma iteração com quatro processos. Na fase 1 (azul), cada rank atualiza "
        "sua faixa local, mas as faixas da bacia central têm mais células alagadas ativas e demoram "
        "mais que as faixas costeiras. Na fase 2 (laranja), todos combinam o critério de parada em "
        "um único MPI_Allreduce: quem terminou cedo espera na área tracejada pelo processo mais lento. "
        "Se alguém parasse sozinho, o vizinho travaria esperando bordas na iteração seguinte. "
        "Se ainda houve mudança, a fase 3 (verde) troca uma linha de borda entre vizinhos.",
        13.8, False, INK, lista=True,
    )
    legenda(s, [
        "fase 1: computação local na faixa 1/P com duplo buffer para não depender de P",
        "fase 2: MPI_Allreduce combina mudou_local de todos os processos para decidir a parada juntos",
        "fase 3: troca das linhas de fronteira entre rank r e seus vizinhos imediatos r menos 1 e r mais 1",
    ])

    # 5. Codigo das 3 fases e troca de halo
    s = prs.slides.add_slide(blank)
    chrome(s, "Implementação das fases e troca em full duplex", next_page(), total)
    codigo(
        s, 0.38, 1.32, 6.35, 4.75,
        "for (;;) {\n"
        "  // Fase 1: computacao local na faixa 1/P\n"
        "  int mudou_loc = passo_planchon_darboux(\n"
        "      w_a, w_b, z_loc, n, ini, linhas);\n"
        "  int *tmp = w_a; w_a = w_b; w_b = tmp;\n\n"
        "  // Fase 2: verificacao coletiva da parada\n"
        "  int mudou_glob = 0;\n"
        "  MPI_Allreduce(&mudou_loc, &mudou_glob,\n"
        "                1, MPI_INT, MPI_LOR, COMM);\n"
        "  if (!mudou_glob) break;\n\n"
        "  // Fase 3: troca de bordas com vizinhos\n"
        "  trocar_bordas(w_a, n, linhas, acima, abaixo);\n"
        "}"
    )
    add_text(
        s, 6.95, 1.35, 5.95, 4.85,
        "Usamos duplo buffer (w_a e w_b): cada célula calcula seu próximo nível lendo apenas os "
        "valores da iteração anterior. Isso garante que a trajetória matemática seja idêntica no "
        "sequencial e em qualquer número de processos P.\n\n"
        "Cada processo aloca duas linhas fantasmas (halo superior na posição 0 e inferior na "
        "posição linhas mais 1) para enxergar a fronteira dos vizinhos.\n\n"
        "Na função trocar_bordas, disparamos duas recepções MPI_Irecv e dois envios MPI_Isend "
        "ao mesmo tempo e fechamos com MPI_Waitall. Assim as mensagens que sobem e descem entre "
        "os nós trafegam em paralelo pela rede, sem fila em cascata.\n\n"
        "Nas extremidades norte (rank 0) e sul (rank P menos 1), o vizinho inexistente recebe "
        "MPI_PROC_NULL, mantendo o código único e livre de impasse.",
        13.8, False, INK, lista=True,
    )
    legenda(s, [
        "linhas fantasmas (halo): cópias locais da última linha do vizinho de cima e da primeira do de baixo",
        "MPI_PROC_NULL: destino nulo do MPI que transforma envios de borda externa em operação vazia segura",
    ])

    # 6. Equivalencia e fracao sequencial de Amdahl
    s = prs.slides.add_slide(blank)
    chrome(s, "Equivalência demonstrada e teto da Lei de Amdahl", next_page(), total)
    add_text(
        s, 0.4, 1.38, 12.5, 5.0,
        f"A entrada oficial usa uma grade de {ctx['n']} por {ctx['n']} células (múltiplo exato de 64, "
        "dando o mesmo número de linhas a cada processo). Todas as execuções sequenciais e paralelas "
        f"convergiram em exatas {ctx['iteracoes']} iterações, com {ctx['celulas_alagadas']} células "
        f"alagadas e volume retido igual a {ctx['volume_retido']}.\n\n"
        "O programa sequencial é compilado com gcc puro sem biblioteca MPI e compartilha o mesmo "
        "objeto numérico relevo.o da versão paralela, ambos com otimização O3 e padrão C11.\n\n"
        f"Na versão sequencial, o tempo total mediano de dez repetições foi T1 igual a {ctx['t1_txt']} s "
        f"(entre {ctx['t1_min_txt']} s e {ctx['t1_max_txt']} s). A construção inicial do modelo de "
        f"elevação na memória levou {ctx['t_serial_txt']} s antes do laço paralelizável.\n\n"
        f"Isso define a fração sequencial medida s igual a {ctx['frac_s_pct']}. Com ela calculamos "
        "a curva do teto de Amdahl pela expressão 1 dividido por (s mais (1 menos s) sobre P), "
        f"cujo limite assintótico 1 sobre s é {ctx['amdahl_inf_txt']}.",
        14.8, False, INK, lista=True,
    )
    legenda(s, [
        "equivalência: iterações, células alagadas e volume retido conferidos automaticamente em cada rodada",
        "fração sequencial s: parcela de T1 correspondente à geração inicial do terreno antes das fases paralelas",
        "teto de Amdahl: maior speedup possível caso não existisse custo de rede nem desbalanceamento",
    ])

    # 7. Ambiente e topologia de nos
    s = prs.slides.add_slide(blank)
    chrome(s, "Protocolo no Atlântica: mínimo de nós exclusivos por P", next_page(), total)
    s.shapes.add_picture(str(FIG / "topologia_nos.png"), Inches(0.35), Inches(1.32), Inches(12.55))
    add_text(
        s, 0.4, 4.75, 12.5, 1.95,
        "A figura resume o mapeamento exigido pelo enunciado sobre os nós Xeon E5520 do Atlântica "
        "(8 núcleos físicos e 16 threads por nó). Até P igual a 8 usamos 1 nó exclusivo (atlantica07) "
        "com fixação em núcleos físicos. Em P igual a 16 usamos 2 nós exclusivos (07 e 08), mantendo "
        "um processo por núcleo físico. Em P igual a 32 usamos 4 nós exclusivos (07 a 10, totalizando "
        "32 núcleos físicos). Em P igual a 64 mantemos os mesmos 4 nós e ocupamos as duas threads "
        "de cada núcleo físico para avaliar isoladamente o efeito do hyperthreading.",
        14.2, False, INK, lista=True,
    )
    legenda(s, [
        "nós exclusivos: reserva dedicada no Slurm para evitar interferência de outros jobs na CPU e na rede",
        "cpu bind cores/threads: garante 1 processo por núcleo físico até P=32 e ativa HT apenas em P=64",
    ])

    # 8. Speed-up e Eficiencia
    s = prs.slides.add_slide(blank)
    chrome(s, "Speedup, eficiência e distância até o teto de Amdahl", next_page(), total)
    s.shapes.add_picture(str(FIG / "speedup_slides.png"), Inches(5.35), Inches(1.28), Inches(7.7))
    tab1 = [["P", "Nós", "Mediana (s)", "S", "Amdahl", "E"]]
    for item in ctx["serie"]:
        tab1.append([
            str(item["p"]), str(item["nos"]), item["tp_txt"],
            item["s_txt"], item["amdahl_txt"], item["e_txt"],
        ])
    table(s, 0.32, 1.35, 4.85, 3.10, tab1, [0.55, 0.55, 1.15, 0.85, 0.95, 0.80], fonte=11.5)
    add_text(
        s, 0.35, 4.65, 12.6, 2.1,
        f"O gráfico da esquerda traz as três curvas pedidas: a reta pontilhada ideal (S igual a P), "
        f"a curva tracejada laranja do teto de Amdahl (s igual a {ctx['frac_s_pct']}) e a curva azul "
        f"do speedup medido; o gráfico da direita mostra a eficiência E igual a S sobre P.\n\n"
        f"Em 1 nó os 8 processos disputam o mesmo barramento de memória ({p8['s_txt']} em P igual a 8, "
        f"E igual a {p8['e_txt']}). Ao abrir para 2 nós (P igual a 16) as fatias cabem melhor na cache L3, "
        f"elevando a eficiência para {p16['e_txt']} (S igual a {p16['s_txt']}), e em 4 nós (P igual a 32) "
        f"atinge {p32['s_txt']} contra {p32['amdahl_txt']} do teto de Amdahl. A distância entre a curva azul "
        "e a laranja vem da espera pela bacia central mais carregada somada à comunicação entre nós.",
        13.6, False, INK, lista=True,
    )
    legenda(s, [
        "tabela 1: medianas de dez repetições por ponto (mínimo e máximo completos constam no relatório)",
        "distância para Amdahl: causada por espera de desbalanceamento topográfico mais rede, não por código serial",
    ])

    # 9. Divisao por fase e espera
    s = prs.slides.add_slide(blank)
    chrome(s, "Divisão do tempo por fase: separando comunicação e espera", next_page(), total)
    s.shapes.add_picture(str(FIG / "fases_slides.png"), Inches(5.55), Inches(1.28), Inches(7.5))
    tab2 = [["P", "Comp.", "Verif. méd", "Verif. mín", "Espera", "Troca"]]
    for item in ctx["serie"]:
        tab2.append([
            str(item["p"]), item["comp_txt"], item["verif_med_txt"],
            item["verif_min_txt"], item["espera_txt"], item["troca_txt"],
        ])
    table(s, 0.30, 1.35, 5.05, 3.10, tab2, [0.50, 0.90, 0.95, 0.95, 0.90, 0.85], fonte=11.0)
    add_text(
        s, 0.35, 4.65, 12.6, 2.1,
        "Os gráficos de barras empilhadas mostram a média entre os processos em toda a série (à esquerda) "
        "e a ampliação de P igual a 8 a 64 (à direita), dividindo a verificação em duas cores: "
        "vermelho para o menor tempo entre os processos (verif_min) e amarelo para a espera.\n\n"
        "Como o processo mais lento nas faixas centrais chega por último ao MPI_Allreduce, ele quase "
        f"não espera: verif_min mede o custo puro da comunicação ({p32['verif_min_txt']} s em P igual a 32). "
        f"Já os processos das bordas costeiras secam cedo e aguardam: a diferença verif_med menos "
        f"verif_min chega a {p32['espera_txt']} s em P igual a 32, superando a troca de bordas ({p32['troca_txt']} s).",
        13.5, False, INK, lista=True,
    )
    legenda(s, [
        "verif_min: menor tempo de verificação entre os P ranks, equivalente ao custo puro da coletiva",
        "espera (verif_med menos verif_min): tempo médio que os ranks rápidos passam aguardando o mais lento",
    ])

    # 10. Allreduce vs P Broadcasts
    s = prs.slides.add_slide(blank)
    chrome(s, "Coletiva da parada: um MPI_Allreduce contra P broadcasts", next_page(), total)
    s.shapes.add_picture(str(FIG / "allreduce_vs_bcast.png"), Inches(0.35), Inches(1.35), Inches(7.1))
    add_text(
        s, 7.65, 1.38, 5.3, 4.95,
        "O gráfico à esquerda compara o menor tempo de verificação (verif_min) medido no cluster "
        f"entre duas formas de combinar o critério de parada nas mesmas {ctx['iteracoes']} iterações.\n\n"
        "Em azul usamos um único MPI_Allreduce com operação lógica MPI_LOR: o Open MPI combina e "
        "espalha o resultado em árvore em O(log P) passos.\n\n"
        "Em vermelho executamos P chamadas MPI_Bcast, uma por processo em sequência, o que eleva "
        "o custo para O(P log P) mensagens coletivas por iteração.\n\n"
        f"Em P igual a 32, o custo puro sobe de {p32['verif_min_txt']} s para {bc32['verif_min_txt']} s. "
        f"Em P igual a 64, salta de {p64['verif_min_txt']} s para {bc64['verif_min_txt']} s "
        f"({dados.fmt_razao(fator_bc64, 1)} vezes mais caro), derrubando o speedup total de "
        f"{p64['s_txt']} para apenas {bc64['s_txt']}.",
        13.8, False, INK, lista=True,
    )
    legenda(s, [
        "MPI_Allreduce: reduz e distribui o sinal de parada em uma única operação coletiva O(log P)",
        "P broadcasts: cada rank difunde seu estado separadamente, multiplicando a latência de rede por P",
    ])

    # 11. Efeito do Hyper-Threading
    s = prs.slides.add_slide(blank)
    chrome(s, "Por que o hyperthreading em P = 64 não amplia o ganho", next_page(), total)
    add_text(
        s, 0.4, 1.38, 12.5, 5.0,
        f"De P igual a 32 para P igual a 64 mantemos os mesmos 4 nós (32 núcleos físicos no total) "
        "e colocamos dois processos por núcleo físico sobre as threads lógicas do Xeon E5520.\n\n"
        f"A média da computação local até diminui levemente, passando de {p32['comp_txt']} s em "
        f"P igual a 32 para {p64['comp_txt']} s em P igual a 64, pois as duas threads aproveitam "
        "algumas bolhas de acesso à memória nas faixas leves.\n\n"
        "Porém, quem governa o tempo de cada iteração nas fases paralelas não é a média, e sim o "
        f"processo mais lento da bacia central: o tempo máximo de computação (comp_max) vai de "
        f"{dados.fmt_tempo(p32['comp_max'])} s em P igual a 32 para {dados.fmt_tempo(p64['comp_max'])} s "
        "em P igual a 64 porque os dois processos da faixa central disputam as mesmas unidades "
        "inteiras e a mesma cache do núcleo físico.\n\n"
        f"Somado ao aumento do MPI_Allreduce com 64 processos ({p32['verif_min_txt']} s para "
        f"{p64['verif_min_txt']} s), o tempo total passa de {p32['tp_txt']} s (S igual a {p32['s_txt']}) "
        f"para {p64['tp_txt']} s (S igual a {p64['s_txt']}), derrubando a eficiência de "
        f"{p32['e_txt']} para {p64['e_txt']}.",
        14.5, False, INK, lista=True,
    )
    legenda(s, [
        "caminho crítico: nas fases paralelas, o ritmo de todas as iterações é ditado pelo rank mais carregado",
        "hyperthreading (HT): compartilha o mesmo núcleo físico entre duas threads, sem duplicar cache nem ALUs",
    ])

    # 12. Fechamento
    s = prs.slides.add_slide(blank)
    chrome(s, "O que levar da análise", next_page(), total)
    add_text(
        s, 0.4, 1.38, 12.5, 5.0,
        "O preenchimento de depressões de Planchon e Darboux se ajusta de forma exata ao modelo "
        f"de fases paralelas: parada guiada pelos dados ({ctx['iteracoes']} iterações), duplo buffer "
        "e equivalência integral demonstrada em todas as execuções.\n\n"
        f"Com fração sequencial medida s igual a {ctx['frac_s_pct']}, o speedup atinge {p32['s_txt']} "
        f"em 32 núcleos físicos (teto de Amdahl {p32['amdahl_txt']}). A diferença para Amdahl é "
        "integralmente explicada pelas medições de fase: espera pelo rank da bacia central, "
        "coletiva de parada e troca de bordas.\n\n"
        f"Separar verif_min de verif_med mostrou que a maior fatia da verificação em múltiplos nós "
        f"é espera pelo mais lento ({p32['espera_txt']} s), enquanto um único MPI_Allreduce custa "
        f"apenas {p32['verif_min_txt']} s em P igual a 32 (frente a {bc32['verif_min_txt']} s com P broadcasts).\n\n"
        f"Em P igual a 64, o hyperthreading não reduz o tempo da faixa crítica e encarece a "
        "sincronização coletiva. Todo o código, scripts Slurm e saídas brutas estão no repositório.",
        14.5, False, INK, lista=True,
    )
    legenda(s, [
        "repositório público: github.com/bengo501/Trabalho4-Computacao-Paralela",
        "referência do algoritmo: O. Planchon e F. Darboux, Catena 46 (2001) 159 a 176",
    ])

    assert page == total, f"paginas {page} != total {total}"
    prs.save(str(SAIDA))
    print(f"Gerado {SAIDA} | slides={len(prs.slides)}")


if __name__ == "__main__":
    build()
