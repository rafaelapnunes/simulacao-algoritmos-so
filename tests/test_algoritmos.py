"""Testes dos algoritmos de substituição e da leitura dos traces.

Os testes combinam um caso com resultado conhecido (a sequência de referência
clássica do livro do Silberschatz) com propriedades que qualquer
implementação correta precisa respeitar, verificadas sobre uma sequência
aleatória reprodutível.
"""

import random

import pytest

from algoritmos import lru, lru_aproximado, opt
from leitor_trace import endereco_para_pagina, ler_trace

# Sequência clássica de Silberschatz; com 3 frames: OPT = 9, LRU = 12
SEQUENCIA_CLASSICA = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]


def sequencia_aleatoria(tamanho=5000, paginas=60, semente=42):
    """Gera uma sequência de acessos aleatória, sempre a mesma para a mesma semente."""
    gerador = random.Random(semente)
    return [gerador.randrange(paginas) for _ in range(tamanho)]


def test_opt_sequencia_classica():
    """O OPT reproduz o resultado do livro: 9 falhas com 3 frames."""
    assert opt(SEQUENCIA_CLASSICA, 3) == 9


def test_lru_sequencia_classica():
    """O LRU reproduz o resultado do livro: 12 falhas com 3 frames."""
    assert lru(SEQUENCIA_CLASSICA, 3) == 12


def test_lru_aproximado_com_intervalo_1_equivale_ao_lru():
    """Deslocando a cada acesso e com bits suficientes, o histórico registra a ordem exata de uso."""
    assert lru_aproximado(SEQUENCIA_CLASSICA, 3, bits=32, intervalo=1) == 12


@pytest.mark.parametrize("frames", [1, 2, 4, 8, 16, 32])
def test_opt_nunca_supera_os_demais(frames):
    """O OPT é o limite inferior: nenhuma política pode ter menos falhas."""
    paginas = sequencia_aleatoria()
    falhas_opt = opt(paginas, frames)
    assert falhas_opt <= lru(paginas, frames)
    assert falhas_opt <= lru_aproximado(paginas, frames, bits=8, intervalo=10)


@pytest.mark.parametrize("algoritmo", [opt, lru, lru_aproximado])
def test_memoria_suficiente_so_tem_falhas_compulsorias(algoritmo):
    """Se todas as páginas cabem na memória, só ocorre uma falha por página distinta."""
    paginas = sequencia_aleatoria()
    distintas = len(set(paginas))
    assert algoritmo(paginas, distintas) == distintas
    assert algoritmo(paginas, distintas + 10) == distintas


@pytest.mark.parametrize("algoritmo", [opt, lru, lru_aproximado])
def test_um_frame_falha_sempre_que_a_pagina_muda(algoritmo):
    """Com um único frame, toda troca de página entre acessos consecutivos é uma falha."""
    paginas = sequencia_aleatoria()
    trocas = 1 + sum(1 for a, b in zip(paginas, paginas[1:]) if a != b)
    assert algoritmo(paginas, 1) == trocas


def test_endereco_para_pagina():
    """O número da página são os 20 bits superiores do endereço (páginas de 4096 bytes)."""
    assert endereco_para_pagina("31348900") == 0x31348
    assert endereco_para_pagina("00000fff") == 0
    assert endereco_para_pagina("00001000") == 1
    assert endereco_para_pagina("ffffffff") == 0xFFFFF


def test_ler_trace(tmp_path):
    """O leitor ignora o tipo de acesso e as linhas em branco."""
    arquivo = tmp_path / "exemplo.trace"
    arquivo.write_text("31348900 W\n31348a10 R\n\n0041f7a0 R\n")
    assert ler_trace(arquivo) == [0x31348, 0x31348, 0x0041F]
