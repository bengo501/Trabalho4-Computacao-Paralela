#!/bin/bash
#SBATCH --job-name=t4cargas
#SBATCH --partition=LAD_geral
#SBATCH --nodes=4
#SBATCH --ntasks=64
#SBATCH --ntasks-per-node=16
#SBATCH --exclusive
#SBATCH --nodelist=atlantica[07-10]
#SBATCH --time=00:45:00
#SBATCH --output=results/slurm-%j.out

set -euo pipefail

export PATH=/LADAPPs/OpenMPI/openmpi-4.1.1/bin:$PATH
export LD_LIBRARY_PATH=/LADAPPs/OpenMPI/openmpi-4.1.1/lib:${LD_LIBRARY_PATH:-}
export OMPI_MCA_btl_vader_single_copy_mechanism=none

cd "$SLURM_SUBMIT_DIR"
mkdir -p results/raw_cargas

NODOS=($(scontrol show hostnames "$SLURM_JOB_NODELIST"))
NO1="${NODOS[0]}"
NO2="${NODOS[0]},${NODOS[1]}"
NO4="${NODOS[0]},${NODOS[1]},${NODOS[2]},${NODOS[3]}"

SEMENTE=20260401
REPS=5
CSV="results/cargas.csv"

echo "versao,coletiva,n,p,nos,bind,rep,iteracoes,volume_retido,celulas_alagadas,soma_cotas,tempo,t_serial,frac_seq,comp_med,comp_min,comp_max,verif_med,verif_min,verif_max,espera_med,troca_med,troca_min,troca_max,extra_med" > "$CSV"

extrair_campo() {
    echo "$1" | tr ' ' '\n' | awk -F= -v k="$2" '$1 == k { print $2; exit }'
}

registrar_linha() {
    local linha="$1"
    local versao="$2"
    local coletiva="$3"
    local n="$4"
    local p="$5"
    local nos="$6"
    local bind="$7"
    local rep="$8"

    local iter vol alag soma tempo tser fseq
    local cmed cmin cmax vmed vmin vmax emed tmed tmin tmax xmed
    iter=$(extrair_campo "$linha" iteracoes)
    vol=$(extrair_campo "$linha" volume_retido)
    alag=$(extrair_campo "$linha" celulas_alagadas)
    soma=$(extrair_campo "$linha" soma_cotas)
    tempo=$(extrair_campo "$linha" tempo)

    if [ "$versao" = "sequencial" ]; then
        tser=$(extrair_campo "$linha" t_serial)
        fseq=$(extrair_campo "$linha" frac_seq)
        cmed=$(extrair_campo "$linha" t_paralelo)
        cmin="$cmed"; cmax="$cmed"
        vmed=0; vmin=0; vmax=0; emed=0; tmed=0; tmin=0; tmax=0; xmed="$tser"
    else
        tser=0; fseq=0
        cmed=$(extrair_campo "$linha" comp_med)
        cmin=$(extrair_campo "$linha" comp_min)
        cmax=$(extrair_campo "$linha" comp_max)
        vmed=$(extrair_campo "$linha" verif_med)
        vmin=$(extrair_campo "$linha" verif_min)
        vmax=$(extrair_campo "$linha" verif_max)
        emed=$(extrair_campo "$linha" espera_med)
        tmed=$(extrair_campo "$linha" troca_med)
        tmin=$(extrair_campo "$linha" troca_min)
        tmax=$(extrair_campo "$linha" troca_max)
        xmed=$(extrair_campo "$linha" extra_med)
    fi

    echo "${versao},${coletiva},${n},${p},${nos},${bind},${rep},${iter},${vol},${alag},${soma},${tempo},${tser},${fseq},${cmed},${cmin},${cmax},${vmed},${vmin},${vmax},${emed},${tmed},${tmin},${tmax},${xmed}" >> "$CSV"
}

rodar_carga() {
    local n="$1"
    local ref_iter=""
    local ref_vol=""
    local ref_alag=""

    echo "=== Iniciando carga N=${n} (${REPS} repeticoes por configuracao) ==="

    for r in $(seq 1 "$REPS"); do
        out="results/raw_cargas/seq_n${n}_r${r}.out"
        echo "carga n=${n} sequencial rep=${r}"
        srun --nodes=1 --ntasks=1 --nodelist="$NO1" --cpu-bind=cores \
            ./bin/sequencial "$n" "$SEMENTE" > "$out"
        linha=$(grep '^resultado ' "$out")
        iter=$(extrair_campo "$linha" iteracoes)
        vol=$(extrair_campo "$linha" volume_retido)
        alag=$(extrair_campo "$linha" celulas_alagadas)
        if [ -z "$ref_iter" ]; then
            ref_iter="$iter"; ref_vol="$vol"; ref_alag="$alag"
        elif [ "$iter" != "$ref_iter" ] || [ "$vol" != "$ref_vol" ] || [ "$alag" != "$ref_alag" ]; then
            echo "ERRO equivalencia seq n=${n} rep=${r}" >&2
            exit 1
        fi
        registrar_linha "$linha" "sequencial" "nenhuma" "$n" 1 1 "cores" "$r"
    done

    for spec in "8 1 $NO1 cores" "16 2 $NO2 cores" "32 4 $NO4 cores" "64 4 $NO4 threads"; do
        set -- $spec
        local p="$1" nos="$2" nodelist="$3" bind="$4"
        for r in $(seq 1 "$REPS"); do
            out="results/raw_cargas/mpi_n${n}_p${p}_r${r}.out"
            echo "carga n=${n} mpi p=${p} nos=${nos} bind=${bind} rep=${r}"
            srun --mpi=pmix --nodes="$nos" --ntasks="$p" --nodelist="$nodelist" \
                --cpu-bind="$bind" ./bin/fases_mpi "$n" "$SEMENTE" > "$out"
            linha=$(grep '^resultado ' "$out")
            iter=$(extrair_campo "$linha" iteracoes)
            vol=$(extrair_campo "$linha" volume_retido)
            alag=$(extrair_campo "$linha" celulas_alagadas)
            if [ "$iter" != "$ref_iter" ] || [ "$vol" != "$ref_vol" ] || [ "$alag" != "$ref_alag" ]; then
                echo "ERRO equivalencia mpi n=${n} p=${p} rep=${r}" >&2
                exit 1
            fi
            registrar_linha "$linha" "mpi" "allreduce" "$n" "$p" "$nos" "$bind" "$r"
        done
    done
}

# Carga leve (~17 s sequencial) e carga pesada (~100 s sequencial)
rodar_carga 1280
rodar_carga 2304

echo "Campanha de cargas concluida com sucesso."
