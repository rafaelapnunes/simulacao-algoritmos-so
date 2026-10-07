"""Políticas de substituição de páginas.

Todas as funções seguem o mesmo modelo de simulação:

- a memória tem ``num_frames`` frames, todos vazios no início;
- para cada acesso da sequência, se a página já está em algum frame há um
  acerto; caso contrário há uma falha de página;
- na falha, se ainda existe frame livre a página é carregada nele; se não
  existe, a política escolhe uma página vítima para sair da memória.

Cada função recebe a sequência de números de página acessados (ver
``leitor_trace.ler_trace``) e devolve o número total de falhas, incluindo as
falhas compulsórias, que ocorrem no primeiro acesso a cada página e não podem
ser evitadas por nenhuma política.
"""

import heapq
from collections import OrderedDict


def opt(paginas, num_frames):
    """Simula o algoritmo ótimo (OPT, ou MIN, de Belady).

    Na falha, expulsa a página cujo próximo uso está mais distante no futuro,
    ou que nunca mais será usada. Nenhuma outra política consegue menos falhas
    para a mesma sequência, então o OPT serve como limite inferior para
    comparação. Não é implementável em um sistema operacional real, pois exige
    conhecer os acessos futuros, o que aqui é possível porque o trace inteiro
    está disponível.

    Implementação:

    1. Uma passada de trás para frente calcula ``proximo_uso[i]``, a posição
       do próximo acesso à mesma página acessada na posição ``i``.
    2. As páginas em memória ficam em um max-heap ordenado pelo próximo uso.
       Quando uma página é acessada de novo, uma nova entrada é inserida e a
       antiga fica desatualizada no heap; ela é descartada quando chega ao
       topo (remoção preguiçosa). Isso evita procurar a vítima percorrendo o
       trace a cada falha.

    Complexidade: O(n log n) no pior caso, sendo n o número de acessos.

    Args:
        paginas: sequência de números de página acessados, em ordem.
        num_frames: quantidade de frames disponíveis (pelo menos 1).

    Returns:
        Número de falhas de página.
    """
    _validar_frames(num_frames)
    total = len(paginas)
    nunca_mais = total  # maior que qualquer posição válida do trace

    # proximo_uso[i] = posição do próximo acesso à mesma página de paginas[i]
    proximo_uso = [0] * total
    ultima_posicao = {}
    for i in range(total - 1, -1, -1):
        pagina = paginas[i]
        proximo_uso[i] = ultima_posicao.get(pagina, nunca_mais)
        ultima_posicao[pagina] = i

    em_memoria = {}  # página -> posição do seu próximo uso
    heap = []  # max-heap de (-próximo uso, página), com remoção preguiçosa
    falhas = 0
    for i, pagina in enumerate(paginas):
        if pagina not in em_memoria:
            falhas += 1
            if len(em_memoria) == num_frames:
                while True:
                    negativo, vitima = heapq.heappop(heap)
                    # Entradas antigas de uma página que voltou a ser usada são descartadas
                    if em_memoria.get(vitima) == -negativo:
                        break
                del em_memoria[vitima]
        em_memoria[pagina] = proximo_uso[i]
        heapq.heappush(heap, (-proximo_uso[i], pagina))
    return falhas


def lru(paginas, num_frames):
    """Simula o LRU exato (Least Recently Used).

    Na falha, expulsa a página que está há mais tempo sem ser usada. Parte do
    princípio da localidade temporal: o passado recente é uma boa previsão do
    futuro próximo. Em hardware real, manter a ordem exata de uso a cada acesso
    é caro demais, por isso existem aproximações como ``lru_aproximado``.

    Implementação: um ``OrderedDict`` mantém as páginas da menos para a mais
    recentemente usada. Num acerto, a página vai para o fim; na falha, sai a
    primeira. Complexidade: O(n).

    Args:
        paginas: sequência de números de página acessados, em ordem.
        num_frames: quantidade de frames disponíveis (pelo menos 1).

    Returns:
        Número de falhas de página.
    """
    _validar_frames(num_frames)
    em_memoria = OrderedDict()  # do menos para o mais recentemente usado
    falhas = 0
    for pagina in paginas:
        if pagina in em_memoria:
            em_memoria.move_to_end(pagina)
        else:
            falhas += 1
            if len(em_memoria) == num_frames:
                em_memoria.popitem(last=False)
            em_memoria[pagina] = None
    return falhas


def lru_aproximado(paginas, num_frames, bits=32, intervalo=100):
    """Simula o LRU aproximado com bit de referência e N bits de histórico (aging).

    Cada página em memória tem:

    - um bit de referência R, que o "hardware" coloca em 1 a cada acesso;
    - um registrador de histórico com ``bits`` bits, mantido pelo "sistema
      operacional".

    A cada ``intervalo`` acessos (um tique do relógio), o histórico de todas
    as páginas em memória é deslocado uma posição para a direita, o bit R
    entra como bit mais significativo e R é zerado. Assim, o histórico guarda
    se a página foi usada em cada um dos últimos ``bits`` intervalos, com os
    intervalos mais recentes nos bits de maior peso. Quanto menor o valor do
    registrador, há mais tempo a página não é usada.

    Escolha da vítima: sai a página com menor valor de (R, histórico). R é
    comparado primeiro porque indica uso desde o último deslocamento, ou seja,
    mais recente que qualquer informação do histórico. Em caso de empate, sai
    a página carregada há mais tempo (como no FIFO). Uma página recém-carregada
    entra com R = 1 e histórico zerado.

    Os parâmetros determinam a "memória" do algoritmo: o histórico cobre os
    últimos ``bits * intervalo`` acessos. Intervalos grandes demais fazem
    quase todas as páginas terem R = 1 (perde-se a ordem dentro do intervalo);
    janelas curtas demais deixam muitas páginas com histórico zerado e
    empatadas.

    Implementação: o conjunto ``referenciadas`` representa as páginas com
    R = 1. Complexidade: O(n * F / intervalo) para os deslocamentos mais
    O(F) por falha para escolher a vítima, sendo F o número de frames.

    Args:
        paginas: sequência de números de página acessados, em ordem.
        num_frames: quantidade de frames disponíveis (pelo menos 1).
        bits: tamanho N do registrador de histórico (pelo menos 1).
        intervalo: número T de acessos entre dois deslocamentos (pelo menos 1).

    Returns:
        Número de falhas de página.
    """
    _validar_frames(num_frames)
    if bits < 1:
        raise ValueError("o número de bits de histórico deve ser pelo menos 1")
    if intervalo < 1:
        raise ValueError("o intervalo de deslocamento deve ser pelo menos 1")

    bit_mais_significativo = 1 << (bits - 1)
    historico = {}  # página em memória -> registrador de N bits
    referenciadas = set()  # páginas em memória com bit R = 1
    carga = {}  # página em memória -> instante em que foi carregada (desempate)
    falhas = 0
    for i, pagina in enumerate(paginas):
        if i and i % intervalo == 0:
            for p in historico:
                historico[p] >>= 1
            for p in referenciadas:
                historico[p] |= bit_mais_significativo
            referenciadas.clear()

        if pagina in historico:
            referenciadas.add(pagina)
            continue

        falhas += 1
        if len(historico) == num_frames:
            vitima = min(historico, key=lambda p: (p in referenciadas, historico[p], carga[p]))
            del historico[vitima], carga[vitima]
            referenciadas.discard(vitima)
        historico[pagina] = 0
        referenciadas.add(pagina)
        carga[pagina] = i
    return falhas


def _validar_frames(num_frames):
    """Garante que exista ao menos um frame para a simulação."""
    if num_frames < 1:
        raise ValueError("o número de frames deve ser pelo menos 1")
