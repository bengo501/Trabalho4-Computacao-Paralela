/* Preenchimento de depressoes em relevo (Planchon-Darboux, 2001) no modelo
 * fases paralelas com MPI.
 *
 * Cada processo recebe uma faixa contigua de ~N/P linhas do Modelo Digital de
 * Elevacao (DEM) via MPI_Scatterv e repete tres fases ate convergir:
 *   1. Computacao local: atualiza as cotas da agua W na sua faixa.
 *   2. Verificacao da parada: combina mudou_local entre todos os ranks com
 *      MPI_Allreduce (ou P chamadas MPI_Bcast com --bcast) para decidir em
 *      conjunto se todas as faixas estabilizaram.
 *   3. Troca de dados: envia a primeira e a ultima linha interna aos vizinhos
 *      rank-1 e rank+1 com MPI_Isend/MPI_Irecv simultaneos e MPI_Waitall,
 *      atualizando as linhas fantasmas em full-duplex. */

#include "relevo.h"

#include <inttypes.h>
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TAG_SOBE  10
#define TAG_DESCE 11

static void trocar_bordas(int *w, int n, int linhas, int acima, int abaixo)
{
    size_t larg = (size_t)n;
    int *halo_sup = w;
    int *primeira = w + larg;
    int *ultima   = w + (size_t)linhas * larg;
    int *halo_inf = w + (size_t)(linhas + 1) * larg;

    MPI_Request reqs[4];
    MPI_Irecv(halo_sup, n, MPI_INT, acima,  TAG_DESCE, MPI_COMM_WORLD, &reqs[0]);
    MPI_Irecv(halo_inf, n, MPI_INT, abaixo, TAG_SOBE,  MPI_COMM_WORLD, &reqs[1]);
    MPI_Isend(primeira, n, MPI_INT, acima,  TAG_SOBE,  MPI_COMM_WORLD, &reqs[2]);
    MPI_Isend(ultima,   n, MPI_INT, abaixo, TAG_DESCE, MPI_COMM_WORLD, &reqs[3]);
    MPI_Waitall(4, reqs, MPI_STATUSES_IGNORE);
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);

    int rank = 0, p = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &p);

    if (argc < 2) {
        if (rank == 0)
            fprintf(stderr, "uso: %s <n> [semente] [--bcast]\n", argv[0]);
        MPI_Finalize();
        return 1;
    }

    int n = atoi(argv[1]);
    uint64_t semente = SEMENTE_PADRAO;
    int usar_bcast = 0;

    for (int i = 2; i < argc; i++) {
        if (strcmp(argv[i], "--bcast") == 0)
            usar_bcast = 1;
        else
            semente = strtoull(argv[i], NULL, 10);
    }

    if (n < 4 || n < p) {
        if (rank == 0)
            fprintf(stderr, "erro: n=%d invalido para p=%d processos\n", n, p);
        MPI_Finalize();
        return 1;
    }

    int linha_ini = 0, linhas = 0;
    dividir_linhas(n, p, rank, &linha_ini, &linhas);

    int *counts = NULL;
    int *displs = NULL;
    int *z_global = NULL;

    if (rank == 0) {
        counts = malloc((size_t)p * sizeof(int));
        displs = malloc((size_t)p * sizeof(int));
        z_global = malloc((size_t)n * (size_t)n * sizeof(int));
        if (!counts || !displs || !z_global) {
            fprintf(stderr, "erro: falta de memoria na raiz\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        for (int r = 0; r < p; r++) {
            int ini_r = 0, lin_r = 0;
            dividir_linhas(n, p, r, &ini_r, &lin_r);
            counts[r] = lin_r * n;
            displs[r] = ini_r * n;
        }
    }

    int *z_local = malloc((size_t)linhas * (size_t)n * sizeof(int));
    int *w_a = malloc((size_t)(linhas + 2) * (size_t)n * sizeof(int));
    int *w_b = malloc((size_t)(linhas + 2) * (size_t)n * sizeof(int));
    if (!z_local || !w_a || !w_b) {
        fprintf(stderr, "erro: falta de memoria no rank %d\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    int acima  = (rank > 0)     ? (rank - 1) : MPI_PROC_NULL;
    int abaixo = (rank < p - 1) ? (rank + 1) : MPI_PROC_NULL;

    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    /* Preparacao inicial: geracao do DEM na raiz e distribuicao 1/P. */
    double tp0 = MPI_Wtime();
    if (rank == 0)
        gerar_relevo(z_global, n, semente);

    MPI_Scatterv(z_global, counts, displs, MPI_INT,
                 z_local, linhas * n, MPI_INT, 0, MPI_COMM_WORLD);

    inicializar_agua_faixa(w_a, z_local, n, linha_ini, linhas);
    inicializar_agua_faixa(w_b, z_local, n, linha_ini, linhas);
    trocar_bordas(w_a, n, linhas, acima, abaixo);
    double t_prep_local = MPI_Wtime() - tp0;

    double t_comp_local  = 0.0;
    double t_verif_local = 0.0;
    double t_troca_local = 0.0;
    int iteracoes = 0;

    for (;;) {
        /* Fase 1: computacao local na faixa 1/P. */
        double f1 = MPI_Wtime();
        int mudou_local = passo_planchon_darboux(w_a, w_b, z_local,
                                                 n, linha_ini, linhas);
        int *tmp = w_a;
        w_a = w_b;
        w_b = tmp;
        iteracoes++;
        t_comp_local += MPI_Wtime() - f1;

        /* Fase 2: verificacao coletiva da parada. */
        double f2 = MPI_Wtime();
        int mudou_global = 0;
        if (!usar_bcast) {
            MPI_Allreduce(&mudou_local, &mudou_global, 1, MPI_INT,
                          MPI_LOR, MPI_COMM_WORLD);
        } else {
            for (int r = 0; r < p; r++) {
                int flag = (rank == r) ? mudou_local : 0;
                MPI_Bcast(&flag, 1, MPI_INT, r, MPI_COMM_WORLD);
                mudou_global |= flag;
            }
        }
        t_verif_local += MPI_Wtime() - f2;

        if (!mudou_global)
            break;

        /* Fase 3: troca das bordas com os vizinhos imediato superior/inferior. */
        double f3 = MPI_Wtime();
        trocar_bordas(w_a, n, linhas, acima, abaixo);
        t_troca_local += MPI_Wtime() - f3;
    }

    double tr0 = MPI_Wtime();
    ResumoRelevo loc = resumir_faixa(w_a, z_local, n, linhas);
    long long v_loc[3] = { loc.volume_retido, loc.celulas_alagadas, loc.soma_cotas };
    long long v_glob[3] = { 0, 0, 0 };
    MPI_Reduce(v_loc, v_glob, 3, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);
    double t_res_local = MPI_Wtime() - tr0;

    double t1 = MPI_Wtime();
    double tempo_total = t1 - t0;

    /* Coleta estatisticas de tempo por fase fora do relogio principal. */
    double fases_loc[4] = { t_comp_local, t_verif_local, t_troca_local,
                            t_prep_local + t_res_local };
    double fases_soma[4] = { 0.0, 0.0, 0.0, 0.0 };
    double fases_min[4]  = { 0.0, 0.0, 0.0, 0.0 };
    double fases_max[4]  = { 0.0, 0.0, 0.0, 0.0 };

    MPI_Reduce(fases_loc, fases_soma, 4, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(fases_loc, fases_min,  4, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(fases_loc, fases_max,  4, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        double comp_med  = fases_soma[0] / p;
        double verif_med = fases_soma[1] / p;
        double troca_med = fases_soma[2] / p;
        double extra_med = fases_soma[3] / p;
        double verif_min = fases_min[1];
        double espera_med = verif_med - verif_min;

        printf("resultado versao=mpi coletiva=%s p=%d n=%d semente=%" PRIu64
               " iteracoes=%d volume_retido=%lld celulas_alagadas=%lld soma_cotas=%lld"
               " tempo=%.6f comp_med=%.6f comp_min=%.6f comp_max=%.6f"
               " verif_med=%.6f verif_min=%.6f verif_max=%.6f espera_med=%.6f"
               " troca_med=%.6f troca_min=%.6f troca_max=%.6f extra_med=%.6f\n",
               usar_bcast ? "bcast" : "allreduce", p, n, semente, iteracoes,
               v_glob[0], v_glob[1], v_glob[2], tempo_total,
               comp_med, fases_min[0], fases_max[0],
               verif_med, verif_min, fases_max[1], espera_med,
               troca_med, fases_min[2], fases_max[2], extra_med);
    }

    free(z_local);
    free(w_a);
    free(w_b);
    free(counts);
    free(displs);
    free(z_global);

    MPI_Finalize();
    return 0;
}
