#!/usr/bin/env python3
"""Escolhe N a partir das sondas em calib.txt para manter T1 perto de 45 s
(dentro da janela de 30 a 60 s). Se a ultima sonda ja estiver entre 36 e 54 s,
imprime N e encerra com codigo 0; caso contrario sugere novo N e sai com 1."""

import math
import sys
from pathlib import Path


def main() -> int:
    caminho = Path(sys.argv[1])
    linhas = [ln.split() for ln in caminho.read_text().splitlines() if ln.strip()]
    n_ult, t_ult = int(linhas[-1][0]), float(linhas[-1][1])

    alvo = 45.0
    if 36.0 <= t_ult <= 54.0:
        print(n_ult)
        return 0

    # Em Planchon-Darboux sincrono, celulas ~ N^2 e iteracoes ~ N => T1 ~ N^3.
    fator = (alvo / max(t_ult, 0.05)) ** (1.0 / 3.0)
    fator = max(0.5, min(2.2, fator))
    novo_n = int(round((n_ult * fator) / 64.0)) * 64
    novo_n = max(512, min(8192, novo_n))
    if novo_n == n_ult:
        novo_n += 64 if t_ult < alvo else -64
    print(novo_n)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
