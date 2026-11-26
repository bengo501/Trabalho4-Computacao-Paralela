#ifndef RELEVO_H
#define RELEVO_H

#include <stdint.h>

/* Cota inicial de inundacao acima de qualquer pico do terreno (em mm). */
#define COTA_INFINITA 1000000000

/* Semente padrao do terreno sintetico deterministico. */
#define SEMENTE_PADRAO 20260401ULL

typedef struct {
    long long volume_retido;
    long long celulas_alagadas;
    long long soma_cotas;
} ResumoRelevo;

/* Gera o Modelo Digital de Elevacao Z[n * n] com cristas encaixadas,
 * gargantas alternadas e crateras locais para testar o escoamento. */
void gerar_relevo(int *z, int n, uint64_t semente);

/* Inicializa o nivel de agua W[0..linhas-1] para as linhas globais
 * [linha_ini, linha_ini + linhas). As bordas externas do mapa recebem Z
 * e o interior recebe COTA_INFINITA. O buffer w tem (linhas + 2) * n
 * posicoes: linha 0 e linha (linhas + 1) sao as bordas fantasmas (halo). */
void inicializar_agua_faixa(int *w, const int *z_faixa, int n,
                            int linha_ini, int linhas);

/* Fase 1 (computacao local): executa uma iteracao sincrona de
 * Planchon-Darboux sobre as linhas internas 1..linhas do buffer local
 * w_atual (lendo tambem as linhas fantasmas 0 e linhas+1) e grava em
 * w_prox. Devolve 1 se alguma altura diminuiu nesta faixa, ou 0 caso
 * contrario. */
int passo_planchon_darboux(const int * restrict w_atual,
                           int * restrict w_prox,
                           const int * restrict z_faixa,
                           int n, int linha_ini, int linhas);

/* Soma o volume de agua retido (W - Z), o numero de celulas alagadas
 * (W > Z) e a soma total das cotas finais W na faixa local. */
ResumoRelevo resumir_faixa(const int *w_atual, const int *z_faixa,
                           int n, int linhas);

/* Calcula quantas linhas e o deslocamento inicial cabem ao processo rank
 * na divisao balanceada de n linhas entre p processos. */
void dividir_linhas(int n, int p, int rank, int *linha_ini, int *linhas);

#endif
