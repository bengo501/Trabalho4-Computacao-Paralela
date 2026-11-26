#!/bin/bash
#SBATCH -J t4fases
#SBATCH -N 4
#SBATCH --nodelist=atlantica[07-10]
#SBATCH --exclusive
#SBATCH -t 02:30:00
#SBATCH -o results/slurm-%j.out
# Campanha oficial do T4 no cluster Atlantica:
#   - 1 no exclusivo (atlantica07) para sequencial e P = 1, 2, 4, 8
#   - 2 nos exclusivos (atlantica[07-08]) para P = 16
#   - 4 nos exclusivos (atlantica[07-10]) para P = 32 e P = 64 (HT)
# Tambem mede a verificacao por P broadcasts (--bcast) em P = 8, 16, 32 e 64
# para comparar diretamente contra MPI_Allreduce.

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"

export PATH=/LADAPPs/OpenMPI/openmpi-4.1.1/bin:$PATH
export LD_LIBRARY_PATH=/LADAPPs/OpenMPI/openmpi-4.1.1/lib:${LD_LIBRARY_PATH:-}
unset OMPI_MCA_mpi_yield_when_idle || true

OUT=${OUTDIR:-results}
mkdir -p "${OUT}/raw" bin
make clean && make
./bin/confere > "${OUT}/confere.txt"

echo "$SLURM_JOB_NODELIST" | tee "${OUT}/nodes.txt"
srun -N 4 -n 4 -w atlantica[07-10] --distribution=block \
    bash -c 'echo "== $(hostname) =="; lscpu' > "${OUT}/lscpu.txt"

REPS=${REPS:-10}

extrair_campo() {
    local linha="$1" chave="$2"
    echo "${linha}" | sed -n "s/.*${chave}=\([^ ]*\).*/\1/p"
}

medir_calib() {
    local n="$1"
    local log="${OUT}/raw/calib_n${n}.out"
    echo "calibracao n=${n}"
    srun -N 1 -n 1 -w atlantica07 --cpu-bind=cores ./bin/sequencial "${n}" > "${log}"
    local linha tempo
    linha=$(grep '^resultado ' "${log}" | tail -1)
    tempo=$(extrair_campo "${linha}" "tempo")
    echo "${n} ${tempo}" | tee -a "${OUT}/calib.txt"
}

if [ "${N:-1792}" != "auto" ]; then
    N="${N:-1792}"
    echo "N oficial: ${N}"
else
    : > "${OUT}/calib.txt"
    N=1600
    medir_calib "${N}"
    for _ in 1 2 3 4; do
        if escolha=$(python3 scripts/escolhe_n.py "${OUT}/calib.txt"); then
            N=${escolha}
            break
        fi
        medir_calib "${escolha}"
        N=${escolha}
    done
fi
echo "${N}" | tee "${OUT}/n.txt"

# Exporta uma grade pequena 360x360 para ilustracoes fieis do relevo/lagos
./bin/sequencial 360 20260401 --exportar "${OUT}/mapa360" > "${OUT}/mapa360.txt"

if [ -f "${OUT}/runs.csv" ]; then
    mv "${OUT}/runs.csv" "${OUT}/runs-$(date +%Y%m%d-%H%M%S).csv"
fi
echo "versao,coletiva,n,p,nos,rep,iteracoes,volume_retido,celulas_alagadas,soma_cotas,tempo,t_serial,frac_seq,comp_med,comp_min,comp_max,verif_med,verif_min,verif_max,espera_med,troca_med,troca_min,troca_max,extra_med,verificacao" > "${OUT}/runs.csv"

REF_ITER=""
REF_VOL=""
REF_CEL=""
REF_SOMA=""

for rep in $(seq 1 "${REPS}"); do
    log="${OUT}/raw/seq_n${N}_r${rep}.out"
    echo "sequencial n=${N} rep=${rep}"
    srun -N 1 -n 1 -w atlantica07 --cpu-bind=cores ./bin/sequencial "${N}" > "${log}"
    linha=$(grep '^resultado ' "${log}" | tail -1)
    iter=$(extrair_campo "${linha}" "iteracoes")
    vol=$(extrair_campo "${linha}" "volume_retido")
    cel=$(extrair_campo "${linha}" "celulas_alagadas")
    soma=$(extrair_campo "${linha}" "soma_cotas")
    tempo=$(extrair_campo "${linha}" "tempo")
    tser=$(extrair_campo "${linha}" "t_serial")
    tpar=$(extrair_campo "${linha}" "t_paralelo")
    fseq=$(extrair_campo "${linha}" "frac_seq")

    if [ -z "${REF_ITER}" ]; then
        REF_ITER="${iter}"
        REF_VOL="${vol}"
        REF_CEL="${cel}"
        REF_SOMA="${soma}"
    fi
    ver="OK"
    if [ "${iter}" != "${REF_ITER}" ] || [ "${vol}" != "${REF_VOL}" ] || \
       [ "${cel}" != "${REF_CEL}" ] || [ "${soma}" != "${REF_SOMA}" ]; then
        ver="ERRO"
    fi
    echo "sequencial,nenhuma,${N},1,1,${rep},${iter},${vol},${cel},${soma},${tempo},${tser},${fseq},${tpar},${tpar},${tpar},0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,${tser},${ver}" >> "${OUT}/runs.csv"
    [ "${ver}" = "OK" ] || { echo "ERRO no sequencial rep=${rep}" >&2; exit 1; }
done

nos_para_p() {
    local p="$1"
    if [ "${p}" -le 8 ]; then
        echo "1 atlantica07 cores"
    elif [ "${p}" -eq 16 ]; then
        echo "2 atlantica[07-08] cores"
    elif [ "${p}" -eq 32 ]; then
        echo "4 atlantica[07-10] cores"
    else
        echo "4 atlantica[07-10] threads"
    fi
}

roda_mpi() {
    local col="$1" p="$2" rep="$3" flag_extra="${4:-}"
    read -r nos lista bind <<< "$(nos_para_p "${p}")"
    local log="${OUT}/raw/mpi_${col}_n${N}_p${p}_r${rep}.out"
    echo "mpi coletiva=${col} n=${N} p=${p} nos=${nos} bind=${bind} rep=${rep}"
    if [ -n "${flag_extra}" ]; then
        srun -N "${nos}" -n "${p}" -w "${lista}" --distribution=block --cpu-bind="${bind}" \
            ./bin/fases_mpi "${N}" "${flag_extra}" > "${log}"
    else
        srun -N "${nos}" -n "${p}" -w "${lista}" --distribution=block --cpu-bind="${bind}" \
            ./bin/fases_mpi "${N}" > "${log}"
    fi

    local linha iter vol cel soma tempo cmed cmin cmax vmed vmin vmax esp tmed tmin tmax exmed ver
    linha=$(grep '^resultado ' "${log}" | tail -1)
    iter=$(extrair_campo "${linha}" "iteracoes")
    vol=$(extrair_campo "${linha}" "volume_retido")
    cel=$(extrair_campo "${linha}" "celulas_alagadas")
    soma=$(extrair_campo "${linha}" "soma_cotas")
    tempo=$(extrair_campo "${linha}" "tempo")
    cmed=$(extrair_campo "${linha}" "comp_med")
    cmin=$(extrair_campo "${linha}" "comp_min")
    cmax=$(extrair_campo "${linha}" "comp_max")
    vmed=$(extrair_campo "${linha}" "verif_med")
    vmin=$(extrair_campo "${linha}" "verif_min")
    vmax=$(extrair_campo "${linha}" "verif_max")
    esp=$(extrair_campo "${linha}" "espera_med")
    tmed=$(extrair_campo "${linha}" "troca_med")
    tmin=$(extrair_campo "${linha}" "troca_min")
    tmax=$(extrair_campo "${linha}" "troca_max")
    exmed=$(extrair_campo "${linha}" "extra_med")

    ver="OK"
    if [ "${iter}" != "${REF_ITER}" ] || [ "${vol}" != "${REF_VOL}" ] || \
       [ "${cel}" != "${REF_CEL}" ] || [ "${soma}" != "${REF_SOMA}" ]; then
        ver="ERRO"
    fi

    echo "mpi,${col},${N},${p},${nos},${rep},${iter},${vol},${cel},${soma},${tempo},0.000000,0.000000,${cmed},${cmin},${cmax},${vmed},${vmin},${vmax},${esp},${tmed},${tmin},${tmax},${exmed},${ver}" >> "${OUT}/runs.csv"
    if [ "${ver}" != "OK" ]; then
        echo "ERRO de equivalencia em ${log}" >&2
        cat "${log}" >&2 || true
        exit 1
    fi
}

# Serie principal (MPI_Allreduce): P = 1, 2, 4, 8, 16, 32 e 64
for p in 1 2 4 8 16 32 64; do
    for rep in $(seq 1 "${REPS}"); do
        roda_mpi "allreduce" "${p}" "${rep}" ""
    done
done

# Serie complementar para quantificar P broadcasts vs MPI_Allreduce (Secao 6.2)
for p in 8 16 32 64; do
    for rep in $(seq 1 "${REPS}"); do
        roda_mpi "bcast" "${p}" "${rep}" "--bcast"
    done
done

python3 scripts/resumir.py "${OUT}/runs.csv" | tee "${OUT}/resumo.txt"
echo "campanha concluida com sucesso"
