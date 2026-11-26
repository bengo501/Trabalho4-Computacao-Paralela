"""Leitura centralizada de results/runs.csv para relatorio e apresentacao."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CSV_PADRAO = RAIZ / "results" / "runs.csv"

PS_SERIE = (1, 2, 4, 8, 16, 32, 64)
PS_BCAST = (8, 16, 32, 64)


def fmt_tempo(x: float, casas: int = 3) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def fmt_razao(x: float, casas: int = 2) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def fmt_pct(x: float, casas: int = 2) -> str:
    return f"{x * 100.0:.{casas}f}%".replace(".", ",")


def fmt_ms(x: float, casas: int = 2) -> str:
    return f"{x * 1000.0:.{casas}f}".replace(".", ",")


def carregar(caminho: Path = CSV_PADRAO) -> dict:
    if not caminho.exists():
        raise SystemExit(f"Arquivo nao encontrado: {caminho}")

    grupos: dict[tuple[str, str, int], list[dict]] = {}
    assinatura_ref = None

    with caminho.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["verificacao"] != "OK":
                raise SystemExit(f"Execucao invalida em runs.csv: {row}")
            ass = (
                int(row["n"]),
                int(row["iteracoes"]),
                int(row["volume_retido"]),
                int(row["celulas_alagadas"]),
                int(row["soma_cotas"]),
            )
            if assinatura_ref is None:
                assinatura_ref = ass
            elif ass != assinatura_ref:
                raise SystemExit(f"Divergencia de equivalencia: {ass} != {assinatura_ref}")

            chave = (row["versao"], row["coletiva"], int(row["p"]))
            grupos.setdefault(chave, []).append(row)

    if assinatura_ref is None:
        raise SystemExit("runs.csv vazio")

    seq_rows = grupos.get(("sequencial", "nenhuma", 1), [])
    if len(seq_rows) < 1:
        raise SystemExit("Sem linhas sequenciais em runs.csv")

    tempos_seq = [float(r["tempo"]) for r in seq_rows]
    t1 = statistics.median(tempos_seq)
    t1_min, t1_max = min(tempos_seq), max(tempos_seq)
    t_serial = statistics.median(float(r["t_serial"]) for r in seq_rows)
    t_par_seq = statistics.median(float(r["comp_med"]) for r in seq_rows)
    frac_s = statistics.median(float(r["frac_seq"]) for r in seq_rows)

    def amdahl(p: int) -> float:
        return 1.0 / (frac_s + (1.0 - frac_s) / p)

    def resumir_mpi(col: str, p: int) -> dict | None:
        rows = grupos.get(("mpi", col, p))
        if not rows:
            return None
        tps = [float(r["tempo"]) for r in rows]
        tp_med = statistics.median(tps)
        tp_min, tp_max = min(tps), max(tps)
        s_med = t1 / tp_med
        s_min = t1 / tp_max
        s_max = t1 / tp_min
        amd = amdahl(p)
        e_med = s_med / p
        nos = int(rows[0]["nos"])

        comp_med = statistics.median(float(r["comp_med"]) for r in rows)
        comp_min = statistics.median(float(r["comp_min"]) for r in rows)
        comp_max = statistics.median(float(r["comp_max"]) for r in rows)
        verif_med = statistics.median(float(r["verif_med"]) for r in rows)
        verif_min = statistics.median(float(r["verif_min"]) for r in rows)
        verif_max = statistics.median(float(r["verif_max"]) for r in rows)
        espera_med = statistics.median(float(r["espera_med"]) for r in rows)
        # Garante consistencia aditiva exata verif_com + espera = verif_med
        espera_decomp = max(0.0, verif_med - verif_min)
        troca_med = statistics.median(float(r["troca_med"]) for r in rows)
        troca_min = statistics.median(float(r["troca_min"]) for r in rows)
        troca_max = statistics.median(float(r["troca_max"]) for r in rows)
        extra_med = statistics.median(float(r["extra_med"]) for r in rows)

        soma_fases = comp_med + verif_med + troca_med
        return {
            "p": p,
            "nos": nos,
            "reps": len(rows),
            "tp": tp_med,
            "tp_min": tp_min,
            "tp_max": tp_max,
            "tp_txt": fmt_tempo(tp_med),
            "min_txt": fmt_tempo(tp_min),
            "max_txt": fmt_tempo(tp_max),
            "s": s_med,
            "s_min": s_min,
            "s_max": s_max,
            "s_txt": fmt_razao(s_med),
            "amdahl": amd,
            "amdahl_txt": fmt_razao(amd),
            "e": e_med,
            "e_txt": fmt_razao(e_med),
            "comp_med": comp_med,
            "comp_min": comp_min,
            "comp_max": comp_max,
            "verif_med": verif_med,
            "verif_min": verif_min,
            "verif_max": verif_max,
            "espera_med": espera_med,
            "espera_decomp": espera_decomp,
            "troca_med": troca_med,
            "troca_min": troca_min,
            "troca_max": troca_max,
            "extra_med": extra_med,
            "soma_fases": soma_fases,
            "comp_txt": fmt_tempo(comp_med),
            "verif_med_txt": fmt_tempo(verif_med),
            "verif_min_txt": fmt_tempo(verif_min),
            "espera_txt": fmt_tempo(espera_decomp),
            "troca_txt": fmt_tempo(troca_med),
            "extra_txt": fmt_tempo(extra_med),
        }

    serie = [x for p in PS_SERIE if (x := resumir_mpi("allreduce", p)) is not None]
    bcast = [x for p in PS_BCAST if (x := resumir_mpi("bcast", p)) is not None]

    total_execucoes = sum(len(v) for v in grupos.values())

    return {
        "n": assinatura_ref[0],
        "iteracoes": assinatura_ref[1],
        "volume_retido": assinatura_ref[2],
        "celulas_alagadas": assinatura_ref[3],
        "soma_cotas": assinatura_ref[4],
        "reps_seq": len(seq_rows),
        "total_execucoes": total_execucoes,
        "t1": t1,
        "t1_min": t1_min,
        "t1_max": t1_max,
        "t1_txt": fmt_tempo(t1),
        "t1_min_txt": fmt_tempo(t1_min),
        "t1_max_txt": fmt_tempo(t1_max),
        "t_serial": t_serial,
        "t_serial_txt": fmt_tempo(t_serial),
        "t_par_seq": t_par_seq,
        "frac_s": frac_s,
        "frac_s_pct": fmt_pct(frac_s, 2),
        "amdahl_inf": 1.0 / frac_s if frac_s > 0 else float("inf"),
        "amdahl_inf_txt": fmt_razao(1.0 / frac_s, 1) if frac_s > 0 else "-",
        "serie": serie,
        "por_p": {x["p"]: x for x in serie},
        "bcast": bcast,
        "bcast_por_p": {x["p"]: x for x in bcast},
    }
