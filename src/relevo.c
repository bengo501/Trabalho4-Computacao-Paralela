#include "relevo.h"

#include <stddef.h>

static inline uint64_t mistura64(uint64_t x)
{
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

static inline int min2(int a, int b)
{
    return a < b ? a : b;
}

static inline int max2(int a, int b)
{
    return a > b ? a : b;
}

/* Ruido suave bilinear em grade grossa para formar colinas e vales naturais
 * usando apenas aritmetica inteira deterministica. */
static int ruido_suave(int i, int j, int passo, uint64_t semente, int amplitude)
{
    if (passo < 1)
        passo = 1;
    int gi = i / passo;
    int gj = j / passo;
    int fi = ((i % passo) * 1024) / passo;
    int fj = ((j % passo) * 1024) / passo;

    uint64_t h00 = mistura64(semente ^ ((uint64_t)gi * 1315423911ULL + (uint64_t)gj));
    uint64_t h10 = mistura64(semente ^ ((uint64_t)(gi + 1) * 1315423911ULL + (uint64_t)gj));
    uint64_t h01 = mistura64(semente ^ ((uint64_t)gi * 1315423911ULL + (uint64_t)(gj + 1)));
    uint64_t h11 = mistura64(semente ^ ((uint64_t)(gi + 1) * 1315423911ULL + (uint64_t)(gj + 1)));

    int v00 = (int)(h00 % (uint64_t)(2 * amplitude + 1)) - amplitude;
    int v10 = (int)(h10 % (uint64_t)(2 * amplitude + 1)) - amplitude;
    int v01 = (int)(h01 % (uint64_t)(2 * amplitude + 1)) - amplitude;
    int v11 = (int)(h11 % (uint64_t)(2 * amplitude + 1)) - amplitude;

    int a = v00 + ((v10 - v00) * fi) / 1024;
    int b = v01 + ((v11 - v01) * fi) / 1024;
    return a + ((b - a) * fj) / 1024;
}

void gerar_relevo(int *z, int n, uint64_t semente)
{
    const int passo_macro = max2(16, n / 18);
    const int passo_medio = max2(6, n / 64);
    const int passo_cratera = max2(12, n / 28);
    const int r_cratera = max2(3, passo_cratera / 3);
    const int r2_max = r_cratera * r_cratera;

    /* Bacia central encaixada por cristas com gargantas alternadas:
     * obriga o escoamento a percorrer talvegues longos antes de atingir
     * as planicies costeiras, enquanto crateras locais retem lagos. */
    const int i_sul_bacia = (n * 22) / 100;
    const int i_nor_bacia = (n * 78) / 100;
    const int j_esq_bacia = (n * 18) / 100;
    const int j_dir_bacia = (n * 82) / 100;
    const int num_cristas = 2;
    const int alt_bacia = max2(1, i_nor_bacia - i_sul_bacia);

    for (int i = 0; i < n; i++) {
        int dist_i = min2(i, n - 1 - i);
        for (int j = 0; j < n; j++) {
            int dist_j = min2(j, n - 1 - j);
            int dist_borda = min2(dist_i, dist_j);

            /* Rampa continental suave subindo das bordas ate o interior. */
            int cota = 10000 + (int)(((long long)dist_borda * 18000LL) / max2(1, n / 2));

            /* Ondulacoes geomorfologicas em duas escalas + micro-rugosidade. */
            cota += ruido_suave(i, j, passo_macro, semente, 2600);
            cota += ruido_suave(i, j, passo_medio, semente ^ 0x55aa55aaULL, 900);
            uint64_t h_cel = mistura64(semente ^ ((uint64_t)i * 2654435761ULL + (uint64_t)j));
            cota += (int)(h_cel % 181ULL) - 90;

            /* Paredes da bacia hidrologica central e cristas em serpentina. */
            if (i >= i_sul_bacia && i <= i_nor_bacia &&
                j >= j_esq_bacia && j <= j_dir_bacia) {
                int esp = max2(2, n / 140);
                int borda_oeste = (j - j_esq_bacia) < esp;
                int borda_leste = (j_dir_bacia - j) < esp;
                int borda_topo = (i - i_sul_bacia) < esp;
                int borda_base = (i_nor_bacia - i) < esp;

                /* Unica foz principal da bacia na parede norte-central. */
                int foz = borda_topo &&
                          j >= (n / 2 - max2(2, n / 90)) &&
                          j <= (n / 2 + max2(2, n / 90));

                if ((borda_oeste || borda_leste || borda_topo || borda_base) && !foz) {
                    cota += 14000;
                } else {
                    /* Cristas internas horizontais com gargantas alternadas. */
                    for (int k = 1; k <= num_cristas; k++) {
                        int ic = i_sul_bacia + (k * alt_bacia) / (num_cristas + 1);
                        int di = i > ic ? (i - ic) : (ic - i);
                        if (di < max2(1, n / 220)) {
                            int larg_garganta = max2(3, n / 55);
                            int abre_esq = (k % 2 == 1) &&
                                           (j < j_esq_bacia + esp + larg_garganta);
                            int abre_dir = (k % 2 == 0) &&
                                           (j > j_dir_bacia - esp - larg_garganta);
                            if (!abre_esq && !abre_dir)
                                cota += 11500 - k * 500;
                        }
                    }
                }
            }

            /* Rede deterministica de depressoes/crateras fechadas que retem agua. */
            int ci = i / passo_cratera;
            int cj = j / passo_cratera;
            uint64_t hc = mistura64((semente + 7919ULL) ^
                                    ((uint64_t)ci * 40503ULL + (uint64_t)cj));
            if ((hc & 3ULL) == 0ULL && dist_borda > passo_cratera) {
                int centro_i = ci * passo_cratera + passo_cratera / 2;
                int centro_j = cj * passo_cratera + passo_cratera / 2;
                int di = i - centro_i;
                int dj = j - centro_j;
                int d2 = di * di + dj * dj;
                if (d2 < r2_max) {
                    int prof = 3200 + (int)((hc >> 8) % 2800ULL);
                    cota -= (int)(((long long)prof * (r2_max - d2)) / r2_max);
                }
            }

            if (cota < 500)
                cota = 500;
            z[(size_t)i * (size_t)n + (size_t)j] = cota;
        }
    }
}

void dividir_linhas(int n, int p, int rank, int *linha_ini, int *linhas)
{
    int base = n / p;
    int resto = n % p;
    if (rank < resto) {
        *linhas = base + 1;
        *linha_ini = rank * (base + 1);
    } else {
        *linhas = base;
        *linha_ini = resto * (base + 1) + (rank - resto) * base;
    }
}

void inicializar_agua_faixa(int *w, const int *z_faixa, int n,
                            int linha_ini, int linhas)
{
    size_t larg = (size_t)n;
    for (int j = 0; j < n; j++) {
        w[j] = COTA_INFINITA;
        w[(size_t)(linhas + 1) * larg + (size_t)j] = COTA_INFINITA;
    }

    for (int il = 1; il <= linhas; il++) {
        int ig = linha_ini + il - 1;
        int *linha_w = w + (size_t)il * larg;
        const int *linha_z = z_faixa + (size_t)(il - 1) * larg;
        if (ig == 0 || ig == n - 1) {
            for (int j = 0; j < n; j++)
                linha_w[j] = linha_z[j];
        } else {
            linha_w[0] = linha_z[0];
            for (int j = 1; j < n - 1; j++)
                linha_w[j] = COTA_INFINITA;
            linha_w[n - 1] = linha_z[n - 1];
        }
    }
}

int passo_planchon_darboux(const int * restrict w_atual,
                           int * restrict w_prox,
                           const int * restrict z_faixa,
                           int n, int linha_ini, int linhas)
{
    int mudou = 0;
    size_t larg = (size_t)n;

    for (int il = 1; il <= linhas; il++) {
        int ig = linha_ini + il - 1;
        const int *wa = w_atual + (size_t)il * larg;
        int *wp = w_prox + (size_t)il * larg;
        const int *zf = z_faixa + (size_t)(il - 1) * larg;

        if (ig == 0 || ig == n - 1) {
            for (int j = 0; j < n; j++)
                wp[j] = zf[j];
            continue;
        }

        wp[0] = zf[0];
        wp[n - 1] = zf[n - 1];

        const int *wa_sup = wa - larg;
        const int *wa_inf = wa + larg;

        for (int j = 1; j < n - 1; j++) {
            int w_cel = wa[j];
            int z_cel = zf[j];
            if (w_cel > z_cel) {
                int m1 = min2(wa_sup[j - 1], wa_sup[j]);
                int m2 = min2(wa_sup[j + 1], wa[j - 1]);
                int m3 = min2(wa[j + 1], wa_inf[j - 1]);
                int m4 = min2(wa_inf[j], wa_inf[j + 1]);
                int m_viz = min2(min2(m1, m2), min2(m3, m4));
                int novo = max2(z_cel, m_viz);
                if (novo < w_cel) {
                    wp[j] = novo;
                    mudou = 1;
                } else {
                    wp[j] = w_cel;
                }
            } else {
                wp[j] = z_cel;
            }
        }
    }

    return mudou;
}

ResumoRelevo resumir_faixa(const int *w_atual, const int *z_faixa,
                           int n, int linhas)
{
    ResumoRelevo r = {0, 0, 0};
    size_t larg = (size_t)n;

    for (int il = 1; il <= linhas; il++) {
        const int *wa = w_atual + (size_t)il * larg;
        const int *zf = z_faixa + (size_t)(il - 1) * larg;
        for (int j = 0; j < n; j++) {
            int diff = wa[j] - zf[j];
            r.volume_retido += (long long)diff;
            if (diff > 0)
                r.celulas_alagadas++;
            r.soma_cotas += (long long)wa[j];
        }
    }
    return r;
}
