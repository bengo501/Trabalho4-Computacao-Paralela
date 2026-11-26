"""Gera todas as figuras do relatorio (pagina 2) e da apresentacao."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "relatorio"))
import dados

RESULTS = RAIZ / "results"
FIG_SLIDES = RAIZ / "apresentacao" / "figuras"

NAVY = "#1E3A5F"
AZUL = "#1f77b4"
LARANJA = "#e67e22"
VERDE = "#2ca02c"
VERMELHO = "#c0392b"
ROXO = "#7f5af0"
CINZA = "#6b7280"


def ler_binario_grade(caminho: Path) -> np.ndarray:
    raw = caminho.read_bytes()
    (n,) = struct.unpack("<i", raw[:4])
    arr = np.frombuffer(raw, dtype="<i4", offset=4).reshape((n, n))
    return arr.astype(np.float64) / 1000.0  # converte mm -> metros equivalentes


def gerar_relevo_lagos() -> None:
    z_path = RESULTS / "mapa360_z.bin"
    w_path = RESULTS / "mapa360_w.bin"
    if not (z_path.exists() and w_path.exists()):
        return

    FIG_SLIDES.mkdir(parents=True, exist_ok=True)
    z = ler_binario_grade(z_path)
    w = ler_binario_grade(w_path)
    agua = w - z
    n = z.shape[0]

    ls = LightSource(azdeg=315, altdeg=42)
    relevo_rgb = ls.shade(z, cmap=plt.cm.terrain, vert_exag=2.2, blend_mode="soft")

    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.1), dpi=180)

    # Painel 1: DEM original
    ax = axes[0]
    im0 = ax.imshow(z, cmap="terrain", origin="upper")
    ax.imshow(relevo_rgb, origin="upper", alpha=0.85)
    ax.set_title("1. Relevo original Z (com bacias e crateras)", fontsize=10.5, fontweight="bold", color=NAVY)
    ax.set_xlabel("coluna j")
    ax.set_ylabel("linha i (dividida em faixas 1/P)")
    for frac in (0.25, 0.50, 0.75):
        ax.axhline(n * frac, color="white", linestyle="--", linewidth=0.9, alpha=0.85)
    cb0 = fig.colorbar(im0, ax=ax, fraction=0.046, pad=0.04)
    cb0.set_label("cota (m)", fontsize=8.5)

    # Painel 2: Depressoes preenchidas (W - Z > 0)
    ax = axes[1]
    ax.imshow(relevo_rgb, origin="upper")
    agua_mask = np.ma.masked_where(agua <= 0.001, agua)
    im1 = ax.imshow(agua_mask, cmap="Blues", origin="upper", vmin=0, vmax=max(1.0, np.percentile(agua[agua > 0], 98)))
    # Escolhe linha de corte com bastante agua retida
    linha_corte = int(np.argmax(np.sum(agua > 0.2, axis=1)))
    ax.axhline(linha_corte, color="#ffeb3b", linestyle="-", linewidth=1.5)
    ax.set_title("2. Após Planchon-Darboux: lagos retidos (W > Z)", fontsize=10.5, fontweight="bold", color=NAVY)
    ax.set_xlabel("coluna j (linha amarela = perfil ao lado)")
    ax.set_yticks([])
    cb1 = fig.colorbar(im1, ax=ax, fraction=0.046, pad=0.04)
    cb1.set_label(" lâmina retida W - Z (m)", fontsize=8.5)

    # Painel 3: Corte 1D mostrando o nivelamento na soleira
    ax = axes[2]
    xs = np.arange(n)
    z_perfil = z[linha_corte, :]
    w_perfil = w[linha_corte, :]
    ax.fill_between(xs, 0, z_perfil, color="#bfa588", alpha=0.85, label="terreno Z (rocha)")
    ax.fill_between(xs, z_perfil, w_perfil, where=(w_perfil > z_perfil),
                    color="#2b8cbe", alpha=0.85, interpolate=True, label="água retida (depressão preenchida)")
    ax.plot(xs, z_perfil, color="#5c4033", linewidth=1.1)
    ax.plot(xs, w_perfil, color="#08519c", linewidth=1.3, linestyle="--", label="superfície final W")
    ax.set_title(f"3. Perfil (i = {linha_corte}): soleira de escoamento", fontsize=9.6, fontweight="bold", color=NAVY)
    ax.set_xlabel("coluna j")
    ax.set_ylabel("altitude (m)")
    ax.set_ylim(max(0.0, float(z_perfil.min()) - 2.0), float(w_perfil.max()) + 3.0)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower center", fontsize=8, framealpha=0.92)

    fig.tight_layout()
    fig.savefig(FIG_SLIDES / "relevo_lagos.png", dpi=180)
    plt.close(fig)


def gerar_diagrama_fases() -> None:
    FIG_SLIDES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.2, 4.3), dpi=180)
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    ranks = [
        ("Rank 0 (costa norte)", 3.35, 1.45),
        ("Rank 1 (bacia central)", 2.40, 2.35),
        ("Rank 2 (bacia central)", 1.45, 2.50),
        ("Rank 3 (costa sul)", 0.50, 1.55),
    ]

    ax.text(0.15, 4.22, "Uma iteração do modelo de fases paralelas (repetida até mudou_global == 0)",
            fontsize=12, fontweight="bold", color=NAVY)

    x_bar = 4.35  # fim do mais lento na fase 1
    w_verif = 1.45
    w_troca = 1.35

    for nome, y, dur_comp in ranks:
        ax.text(0.12, y + 0.25, nome, fontsize=9.5, fontweight="bold", color="#1f2937", va="center")
        x0 = 1.85
        # Fase 1: computacao local
        ax.add_patch(FancyBboxPatch((x0, y), dur_comp, 0.52, boxstyle="round,pad=0.02",
                                    facecolor="#2b6cb0", edgecolor="white", linewidth=1))
        ax.text(x0 + dur_comp / 2, y + 0.26, "1. Computação\nlocal", color="white",
                fontsize=8, ha="center", va="center", fontweight="bold")

        # Espera pelo mais lento antes de fechar o Allreduce
        espera = x_bar - (x0 + dur_comp)
        if espera > 0.05:
            ax.add_patch(Rectangle((x0 + dur_comp, y + 0.04), espera, 0.44,
                                   facecolor="#fbd38d", edgecolor="#dd6b20", linestyle="--", linewidth=0.9))
            ax.text(x0 + dur_comp + espera / 2, y + 0.26, "espera pelo\nmais lento",
                    color="#7b341e", fontsize=7.5, ha="center", va="center")

        # Fase 2: verificacao coletiva
        ax.add_patch(FancyBboxPatch((x_bar, y), w_verif, 0.52, boxstyle="round,pad=0.02",
                                    facecolor="#dd6b20", edgecolor="white", linewidth=1))
        ax.text(x_bar + w_verif / 2, y + 0.26, "2. MPI_Allreduce\n(mudou?)", color="white",
                fontsize=8, ha="center", va="center", fontweight="bold")

        # Fase 3: troca de bordas
        x_tr = x_bar + w_verif + 0.18
        ax.add_patch(FancyBboxPatch((x_tr, y), w_troca, 0.52, boxstyle="round,pad=0.02",
                                    facecolor="#2f855a", edgecolor="white", linewidth=1))
        ax.text(x_tr + w_troca / 2, y + 0.26, "3. Halo Isend/\nIrecv vizinhos", color="white",
                fontsize=8, ha="center", va="center", fontweight="bold")

    # Setas verticais simbolizando troca entre vizinhos na Fase 3
    x_seta = x_bar + w_verif + 0.18 + w_troca + 0.30
    for y_alto, y_baixo in [(3.45, 2.82), (2.50, 1.87), (1.55, 0.92)]:
        ax.add_patch(FancyArrowPatch((x_seta, y_alto), (x_seta, y_baixo),
                                     arrowstyle="<->", mutation_scale=13, color="#2f855a", linewidth=1.6))
    ax.text(x_seta + 0.22, 2.20, "Troca de 1 linha\nde borda (N ints)\nentre rank r e r±1\nem full-duplex",
            fontsize=8.8, color="#1f2937", va="center")

    ax.axvline(x_bar, color="#c0392b", linestyle=":", linewidth=1.2, ymin=0.08, ymax=0.88)
    ax.text(x_bar, 0.12, "Rank 2 (mais lento) chega aqui:\nseu tempo no Allreduce = verif_min",
            fontsize=8.2, color="#c0392b", ha="center")

    fig.tight_layout()
    fig.savefig(FIG_SLIDES / "modelo_fases.png", dpi=180)
    plt.close(fig)


def gerar_topologia_nos() -> None:
    FIG_SLIDES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.0, 3.3), dpi=180)
    ax.set_xlim(0, 11.2)
    ax.set_ylim(0, 3.4)
    ax.axis("off")

    ax.text(0.15, 3.05, "Alocação exclusiva mínima no cluster Atlântica (Xeon E5520: 8 núcleos físicos e 16 threads por nó)",
            fontsize=11, fontweight="bold", color=NAVY)

    caixas = [
        (0.15, "P = 1, 2, 4, 8", "1 nó exclusivo\n(atlantica07)", "Até 8 processos:\n1 por núcleo físico\n(--cpu-bind=cores)", "#e6f0fa", NAVY),
        (2.90, "P = 16", "2 nós exclusivos\n(atlantica07 e 08)", "8 processos por nó:\n16 núcleos físicos\nrede Gigabit entre 2 nós", "#e6f4ea", "#1e6f43"),
        (5.65, "P = 32", "4 nós exclusivos\n(atlantica07 a 10)", "8 processos por nó:\n32 núcleos físicos\n1 por núcleo físico", "#fef6e6", "#9c5700"),
        (8.40, "P = 64 (HT)", "4 nós exclusivos\n(atlantica07 a 10)", "16 processos por nó:\n2 threads por núcleo\n(--cpu-bind=threads)", "#fdecea", "#9b1c1c"),
    ]

    for x, tit, sub, desc, bg, cor in caixas:
        ax.add_patch(FancyBboxPatch((x, 0.25), 2.55, 2.48, boxstyle="round,pad=0.05",
                                    facecolor=bg, edgecolor=cor, linewidth=1.5))
        ax.text(x + 1.275, 2.42, tit, fontsize=11.5, fontweight="bold", color=cor, ha="center")
        ax.text(x + 1.275, 1.85, sub, fontsize=9.3, fontweight="bold", color="#1f2937", ha="center", va="center")
        ax.text(x + 1.275, 0.90, desc, fontsize=8.6, color="#374151", ha="center", va="center")

    fig.tight_layout()
    fig.savefig(FIG_SLIDES / "topologia_nos.png", dpi=180)
    plt.close(fig)


def gerar_graficos_resultados(ctx: dict) -> None:
    FIG_SLIDES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    serie = ctx["serie"]
    ps = [x["p"] for x in serie]
    s_med = [x["s"] for x in serie]
    s_min = [x["s_min"] for x in serie]
    s_max = [x["s_max"] for x in serie]
    amd = [x["amdahl"] for x in serie]
    eff = [x["e"] for x in serie]

    # 1. Speed-up + Eficiencia (Relatorio pagina 2 e Slides)
    for destino, tam in [(RESULTS / "fig_speedup.png", (8.6, 3.35)),
                         (FIG_SLIDES / "speedup_slides.png", (10.2, 4.1))]:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=tam, dpi=200)

        p_grid = np.linspace(1, 64, 200)
        s_f = ctx["frac_s"]
        amd_grid = 1.0 / (s_f + (1.0 - s_f) / p_grid)

        ax1.plot(ps, ps, "--", color="#374151", linewidth=1.2, label="Ideal (S = P)")
        ax1.plot(p_grid, amd_grid, "-.", color=LARANJA, linewidth=1.6,
                 label=f"Teto de Amdahl (s = {ctx['frac_s_pct']})")
        ax1.plot(ps, s_med, "o-", color=AZUL, linewidth=2.0, markersize=5.5,
                 label="Speed-up medido (mediana)")
        ax1.fill_between(ps, s_min, s_max, color=AZUL, alpha=0.18, label="Faixa mín–máx (10 reps)")
        ax1.axvline(32, color=VERMELHO, linestyle=":", linewidth=1.1)
        ax1.text(33.2, max(ps) * 0.55, "HT\n(P=64)", color=VERMELHO, fontsize=7.8)

        for x_p, y_s in zip(ps, s_med):
            if x_p in (4, 8, 16, 32, 64):
                desl = 2.2 if x_p != 64 else -4.8
                ax1.annotate(dados.fmt_razao(y_s, 1), (x_p, y_s),
                             textcoords="offset points", xytext=(0, 6 if desl > 0 else -12),
                             ha="center", fontsize=7.8, fontweight="bold", color=NAVY)

        ax1.set_title("Speed-up (P = 1 a 64)", fontsize=10, fontweight="bold", color=NAVY)
        ax1.set_xlabel("Processos MPI (P)", fontsize=8.8)
        ax1.set_ylabel("Speed-up S = T1 / Tp", fontsize=8.8)
        ax1.set_xticks([1, 8, 16, 32, 64])
        ax1.set_xlim(0, 66)
        ax1.set_ylim(0, 66)
        ax1.grid(True, alpha=0.28)
        ax1.legend(loc="upper left", fontsize=7.5, framealpha=0.92)

        ax2.axhline(1.0, color="#374151", linestyle="--", linewidth=1.1, label="Ideal (E = 1,00)")
        amd_eff = [a / p for a, p in zip(amd, ps)]
        ax2.plot(ps, amd_eff, "-.", color=LARANJA, linewidth=1.4, label="Eficiência Amdahl")
        ax2.plot(ps, eff, "s-", color=VERDE, linewidth=2.0, markersize=5.5, label="Eficiência medida (S / P)")
        ax2.axvline(8, color=CINZA, linestyle=":", linewidth=0.9)
        ax2.axvline(16, color=CINZA, linestyle=":", linewidth=0.9)
        ax2.axvline(32, color=VERMELHO, linestyle=":", linewidth=1.1)
        ax2.text(4.2, 0.08, "1 nó", fontsize=7.5, color=CINZA, ha="center")
        ax2.text(12.0, 0.08, "2 nós", fontsize=7.5, color=CINZA, ha="center")
        ax2.text(24.0, 0.08, "4 nós", fontsize=7.5, color=CINZA, ha="center")
        ax2.text(48.0, 0.08, "4 nós (HT)", fontsize=7.5, color=VERMELHO, ha="center")

        for x_p, y_e in zip(ps, eff):
            if x_p in (1, 8, 16, 32, 64):
                ax2.annotate(dados.fmt_razao(y_e, 2), (x_p, y_e),
                             textcoords="offset points", xytext=(0, 6),
                             ha="center", fontsize=7.8, fontweight="bold", color="#1e6f43")

        ax2.set_title("Eficiência paralela E = S / P", fontsize=10, fontweight="bold", color=NAVY)
        ax2.set_xlabel("Processos MPI (P)", fontsize=8.8)
        ax2.set_ylabel("Eficiência E", fontsize=8.8)
        ax2.set_xticks([1, 8, 16, 32, 64])
        ax2.set_xlim(0, 66)
        ax2.set_ylim(0, 1.12)
        ax2.grid(True, alpha=0.28)
        ax2.legend(loc="upper right", fontsize=7.5, framealpha=0.92)

        fig.tight_layout()
        fig.savefig(destino, dpi=200)
        plt.close(fig)

    # 2. Barras empilhadas da divisao do tempo por fase (Secao 5.2)
    rotulos = [str(x["p"]) for x in serie]
    comp = np.array([x["comp_med"] for x in serie])
    vmin = np.array([x["verif_min"] for x in serie])
    vesp = np.array([x["espera_decomp"] for x in serie])
    troc = np.array([x["troca_med"] for x in serie])

    for destino, tam in [(RESULTS / "fig_fases.png", (8.6, 3.35)),
                         (FIG_SLIDES / "fases_slides.png", (10.2, 4.1))]:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=tam, dpi=200)
        x_idx = np.arange(len(serie))
        larg = 0.58

        ax1.bar(x_idx, comp, larg, label="Computação local (média)", color="#2b6cb0")
        ax1.bar(x_idx, vmin, larg, bottom=comp, label="Verificação: coletiva (mín)", color="#c0392b")
        ax1.bar(x_idx, vesp, larg, bottom=comp + vmin, label="Verificação: espera (méd − mín)", color="#f6ad55")
        ax1.bar(x_idx, troc, larg, bottom=comp + vmin + vesp, label="Troca de bordas (média)", color="#2f855a")
        ax1.set_xticks(x_idx)
        ax1.set_xticklabels(rotulos)
        ax1.set_xlabel("Processos MPI (P)", fontsize=8.8)
        ax1.set_ylabel("Tempo médio das fases (s)", fontsize=8.8)
        ax1.set_title("Tempo por fase: série completa (P = 1 a 64)", fontsize=9.8, fontweight="bold", color=NAVY)
        ax1.grid(True, axis="y", alpha=0.28)
        ax1.legend(loc="upper right", fontsize=7.1, framealpha=0.92)

        # Painel direito: zoom em P >= 8 para ver claramente comunicacao vs espera
        mask = [i for i, item in enumerate(serie) if item["p"] >= 8]
        xz = np.arange(len(mask))
        rz = [str(serie[i]["p"]) for i in mask]
        cz, vmz, vez, tz = comp[mask], vmin[mask], vesp[mask], troc[mask]

        ax2.bar(xz, cz, 0.52, label="Computação local", color="#2b6cb0")
        ax2.bar(xz, vmz, 0.52, bottom=cz, label="Verif.: comunicação (mín)", color="#c0392b")
        ax2.bar(xz, vez, 0.52, bottom=cz + vmz, label="Verif.: espera pelo mais lento", color="#f6ad55")
        ax2.bar(xz, tz, 0.52, bottom=cz + vmz + vez, label="Troca de bordas", color="#2f855a")
        tot_z = cz + vmz + vez + tz
        for k, tot_val in enumerate(tot_z):
            ax2.text(k, tot_val + max(tot_z) * 0.02, f"{dados.fmt_tempo(tot_val, 2)}s",
                     ha="center", fontsize=7.6, fontweight="bold", color=NAVY)

        ax2.set_xticks(xz)
        ax2.set_xticklabels(rz)
        ax2.set_ylim(0, max(tot_z) * 1.16)
        ax2.set_xlabel("Processos MPI (P)", fontsize=8.8)
        ax2.set_ylabel("Tempo médio das fases (s)", fontsize=8.8)
        ax2.set_title("Zoom (P = 8 a 64): comunicação vs espera", fontsize=9.8, fontweight="bold", color=NAVY)
        ax2.grid(True, axis="y", alpha=0.28)

        fig.tight_layout()
        fig.savefig(destino, dpi=200)
        plt.close(fig)

    # 3. Comparacao MPI_Allreduce vs P * MPI_Bcast (Slides)
    if ctx["bcast"]:
        fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=180)
        ps_b = [x["p"] for x in ctx["bcast"]]
        idx = np.arange(len(ps_b))
        w = 0.35
        ar_min = [ctx["por_p"][p]["verif_min"] for p in ps_b]
        bc_min = [ctx["bcast_por_p"][p]["verif_min"] for p in ps_b]

        b1 = ax.bar(idx - w / 2, ar_min, w, label="1 × MPI_Allreduce — O(log P)", color=AZUL)
        b2 = ax.bar(idx + w / 2, bc_min, w, label="P × MPI_Bcast — O(P log P)", color=VERMELHO)

        for rect in b1:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2, h + 0.15,
                    f"{dados.fmt_tempo(h, 2)}s", ha="center", fontsize=8, color=NAVY, fontweight="bold")
        for rect in b2:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2, h + 0.15,
                    f"{dados.fmt_tempo(h, 2)}s", ha="center", fontsize=8, color=VERMELHO, fontweight="bold")

        ax.set_xticks(idx)
        ax.set_xticklabels([f"P = {p}" for p in ps_b])
        ax.set_ylabel("Menor tempo na verificação verif_min (s)")
        ax.set_title("Custo puro da coletiva de parada: MPI_Allreduce contra P broadcasts",
                     fontsize=10.2, fontweight="bold", color=NAVY)
        ax.set_ylim(0, max(bc_min) * 1.18)
        ax.grid(True, axis="y", alpha=0.28)
        ax.legend(loc="upper left", fontsize=8.8)
        fig.tight_layout()
        fig.savefig(FIG_SLIDES / "allreduce_vs_bcast.png", dpi=180)
        plt.close(fig)


def main() -> None:
    gerar_relevo_lagos()
    gerar_diagrama_fases()
    gerar_topologia_nos()
    if (RESULTS / "runs.csv").exists():
        try:
            ctx = dados.carregar()
            if ctx["serie"]:
                gerar_graficos_resultados(ctx)
        except SystemExit:
            pass
    print("Figuras geradas com sucesso.")


if __name__ == "__main__":
    main()
