/* Versao sequencial pura (sem MPI) do preenchimento de depressoes em relevo
 * pelo metodo de Planchon-Darboux (Catena 46, 2001, p. 159-176).
 *
 * Mede o tempo total T1 e separa a etapa estritamente sequencial (geracao do
 * Modelo Digital de Elevacao na raiz) da etapa paralelizavel (inicializacao
 * da lamina d'agua, laco de drenagem ate estabilizar e resumo hidrologico),
 * fornecendo a fracao sequencial s = t_serial / T1 usada no teto de Amdahl. */

#define _POSIX_C_SOURCE 200809L

#include "relevo.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double relogio_segundos(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static int salvar_grades(const char *prefixo, const int *z, const int *w, int n)
{
    char caminho[512];
    snprintf(caminho, sizeof(caminho), "%s_z.bin", prefixo);
    FILE *fz = fopen(caminho, "wb");
    if (!fz)
        return -1;
    fwrite(&n, sizeof(int), 1, fz);
    fwrite(z, sizeof(int), (size_t)n * (size_t)n, fz);
    fclose(fz);

    snprintf(caminho, sizeof(caminho), "%s_w.bin", prefixo);
    FILE *fw = fopen(caminho, "wb");
    if (!fw)
        return -1;
    fwrite(&n, sizeof(int), 1, fw);
    for (int il = 1; il <= n; il++)
        fwrite(w + (size_t)il * (size_t)n, sizeof(int), (size_t)n, fw);
    fclose(fw);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "uso: %s <n> [semente] [--exportar prefixo]\n", argv[0]);
        return 1;
    }

    int n = atoi(argv[1]);
    uint64_t semente = SEMENTE_PADRAO;
    const char *exportar = NULL;

    int argi = 2;
    if (argi < argc && strncmp(argv[argi], "--", 2) != 0) {
        semente = strtoull(argv[argi], NULL, 10);
        argi++;
    }
    if (argi + 1 < argc && strcmp(argv[argi], "--exportar") == 0) {
        exportar = argv[argi + 1];
    }

    if (n < 4) {
        fprintf(stderr, "erro: n deve ser pelo menos 4\n");
        return 1;
    }

    size_t total_z = (size_t)n * (size_t)n;
    size_t total_w = (size_t)(n + 2) * (size_t)n;

    int *z = malloc(total_z * sizeof(int));
    int *w_a = malloc(total_w * sizeof(int));
    int *w_b = malloc(total_w * sizeof(int));
    if (!z || !w_a || !w_b) {
        fprintf(stderr, "erro: falta de memoria para n=%d\n", n);
        free(z);
        free(w_a);
        free(w_b);
        return 1;
    }

    double t0 = relogio_segundos();

    /* Etapa sequencial: construcao do DEM completo na memoria. */
    gerar_relevo(z, n, semente);
    double t_par0 = relogio_segundos();

    /* Etapa paralelizavel: inicializacao, laco iterativo e resumo. */
    inicializar_agua_faixa(w_a, z, n, 0, n);
    inicializar_agua_faixa(w_b, z, n, 0, n);

    int iteracoes = 0;
    int mudou = 0;
    do {
        mudou = passo_planchon_darboux(w_a, w_b, z, n, 0, n);
        int *tmp = w_a;
        w_a = w_b;
        w_b = tmp;
        iteracoes++;
    } while (mudou);

    ResumoRelevo res = resumir_faixa(w_a, z, n, n);
    double t1 = relogio_segundos();

    double tempo_total = t1 - t0;
    double tempo_serial = t_par0 - t0;
    double tempo_paralelo = t1 - t_par0;
    double frac_seq = tempo_total > 0.0 ? (tempo_serial / tempo_total) : 0.0;

    printf("resultado versao=sequencial coletiva=nenhuma p=1 n=%d semente=%" PRIu64
           " iteracoes=%d volume_retido=%lld celulas_alagadas=%lld soma_cotas=%lld"
           " tempo=%.6f t_serial=%.6f t_paralelo=%.6f frac_seq=%.6f\n",
           n, semente, iteracoes, res.volume_retido, res.celulas_alagadas,
           res.soma_cotas, tempo_total, tempo_serial, tempo_paralelo, frac_seq);

    if (exportar && salvar_grades(exportar, z, w_a, n) != 0) {
        fprintf(stderr, "erro ao exportar grades em %s\n", exportar);
        free(z);
        free(w_a);
        free(w_b);
        return 1;
    }

    free(z);
    free(w_a);
    free(w_b);
    return 0;
}
