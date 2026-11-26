/* Testes locais de corretude e equivalencia do algoritmo de Planchon-Darboux:
 * 1) Confere em uma grade analitica 5x5 com cratera central fechada se o nivel
 *    final da agua iguala exatamente a soleira de transbordamento.
 * 2) Simula em memoria a divisao em P faixas com troca de bordas (para varios
 *    valores de N e P, inclusive N nao multiplo de P) e verifica se iteracoes,
 *    volume_retido, celulas_alagadas e soma_cotas batem bit a bit com P=1. */

#include "relevo.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void exige(int cond, const char *msg)
{
    if (!cond) {
        fprintf(stderr, "FALHA: %s\n", msg);
        exit(1);
    }
}

static void teste_cratera_analitica(void)
{
    /* Grade 5x5: borda com altura 10, anel intermediario com altura 50 e uma
     * unica soleira de altura 30 no norte; centro fundo com altura 12.
     * O centro deve estabilizar exatamente na cota 30 (volume retido = 18). */
    const int n = 5;
    int z[25] = {
        10, 10, 10, 10, 10,
        10, 50, 30, 50, 10,
        10, 50, 12, 50, 10,
        10, 50, 50, 50, 10,
        10, 10, 10, 10, 10
    };
    int buf_a[35], buf_b[35];
    int *w_a = buf_a, *w_b = buf_b;
    inicializar_agua_faixa(w_a, z, n, 0, n);
    inicializar_agua_faixa(w_b, z, n, 0, n);

    int iter = 0, mudou = 0;
    do {
        mudou = passo_planchon_darboux(w_a, w_b, z, n, 0, n);
        int *t = w_a;
        w_a = w_b;
        w_b = t;
        iter++;
    } while (mudou);

    ResumoRelevo r = resumir_faixa(w_a, z, n, n);
    exige(r.celulas_alagadas == 1, "cratera 5x5 deve ter exatamente 1 celula alagada");
    exige(r.volume_retido == 18, "cratera 5x5 deve reter volume 30 - 12 = 18");
    exige(iter > 1, "cratera 5x5 deve exigir mais de 1 iteracao");
}

static void rodar_simulado_faixas(const int *z_global, int n, int p,
                                  int *out_iter, ResumoRelevo *out_res)
{
    int **w_a = malloc((size_t)p * sizeof(int *));
    int **w_b = malloc((size_t)p * sizeof(int *));
    int *ini = malloc((size_t)p * sizeof(int));
    int *lin = malloc((size_t)p * sizeof(int));

    for (int r = 0; r < p; r++) {
        dividir_linhas(n, p, r, &ini[r], &lin[r]);
        w_a[r] = malloc((size_t)(lin[r] + 2) * (size_t)n * sizeof(int));
        w_b[r] = malloc((size_t)(lin[r] + 2) * (size_t)n * sizeof(int));
        const int *zf = z_global + (size_t)ini[r] * (size_t)n;
        inicializar_agua_faixa(w_a[r], zf, n, ini[r], lin[r]);
        inicializar_agua_faixa(w_b[r], zf, n, ini[r], lin[r]);
    }

    int iter = 0;
    for (;;) {
        /* Troca de bordas antes/entre iteracoes (equivale ao Sendrecv). */
        for (int r = 0; r < p; r++) {
            if (r > 0) {
                memcpy(w_a[r],
                       w_a[r - 1] + (size_t)lin[r - 1] * (size_t)n,
                       (size_t)n * sizeof(int));
            }
            if (r < p - 1) {
                memcpy(w_a[r] + (size_t)(lin[r] + 1) * (size_t)n,
                       w_a[r + 1] + (size_t)n,
                       (size_t)n * sizeof(int));
            }
        }

        int mudou_global = 0;
        for (int r = 0; r < p; r++) {
            const int *zf = z_global + (size_t)ini[r] * (size_t)n;
            int m = passo_planchon_darboux(w_a[r], w_b[r], zf, n, ini[r], lin[r]);
            mudou_global |= m;
            int *tmp = w_a[r];
            w_a[r] = w_b[r];
            w_b[r] = tmp;
        }
        iter++;
        if (!mudou_global)
            break;
    }

    ResumoRelevo tot = {0, 0, 0};
    for (int r = 0; r < p; r++) {
        const int *zf = z_global + (size_t)ini[r] * (size_t)n;
        ResumoRelevo loc = resumir_faixa(w_a[r], zf, n, lin[r]);
        tot.volume_retido += loc.volume_retido;
        tot.celulas_alagadas += loc.celulas_alagadas;
        tot.soma_cotas += loc.soma_cotas;
        free(w_a[r]);
        free(w_b[r]);
    }
    free(w_a);
    free(w_b);
    free(ini);
    free(lin);

    *out_iter = iter;
    *out_res = tot;
}

int main(void)
{
    teste_cratera_analitica();

    int ns[] = { 64, 127, 200 };
    int ps[] = { 2, 3, 4, 7, 8, 16, 32, 64 };

    for (size_t in = 0; in < sizeof(ns) / sizeof(ns[0]); in++) {
        int n = ns[in];
        int *z = malloc((size_t)n * (size_t)n * sizeof(int));
        exige(z != NULL, "malloc z");
        gerar_relevo(z, n, SEMENTE_PADRAO);

        int iter_ref = 0;
        ResumoRelevo res_ref;
        rodar_simulado_faixas(z, n, 1, &iter_ref, &res_ref);
        exige(iter_ref > 10, "relevo sintetico deve exigir varias iteracoes");
        exige(res_ref.volume_retido > 0, "relevo sintetico deve reter agua nas crateras");

        for (size_t ip = 0; ip < sizeof(ps) / sizeof(ps[0]); ip++) {
            int p = ps[ip];
            if (p > n)
                continue;
            int iter_p = 0;
            ResumoRelevo res_p;
            rodar_simulado_faixas(z, n, p, &iter_p, &res_p);
            exige(iter_p == iter_ref, "iteracoes divergentes entre P=1 e P>1");
            exige(res_p.volume_retido == res_ref.volume_retido, "volume divergente");
            exige(res_p.celulas_alagadas == res_ref.celulas_alagadas, "contagem divergente");
            exige(res_p.soma_cotas == res_ref.soma_cotas, "soma_cotas divergente");
        }
        printf("ok n=%d iteracoes=%d volume_retido=%lld celulas_alagadas=%lld\n",
               n, iter_ref, res_ref.volume_retido, res_ref.celulas_alagadas);
        free(z);
    }

    printf("todos os testes de equivalencia passaram.\n");
    return 0;
}
