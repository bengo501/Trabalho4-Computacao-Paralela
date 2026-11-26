# Trabalho 4: fases paralelas com MPI (Planchon-Darboux)

Implementação paralela em MPI do algoritmo de preenchimento de depressões em Modelos Digitais de Elevação (Planchon e Darboux, 2001) seguindo o modelo de fases paralelas, com avaliação experimental em até 4 nós exclusivos (64 threads) no cluster Atlântica.

- Disciplina: Computação Paralela e Distribuída (PUCRS)
- Aluno: Bernardo Klein Heitz
- Repositório: https://github.com/bengo501/Trabalho4-Computacao-Paralela
- Cluster: Atlântica (LAD), nós atlantica07 a atlantica10, exclusive

## Problema e modelo de fases paralelas

Dado um terreno representado por uma grade N x N de altitudes Z, depressões fechadas (crateras e bacias sem saída direta) interrompem o traçado hidrológico de redes de drenagem. O método de Planchon e Darboux inunda inicialmente o interior da grade com cota alta W = infinito mantendo W = Z nas bordas abertas do mapa e, a cada iteração, reduz W[i, j] para max(Z[i, j], menor W entre os 8 vizinhos) até que nenhuma célula sofra alteração. O número de iterações não é fixo: depende integralmente da topografia e dos caminhos de escoamento dos dados.

Na versão paralela, o rank 0 gera o relevo Z e distribui faixas horizontais contíguas de N/P linhas via MPI_Scatterv. Cada processo mantém duplo buffer com duas linhas fantasmas (halo superior e inferior) e repete três fases sincronizadas:

1. Computação local: atualiza as linhas internas da sua faixa 1/P lendo o passo anterior (garantindo equivalência matemática exata com o sequencial para qualquer P).
2. Verificação da parada: combina o indicador mudou_local de todos os processos com um único MPI_Allreduce (MPI_LOR) para decidir em conjunto se terminam. Se um processo parasse sozinho, seu vizinho ficaria bloqueado esperando bordas na iteração seguinte.
3. Troca de dados: envia a primeira e a última linha interna aos vizinhos rank - 1 e rank + 1 em full-duplex com MPI_Irecv, MPI_Isend e MPI_Waitall (usando MPI_PROC_NULL nas bordas norte e sul).

## Estrutura

src/           relevo.h, relevo.c, sequencial.c, fases_mpi.c, confere.c
scripts/       campanha.sbatch, campanha_cargas.sbatch, escolhe_n.py, resumir.py
results/       runs.csv, cargas.csv, resumo_campanhas.txt, raw/, raw_cargas/, slurm-*.out, lscpu.txt, nodes.txt, fig_*.png
relatorio/     relatorio.pdf
apresentacao/  apresentacao.pptx, figuras/

## Compilação e testes locais

No cluster Atlântica (Open MPI 4.1.1):

export PATH=/LADAPPs/OpenMPI/openmpi-4.1.1/bin:$PATH
export LD_LIBRARY_PATH=/LADAPPs/OpenMPI/openmpi-4.1.1/lib:$LD_LIBRARY_PATH
make clean && make
make teste

Flags idênticas nas versões sequencial e MPI: -O3 -std=c11 -Wall -Wextra, compartilhando o mesmo objeto numérico bin/relevo.o. O binário sequencial não liga MPI e mede o tempo com clock_gettime.

## Programas

### bin/sequencial (sem MPI)

- ./bin/sequencial n [semente] [--exportar prefixo]
- Imprime iteracoes, volume_retido, celulas_alagadas, soma_cotas, tempo total T1, tempo serial de construção do DEM e a fração sequencial s = t_serial / T1.

### bin/fases_mpi

- ./bin/fases_mpi n [semente] [--bcast]
- Executa as três fases paralelas usando MPI_Allreduce por padrão (ou P chamadas MPI_Bcast quando --bcast é informado) e reporta o tempo total Tp mais média, mínimo e máximo entre os processos para computação local, verificação e troca de bordas.

### bin/confere

Valida o nivelamento exato em uma cratera analítica 5x5 e confere equivalência bit a bit entre P = 1 e P = 2, 3, 4, 7, 8, 16, 32 e 64.

## Campanha no cluster

Respeita a alocação exclusiva mínima que garante 1 processo por núcleo físico (Xeon E5520: 8 núcleos físicos e 16 threads por nó):
- 1 nó exclusivo (atlantica07) para o sequencial e P = 1, 2, 4, 8 (--cpu-bind=cores)
- 2 nós exclusivos (atlantica07 e 08) para P = 16 (--cpu-bind=cores)
- 4 nós exclusivos (atlantica07 a 10) para P = 32 (--cpu-bind=cores) e P = 64 (--cpu-bind=threads, HT)

Submissão e resumo:

sbatch scripts/campanha.sbatch
sbatch scripts/campanha_cargas.sbatch
python3 scripts/resumir.py results/runs.csv

## Resultados oficiais (n = 1792, T1 = 46,034 s, s = 0,72%)

Todas as 120 execuções oficiais convergiram em exatas 2979 iterações, com 1161016 células alagadas e volume retido igual a 3356079226 (verificacao=OK em 100% das rodadas).

| P | Nós | Mediana (s) | Mínimo (s) | Máximo (s) | Speed-up S | Teto Amdahl | Eficiência E |
|---|-----|-------------|------------|------------|------------|-------------|--------------|
| 1 | 1 | 45,991 | 45,908 | 46,035 | 1,00 | 1,00 | 1,00 |
| 2 | 1 | 24,166 | 24,124 | 24,205 | 1,90 | 1,99 | 0,95 |
| 4 | 1 | 14,749 | 14,698 | 14,841 | 3,12 | 3,92 | 0,78 |
| 8 | 1 | 11,923 | 11,902 | 11,953 | 3,86 | 7,62 | 0,48 |
| 16 | 2 | 5,555 | 5,538 | 5,612 | 8,29 | 14,45 | 0,52 |
| 32 | 4 | 3,175 | 3,160 | 3,215 | 14,50 | 26,19 | 0,45 |
| 64 | 4 | 3,571 | 3,540 | 3,624 | 12,89 | 44,10 | 0,20 |

Em P = 32, o menor tempo de verificação entre os processos foi verif_min = 0,379 s (custo puro do MPI_Allreduce) e a espera média pelo processo mais lento foi 0,752 s; em P = 64, a alternativa com P chamadas MPI_Bcast elevou verif_min de 0,599 s para 10,390 s (reduzindo S de 12,89 para 3,43).

## Sensibilidade ao tamanho da carga (results/cargas.csv)

Além da campanha oficial na faixa recomendada de 30 a 60 s (n = 1792, 10 repetições), foram executadas campanhas complementares nos mesmos 4 nós exclusivos com carga leve (n = 1280) e carga pesada (n = 2304), 5 repetições por ponto:

| N | Iterações | T1 mediana (s) | Fração s | S (P=8) | S (P=16) | S (P=32) | S (P=64) |
|---|-----------|----------------|----------|---------|----------|----------|----------|
| 1280 | 2137 | 16,12 | 1,05% | 4,49 | 8,68 | 11,11 | 10,26 |
| 1792 | 2979 | 46,03 | 0,72% | 3,86 | 8,29 | 14,50 | 12,89 |
| 2304 | 3841 | 102,65 | 0,53% | 4,05 | 7,52 | 16,24 | 14,24 |

## Uso de IA

O código C/MPI, os scripts de automação, o relatório e os slides foram desenvolvidos com apoio do Cursor. Todas as medições, saídas brutas do Slurm e verificações de equivalência provêm de execuções reais no cluster Atlântica. O algoritmo hidrológico baseia-se em O. Planchon e F. Darboux, Catena 46 (2001) 159-176.
