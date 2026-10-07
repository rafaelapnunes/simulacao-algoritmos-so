"""Simulador de falhas de página: compara OPT, LRU exato e LRU aproximado.

Para cada trace e cada quantidade de frames, executa os três algoritmos,
mostra uma tabela no terminal e grava os resultados em CSV. O LRU aproximado
é executado para cada combinação de --bits e --intervalo, o que permite
avaliar a influência desses parâmetros.

Exemplos:
    python src/main.py traces/*.trace.txt
    python src/main.py traces/gcc.trace.txt --frames 4 8 16 --bits 32 --intervalo 100
    python src/main.py traces/*.trace.txt --frames 8 32 128 --bits 2 4 8 16 32 \\
        --intervalo 10 100 1000 10000 --saida resultados/sensibilidade.csv
"""

import argparse
import csv
import os
import time

from algoritmos import lru, lru_aproximado, opt
from leitor_trace import ler_trace

FRAMES_PADRAO = [4, 8, 12, 16, 20, 24, 28, 32, 64, 128, 256]
BITS_PADRAO = 32
INTERVALO_PADRAO = 100
COLUNAS = ["trace", "algoritmo", "frames", "bits", "intervalo", "acessos", "falhas", "taxa_falhas"]


def ler_argumentos():
    """Define e interpreta os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("traces", nargs="+", help="arquivos de trace a simular")
    parser.add_argument("--frames", type=int, nargs="+", default=FRAMES_PADRAO,
                        help="quantidades de frames a avaliar (padrão: %(default)s)")
    parser.add_argument("--bits", type=int, nargs="+", default=[BITS_PADRAO],
                        help="bits de histórico (N) do LRU aproximado; aceita vários valores (padrão: %(default)s)")
    parser.add_argument("--intervalo", type=int, nargs="+", default=[INTERVALO_PADRAO],
                        help="acessos entre deslocamentos (T) do LRU aproximado; aceita vários valores "
                             "(padrão: %(default)s)")
    parser.add_argument("--saida", default=os.path.join("resultados", "resultados.csv"),
                        help="arquivo CSV de saída (padrão: %(default)s)")
    return parser.parse_args()


def simular(caminho, lista_frames, lista_bits, lista_intervalos):
    """Executa todos os algoritmos sobre um trace.

    Para cada quantidade de frames, roda o OPT e o LRU uma vez e o LRU
    aproximado uma vez para cada par (bits, intervalo). O progresso é
    mostrado no terminal, incluindo o tempo de cada execução.

    Args:
        caminho: arquivo de trace.
        lista_frames: quantidades de frames a avaliar.
        lista_bits: valores de N (bits de histórico) do LRU aproximado.
        lista_intervalos: valores de T (acessos entre deslocamentos) do LRU aproximado.

    Returns:
        Lista de dicionários, um por execução, com as chaves de ``COLUNAS``.
        ``bits`` e ``intervalo`` ficam vazios para OPT e LRU.
    """
    nome = os.path.basename(caminho)
    paginas = ler_trace(caminho)
    acessos = len(paginas)
    print(f"\n{nome}: {acessos} acessos, {len(set(paginas))} páginas distintas")

    execucoes = []
    for frames in lista_frames:
        execucoes.append(("OPT", frames, None, None, lambda f=frames: opt(paginas, f)))
        execucoes.append(("LRU", frames, None, None, lambda f=frames: lru(paginas, f)))
        for bits in lista_bits:
            for intervalo in lista_intervalos:
                execucoes.append(("LRU aproximado", frames, bits, intervalo,
                                  lambda f=frames, b=bits, t=intervalo: lru_aproximado(paginas, f, b, t)))

    linhas = []
    for algoritmo, frames, bits, intervalo, executar in execucoes:
        inicio = time.perf_counter()
        falhas = executar()
        duracao = time.perf_counter() - inicio
        parametros = f" (N={bits}, T={intervalo})" if bits is not None else ""
        print(f"  {frames:>5} frames | {algoritmo + parametros:<34} | {falhas:>9} falhas "
              f"| {falhas / acessos:7.2%} | {duracao:6.2f}s")
        linhas.append({
            "trace": nome,
            "algoritmo": algoritmo,
            "frames": frames,
            "bits": "" if bits is None else bits,
            "intervalo": "" if intervalo is None else intervalo,
            "acessos": acessos,
            "falhas": falhas,
            "taxa_falhas": f"{falhas / acessos:.6f}",
        })
    return linhas


def main():
    """Simula todos os traces informados e grava o CSV de resultados."""
    args = ler_argumentos()
    resultados = []
    for caminho in args.traces:
        resultados.extend(simular(caminho, args.frames, args.bits, args.intervalo))

    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    with open(args.saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(resultados)
    print(f"\nResultados salvos em {args.saida}")


if __name__ == "__main__":
    main()
