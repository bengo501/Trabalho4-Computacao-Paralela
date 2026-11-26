CC      ?= gcc
MPICC   ?= mpicc
CFLAGS  ?= -O3 -std=c11 -Wall -Wextra
LDFLAGS ?= -lrt

BINDIR  := bin
BINS    := $(BINDIR)/sequencial $(BINDIR)/fases_mpi $(BINDIR)/confere

.PHONY: all clean teste

all: $(BINS)

$(BINDIR):
	mkdir -p $(BINDIR)

$(BINDIR)/relevo.o: src/relevo.c src/relevo.h | $(BINDIR)
	$(CC) $(CFLAGS) -c src/relevo.c -o $@

$(BINDIR)/sequencial: src/sequencial.c $(BINDIR)/relevo.o | $(BINDIR)
	$(CC) $(CFLAGS) src/sequencial.c $(BINDIR)/relevo.o -o $@ $(LDFLAGS)

$(BINDIR)/fases_mpi: src/fases_mpi.c $(BINDIR)/relevo.o | $(BINDIR)
	$(MPICC) $(CFLAGS) src/fases_mpi.c $(BINDIR)/relevo.o -o $@

$(BINDIR)/confere: src/confere.c $(BINDIR)/relevo.o | $(BINDIR)
	$(CC) $(CFLAGS) src/confere.c $(BINDIR)/relevo.o -o $@

teste: $(BINDIR)/confere
	./$(BINDIR)/confere

clean:
	rm -rf $(BINDIR)
