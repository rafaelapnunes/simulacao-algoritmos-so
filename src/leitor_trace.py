"""Leitura dos arquivos de trace de acessos à memória.

Cada linha do trace tem o formato ``31348900 W``: um endereço virtual de 32
bits em hexadecimal, seguido do tipo de acesso (``R`` para leitura, ``W`` para
escrita).

Com páginas de 4096 bytes (2^12), o endereço se divide em:

- 12 bits inferiores: deslocamento dentro da página, irrelevante para a
  simulação;
- 20 bits superiores: número da página virtual.

Exemplo: ``0x31348900 >> 12 = 0x31348``. O tipo de acesso não influencia o
número de falhas de página, por isso apenas o número da página é guardado.
"""

TAMANHO_PAGINA = 4096
BITS_DESLOCAMENTO = TAMANHO_PAGINA.bit_length() - 1  # 12 bits de deslocamento


def endereco_para_pagina(endereco_hex):
    """Converte um endereço em hexadecimal no número da sua página.

    Args:
        endereco_hex: endereço de 32 bits em hexadecimal, sem prefixo ``0x``
            (por exemplo, ``"31348900"``).

    Returns:
        Número da página, isto é, os 20 bits superiores do endereço.
    """
    return int(endereco_hex, 16) >> BITS_DESLOCAMENTO


def ler_trace(caminho):
    """Lê um arquivo de trace e devolve a sequência de páginas acessadas.

    Linhas em branco são ignoradas. O trace inteiro é carregado em memória,
    pois o algoritmo OPT precisa conhecer os acessos futuros e todos os
    algoritmos reaproveitam a mesma sequência.

    Args:
        caminho: caminho do arquivo de trace.

    Returns:
        Lista com o número da página de cada acesso, na ordem do trace.
    """
    paginas = []
    with open(caminho, encoding="ascii") as arquivo:
        for linha in arquivo:
            partes = linha.split()
            if partes:
                paginas.append(endereco_para_pagina(partes[0]))
    return paginas
