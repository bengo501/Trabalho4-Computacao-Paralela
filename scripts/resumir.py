#!/usr/bin/env python3
"""Resume results/runs.csv e confere equivalencia de todas as execucoes."""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    caminho = Path(sys.argv[1] if len(sys.argv) > 1 else "results/runs.csv")
    grupos = defaultdict(list)
    ref = None

    with caminho.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert row["verificacao"] == "OK", f"Execucao falhou: {row}"
            assinatura = (
                int(row["n"]),
                int(row["iteracoes"]),
                int(row["volume_retido"]),
                int(row["celulas_alagadas"]),
                int(row["soma_cotas"]),
            )
            if ref is None:
                ref = assinatura
            elif assinatura != ref:
                raise SystemExit(f"Divergencia de equivalencia: {assinatura} != {ref}")
            chave = (row["versao"], row["coletiva"], int(row["p"]), int(row["nos"]))
            grupos[chave].append(row)

    print(f"Equivalencia OK em todas as linhas: n={ref[0]} iteracoes={ref[1]} "
          f"volume_retido={ref[2]} celulas_alagadas={ref[3]}")

    seq_rows = grupos[("sequencial", "nenhuma", 1, 1)]
    t1 = statistics.median(float(r["tempo"]) for r in seq_rows)
    frac_s = statistics.median(float(r["frac_seq"]) for r in seq_rows)
    print(f"Sequencial (N={len(seq_rows)}): T1={t1:.4f}s  frac_seq(s)={frac_s:.6f}\n")

    print(f"{'versao':<10} {'coletiva':<10} {'P':>3} {'nos':>3} {'med(s)':>9} "
          f"{'min':>9} {'max':>9} {'S':>7} {'Amdahl':>7} {'E':>6} "
          f"{'comp':>8} {'ver_med':>8} {'ver_min':>8} {'espera':>8} {'troca':>8}")
    for chave in sorted(grupos.keys()):
        versao, col, p, nos = chave
        rows = grupos[chave]
        tempos = [float(r["tempo"]) for r in rows]
        med = statistics.median(tempos)
        mn, mx = min(tempos), max(tempos)
        s = t1 / med
        amd = 1.0 / (frac_s + (1.0 - frac_s) / p)
        e = s / p
        comp = statistics.median(float(r["comp_med"]) for r in rows)
        vmed = statistics.median(float(r["verif_med"]) for r in rows)
        vmin = statistics.median(float(r["verif_min"]) for r in rows)
        esp  = statistics.median(float(r["espera_med"]) for r in rows)
        trc  = statistics.median(float(r["troca_med"]) for r in rows)
        print(f"{versao:<10} {col:<10} {p:>3d} {nos:>3d} {med:>9.4f} "
              f"{mn:>9.4f} {mx:>9.4f} {s:>7.2f} {amd:>7.2f} {e:>6.3f} "
              f"{comp:>8.4f} {vmed:>8.4f} {vmin:>8.4f} {esp:>8.4f} {trc:>8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
