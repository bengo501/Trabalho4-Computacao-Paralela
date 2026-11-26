"""Gera relatorio/relatorio.pdf no formato do TP4 exigido na Secao 6:
  - Pagina 1: texto da analise em duas colunas, fonte 10, com cabecalho e link
    do repositorio publico.
  - Pagina 2: tabelas (mediana, min e max de 10 repeticoes) e graficos
    (speed-up com 3 curvas + eficiencia; barras empilhadas por fase).
  - Paginas seguintes: codigo-fonte completo com numeros de linha."""

from __future__ import annotations

import sys
from pathlib import Path

from fpdf import FPDF

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "relatorio"))
import dados
import gerar_graficos

PDF_SAIDA = RAIZ / "relatorio" / "relatorio.pdf"
SRC_DIR = RAIZ / "src"
RES_DIR = RAIZ / "results"

FONT_REG = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_ITAL = r"C:\Windows\Fonts\ariali.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"

REPO_URL = "github.com/bengo501/Trabalho4-Computacao-Paralela"


class RelatorioTP4(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4", unit="mm")
        self.add_font("Arial", "", FONT_REG)
        self.add_font("Arial", "B", FONT_BOLD)
        self.add_font("Arial", "I", FONT_ITAL)
        self.add_font("Consolas", "", FONT_MONO)
        self.set_auto_page_break(False)
        self.set_margins(14, 10, 14)
        self.col_w = 88.0
        self.gap = 6.0
        self.left = 14.0
        self.limit = 286.0
        self.col = 0

    def cabecalho(self, subtitulo: str = "") -> None:
        self.set_font("Arial", "B", 11)
        self.set_xy(self.left, 9.0)
        tit = "Trabalho 4: Preenchimento de depressões em relevo (Planchon-Darboux) em fases paralelas com MPI"
        if subtitulo:
            tit = f"Trabalho 4: Fases paralelas com MPI  ·  {subtitulo}"
        self.cell(182, 4.6, tit, align="L")
        self.set_font("Arial", "", 8.8)
        self.set_xy(self.left, 13.8)
        self.cell(
            182, 4.0,
            f"Aluno: Bernardo Klein Heitz   |   Repositório: https://{REPO_URL}",
            align="L",
        )
        self.set_draw_color(30, 58, 95)
        self.set_line_width(0.3)
        self.line(self.left, 18.4, 210 - self.left, 18.4)

    def iniciar_coluna(self, col: int, y: float = 20.2) -> None:
        self.col = col
        self.set_xy(self.left + col * (self.col_w + self.gap), y)

    def x_col(self) -> float:
        return self.left + self.col * (self.col_w + self.gap)

    def p(self, texto: str, size: float = 10.0, estilo: str = "", h: float = 3.92) -> None:
        self.set_font("Arial", estilo, size)
        self.set_x(self.x_col())
        self.multi_cell(self.col_w, h, texto)
        self.ln(0.8)
        if self.get_y() > self.limit:
            raise SystemExit(f"Texto estourou a coluna {self.col} na pagina {self.page} (y={self.get_y():.1f})")

    def secao(self, titulo: str) -> None:
        self.ln(0.6)
        self.set_font("Arial", "B", 10.0)
        self.set_text_color(30, 58, 95)
        self.set_x(self.x_col())
        self.multi_cell(self.col_w, 4.1, titulo)
        self.set_text_color(0, 0, 0)
        self.ln(0.3)

    def tabela_larga(self, x: float, headers: list[str], rows: list[list[str]],
                     widths: list[float], font_size: float = 7.8, row_h: float = 3.85) -> None:
        self.set_x(x)
        self.set_fill_color(30, 58, 95)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(190, 198, 210)
        self.set_line_width(0.2)
        self.set_font("Arial", "B", font_size)
        for w, h_txt in zip(widths, headers):
            self.cell(w, row_h + 0.4, h_txt, border=1, align="C", fill=True)
        self.ln(row_h + 0.4)

        self.set_text_color(20, 25, 35)
        for idx, r in enumerate(rows):
            self.set_x(x)
            fill = (idx % 2 == 1)
            if fill:
                self.set_fill_color(238, 242, 247)
            for c_i, (w, val) in enumerate(zip(widths, r)):
                self.set_font("Arial", "B" if c_i == 0 else "", font_size)
                self.cell(w, row_h, val, border=1, align="C", fill=fill)
            self.ln(row_h)


def pagina_texto(pdf: RelatorioTP4, ctx: dict) -> float:
    pdf.add_page()
    pdf.cabecalho()

    p1 = ctx["por_p"][1]
    p8 = ctx["por_p"][8]
    p16 = ctx["por_p"][16]
    p32 = ctx["por_p"][32]
    p64 = ctx["por_p"][64]
    bc64 = ctx["bcast_por_p"][64]
    bc32 = ctx["bcast_por_p"][32]
    fator_bcast64 = bc64["verif_min"] / max(p64["verif_min"], 1e-9)

    pdf.iniciar_coluna(0, 20.0)
    pdf.secao("1. Problema e modelagem em fases paralelas")
    pdf.p(
        "Resolvemos o preenchimento de depressões em Modelos Digitais de Elevação (DEM) "
        "pelo algoritmo de Planchon e Darboux (2001). Dada uma grade N×N de altitudes Z, "
        "inunda-se o interior com cota infinita mantendo W = Z nas bordas abertas do mapa "
        "(relevo.c:153-176). A cada passo, toda célula com W > Z baixa para max(Z, menor W "
        "dos 8 vizinhos) até estabilizar na soleira de escoamento (relevo.c:178-227)."
    )
    pdf.p(
        "Na versão MPI (fases_mpi.c), o rank 0 gera Z e distribui faixas contíguas de N/P "
        "linhas via MPI_Scatterv (linhas 116-117). Cada processo aloca duas linhas fantasmas "
        "(halo superior e inferior) e repete três fases sincronizadas (linhas 129-162): "
        "(1) computação local na faixa 1/P com duplo buffer, o que torna a atualização síncrona "
        "e independente de P; (2) verificação coletiva combinando mudou_local por um único "
        "MPI_Allreduce (MPI_LOR), encerrando todos os ranks na mesma iteração quando "
        "mudou_global == 0; (3) troca de bordas em full-duplex com rank-1 e rank+1 por "
        "MPI_Irecv/MPI_Isend e MPI_Waitall (linhas 25-39, MPI_PROC_NULL nas extremidades)."
    )
    pdf.p(
        f"Com N = {ctx['n']} (28×64, divisível por todos os P), todas as {ctx['total_execucoes']} "
        f"execuções convergiram em exatas {ctx['iteracoes']} iterações, com {ctx['celulas_alagadas']} "
        f"células alagadas e volume retido igual a {ctx['volume_retido']}, idênticos ao sequencial."
    )

    pdf.secao("2. Ambiente e metodologia")
    pdf.p(
        "Medições no cluster Atlântica em nós exclusivos Xeon E5520 (2 soquetes × 4 núcleos "
        "físicos, 16 threads por nó), respeitando o mínimo de nós para 1 processo por núcleo "
        "físico: 1 nó (atlantica07) para o sequencial e P = 1, 2, 4, 8; 2 nós (07-08) para "
        "P = 16; e 4 nós (07-10, 32 núcleos físicos / 64 threads) para P = 32 (--cpu-bind=cores) "
        "e P = 64 (--cpu-bind=threads, HT)."
    )
    pdf.p(
        "Os binários compilam o mesmo relevo.o com gcc/mpicc -O3 -std=c11 (Open MPI 4.1.1). "
        f"O sequencial não liga MPI: T1 (mediana de 10 repetições) é {ctx['t1_txt']} s "
        f"(mín. {ctx['t1_min_txt']}, máx. {ctx['t1_max_txt']} s), e a etapa serial de geração "
        f"do DEM leva {ctx['t_serial_txt']} s, resultando na fração sequencial medida "
        f"s = {ctx['frac_s_pct']} (teto assintótico 1/s = {ctx['amdahl_inf_txt']})."
    )

    y_col0 = pdf.get_y()
    pdf.iniciar_coluna(1, 20.0)
    pdf.secao("3. Verificação, troca de bordas e espera")
    pdf.p(
        "A Tabela 2 e a Figura 2 decompõem o tempo das fases. Como células que já atingiram "
        "W == Z não avaliam os 8 vizinhos (relevo.c:207), as faixas costeiras secam cedo e "
        "terminam a Fase 1 antes das faixas centrais (que contêm a bacia encaixada). Assim, "
        f"em P = 32 a computação varia de {dados.fmt_tempo(p32['comp_min'])} s a "
        f"{dados.fmt_tempo(p32['comp_max'])} s (média {p32['comp_txt']} s). O rank mais lento "
        "entra por último no MPI_Allreduce e quase não espera: o menor tempo de verificação "
        f"(verif_min = {p32['verif_min_txt']} s em P = 32; {p64['verif_min_txt']} s em P = 64) "
        "mede o custo puro da coletiva, enquanto a diferença verif_med - verif_min "
        f"({p32['espera_txt']} s em P = 32, ou {dados.fmt_pct(p32['espera_decomp']/p32['tp'], 1)} "
        "de Tp) é a espera média pelo processo mais lento."
    )
    pdf.p(
        "Na troca de bordas (1792 inteiros = 7,0 KB por vizinho em cada uma das "
        f"{ctx['iteracoes']} iterações), a média sobe de {p8['troca_txt']} s em 1 nó (P = 8) "
        f"para {p16['troca_txt']} s (2 nós) e {p32['troca_txt']} s (4 nós). Na verificação, "
        "adotamos um único MPI_Allreduce de complexidade O(log P). Medindo a alternativa de P "
        "chamadas MPI_Bcast (colunas finais da Tabela 2, O(P log P)), o custo puro verif_min "
        f"saltou para {bc32['verif_min_txt']} s em P = 32 e {bc64['verif_min_txt']} s em P = 64 "
        f"({dados.fmt_razao(fator_bcast64, 1)}× mais caro, derrubando S de {p64['s_txt']} para {bc64['s_txt']})."
    )

    pdf.secao("4. Speed-up, eficiência, HT e teto de Amdahl")
    pdf.p(
        f"Na Tabela 1 e Figura 1, P = 1 obtém Tp = {p1['tp_txt']} s (S = {p1['s_txt']}, "
        f"E = {p1['e_txt']}). Em 1 nó, 8 processos saturam o barramento de memória para os "
        f"três vetores da grade (~36,7 MB), limitando P = 8 a S = {p8['s_txt']} (E = {p8['e_txt']}). "
        f"Ao distribuir em 2 e 4 nós, as fatias cabem nas caches L3 somadas e comp_med cai 2,66× "
        f"(P = 16: S = {p16['s_txt']}, E = {p16['e_txt']}) e 2,89× (P = 32: S = {p32['s_txt']}, "
        f"E = {p32['e_txt']}), contra o teto de Amdahl de {p32['amdahl_txt']}. "
        "O afastamento entre a curva medida e Amdahl não vem de código serial oculto, e sim de "
        "três parcelas medidas: o desbalanceamento topográfico entre faixas (comp_max supera "
        f"comp_med em {dados.fmt_tempo(p32['comp_max'] - p32['comp_med'])} s em P = 32, gerando "
        f"{p32['espera_txt']} s de espera), a comunicação entre nós ({p32['verif_min_txt']} s de "
        f"Allreduce + {p32['troca_txt']} s de halo) e o Scatterv/Reduce ({p32['extra_txt']} s)."
    )
    pdf.p(
        f"Ao ativar o Hyper-Threading em P = 64 (teto de Amdahl {p64['amdahl_txt']}), S vai a "
        f"{p64['s_txt']} (E = {p64['e_txt']}): duas threads dividem o mesmo núcleo físico na "
        f"faixa central crítica (comp_max passa de {dados.fmt_tempo(p32['comp_max'])} s para "
        f"{dados.fmt_tempo(p64['comp_max'])} s) enquanto o custo do Allreduce sobe para "
        f"{p64['verif_min_txt']} s, anulando o ganho médio da segunda thread."
    )

    pdf.secao("5. Uso de IA e referência")
    pdf.p(
        "Código C/MPI, scripts Slurm e texto redigidos com apoio do Cursor; medições obtidas "
        "integralmente no Atlântica. Ref.: O. Planchon, F. Darboux, Catena 46 (2001) 159-176.",
        size=9.2, h=3.65,
    )
    return max(y_col0, pdf.get_y())


def pagina_tabelas_graficos(pdf: RelatorioTP4, ctx: dict) -> float:
    pdf.add_page()
    pdf.cabecalho("Tabelas e Gráficos")
    pdf.set_y(20.0)

    # Tabela 1: Speed-up, Amdahl e Eficiencia
    pdf.set_font("Arial", "B", 8.8)
    pdf.set_text_color(30, 58, 95)
    pdf.set_x(pdf.left)
    pdf.cell(
        182, 4.2,
        f"Tabela 1. Tempo total (10 repetições), speed-up, teto de Amdahl (s = {ctx['frac_s_pct']}) "
        f"e eficiência. T1 sequencial = {ctx['t1_txt']} s ({ctx['t1_min_txt']}–{ctx['t1_max_txt']} s).",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)

    rows_t1 = []
    for item in ctx["serie"]:
        rows_t1.append([
            str(item["p"]),
            str(item["nos"]),
            item["tp_txt"],
            item["min_txt"],
            item["max_txt"],
            item["s_txt"],
            item["amdahl_txt"],
            item["e_txt"],
        ])
    pdf.tabela_larga(
        pdf.left,
        ["P", "Nós", "Mediana (s)", "Mínimo (s)", "Máximo (s)", "Speed-up S", "Teto Amdahl", "Eficiência E"],
        rows_t1,
        [14, 14, 25, 25, 25, 26, 27, 26],
        font_size=7.8,
        row_h=3.65,
    )

    pdf.ln(1.8)
    # Tabela 2: Divisao por fase + Tabela 3 compacta ao lado ou logo abaixo
    pdf.set_font("Arial", "B", 8.8)
    pdf.set_text_color(30, 58, 95)
    pdf.set_x(pdf.left)
    pdf.cell(
        182, 4.2,
        "Tabela 2. Divisão do tempo por fase em segundos (medianas de 10 repetições) e comparação MPI_Allreduce vs P × MPI_Bcast.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)

    rows_t2 = []
    for item in ctx["serie"]:
        p = item["p"]
        bc_txt = ctx["bcast_por_p"][p]["verif_min_txt"] if p in ctx["bcast_por_p"] else "—"
        bc_s = ctx["bcast_por_p"][p]["s_txt"] if p in ctx["bcast_por_p"] else "—"
        rows_t2.append([
            str(p),
            item["comp_txt"],
            item["verif_med_txt"],
            item["verif_min_txt"],
            item["espera_txt"],
            item["troca_txt"],
            item["extra_txt"],
            bc_txt,
            bc_s,
        ])
    pdf.tabela_larga(
        pdf.left,
        ["P", "Comp. méd", "Verif. méd", "Verif. mín", "Espera méd", "Troca méd", "Prep+Red", "Bcast mín", "S (Bcast)"],
        rows_t2,
        [12, 21, 21, 21, 22, 21, 20, 22, 22],
        font_size=7.5,
        row_h=3.60,
    )

    pdf.ln(2.2)
    # Figura 1: Speed-up e Eficiencia
    y_fig1 = pdf.get_y()
    pdf.image(str(RES_DIR / "fig_speedup.png"), x=pdf.left, y=y_fig1, w=182)
    pdf.set_y(y_fig1 + 71.5)
    pdf.set_font("Arial", "I", 8.0)
    pdf.set_x(pdf.left)
    pdf.multi_cell(
        182, 3.5,
        "Figura 1. Esquerda: speed-up medido contra a reta ideal (S = P) e o teto de Amdahl calculado com a fração "
        f"sequencial s = {ctx['frac_s_pct']} medida na versão sequencial. Direita: eficiência paralela E = S/P por número de nós.",
    )

    pdf.ln(1.5)
    # Figura 2: Barras empilhadas por fase
    y_fig2 = pdf.get_y()
    pdf.image(str(RES_DIR / "fig_fases.png"), x=pdf.left, y=y_fig2, w=182)
    pdf.set_y(y_fig2 + 71.5)
    pdf.set_font("Arial", "I", 8.0)
    pdf.set_x(pdf.left)
    pdf.multi_cell(
        182, 3.5,
        "Figura 2. Divisão média do tempo entre processos por fase (computação local, verificação separada em custo da "
        "coletiva verif_min e espera pelo mais lento, e troca de bordas). À direita, ampliação para P = 8 a 64.",
    )

    y_fim = pdf.get_y()
    if y_fim > 289.0:
        raise SystemExit(f"Pagina 2 estourou o limite A4 (y={y_fim:.1f})")
    return y_fim


def paginas_codigo(pdf: RelatorioTP4) -> None:
    pdf.set_auto_page_break(True, margin=12)
    arquivos = [
        ("fases_mpi.c", "Implementação paralela MPI no modelo de fases paralelas"),
        ("sequencial.c", "Versão sequencial de referência e medição da fração sequencial s"),
        ("relevo.c", "Geração do relevo e núcleo numérico de Planchon-Darboux"),
        ("relevo.h", " Estruturas e contratos compartilhados"),
    ]
    for nome, desc in arquivos:
        linhas = (SRC_DIR / nome).read_text(encoding="utf-8").splitlines()
        pdf.add_page()
        pdf.set_font("Arial", "B", 10.5)
        pdf.set_text_color(30, 58, 95)
        pdf.set_x(14)
        pdf.cell(0, 5.5, f"{nome}  ·  {desc.strip()}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1.0)
        for num, ln in enumerate(linhas, 1):
            txt = f"{num:4d}  {ln.rstrip()}"
            pdf.set_font("Consolas", "", 7.4)
            if pdf.get_string_width(txt) > pdf.epw:
                pdf.set_font("Consolas", "", 6.2)
            pdf.set_x(14)
            pdf.cell(0, 3.25, txt, new_x="LMARGIN", new_y="NEXT")


def main() -> None:
    gerar_graficos.main()
    ctx = dados.carregar()
    pdf = RelatorioTP4()
    y1 = pagina_texto(pdf, ctx)
    y2 = pagina_tabelas_graficos(pdf, ctx)
    paginas_codigo(pdf)
    pdf.output(str(PDF_SAIDA))
    print(f"Gerado {PDF_SAIDA} | paginas={pdf.page} | p1_y={y1:.1f} | p2_y={y2:.1f}")


if __name__ == "__main__":
    main()
