"""Gera os gráficos a partir do CSV produzido por main.py.

Há dois tipos de gráfico, um arquivo PNG por trace:

- padrão: falhas de página por número de frames, com uma linha por
  algoritmo (``<trace>.png``);
- ``--sensibilidade``: falhas do LRU aproximado em função do intervalo T,
  com uma linha por valor de N e um painel por número de frames; o OPT e o
  LRU exato aparecem como linhas tracejadas de referência
  (``<trace>_sensibilidade.png``).

Exemplos:
    python src/graficos.py resultados/resultados.csv
    python src/graficos.py resultados/sensibilidade.csv --sensibilidade
"""

import argparse
import csv
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, ScalarFormatter  # noqa: E402


def ler_argumentos():
    """Define e interpreta os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="CSV gerado por main.py")
    parser.add_argument("--sensibilidade", action="store_true",
                        help="gera os gráficos de sensibilidade do LRU aproximado a N e T")
    parser.add_argument("--pasta", default="resultados", help="pasta onde salvar os PNGs (padrão: %(default)s)")
    return parser.parse_args()


def ler_csv(caminho):
    """Lê o CSV de resultados, agrupando as linhas por trace.

    Returns:
        Dicionário ``trace -> lista de linhas``, em que cada linha é um
        dicionário com os campos do CSV.
    """
    por_trace = defaultdict(list)
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            por_trace[linha["trace"]].append(linha)
    return por_trace


# Eixo Y com separador de milhar (1.000.000) em vez de notação científica
FORMATO_MILHAR = FuncFormatter(lambda valor, _: f"{valor:,.0f}".replace(",", "."))


def nome_base(trace):
    """Remove as extensões do nome do trace (``gcc.trace.txt`` vira ``gcc``)."""
    return os.path.basename(trace).split(".")[0]


def rotulo(linha):
    """Texto da legenda de uma série, com N e T no caso do LRU aproximado."""
    if linha["bits"]:
        return f"{linha['algoritmo']} (N={linha['bits']}, T={linha['intervalo']})"
    return linha["algoritmo"]


def grafico_por_frames(trace, linhas, pasta):
    """Desenha falhas por número de frames, uma linha por algoritmo.

    O eixo X usa escala logarítmica de base 2, para que os valores pequenos
    (4 a 32 frames) e grandes (64 a 256) fiquem legíveis no mesmo gráfico.

    Returns:
        Caminho do PNG gerado.
    """
    series = defaultdict(list)
    for linha in linhas:
        series[rotulo(linha)].append((int(linha["frames"]), int(linha["falhas"])))

    figura, eixo = plt.subplots(figsize=(9, 5.5))
    for nome, pontos in series.items():
        pontos.sort()
        eixo.plot([f for f, _ in pontos], [q for _, q in pontos], marker="o", label=nome)
    eixo.set_xscale("log", base=2)
    eixo.set_xticks(sorted({int(linha["frames"]) for linha in linhas}))
    eixo.get_xaxis().set_major_formatter(ScalarFormatter())
    eixo.set_title(f"Falhas de página: {nome_base(trace)}")
    eixo.set_xlabel("Número de frames")
    eixo.set_ylabel("Falhas de página")
    eixo.yaxis.set_major_formatter(FORMATO_MILHAR)
    eixo.grid(True, alpha=0.3)
    eixo.legend()
    return salvar(figura, pasta, f"{nome_base(trace)}.png")


def grafico_sensibilidade(trace, linhas, pasta):
    """Desenha as falhas do LRU aproximado em função de T, um painel por número de frames.

    Em cada painel, há uma linha por valor de N e linhas horizontais
    tracejadas com o resultado do LRU exato e do OPT para a mesma quantidade
    de frames, que servem de referência.

    Returns:
        Caminho do PNG gerado.
    """
    lista_frames = sorted({int(linha["frames"]) for linha in linhas})
    figura, eixos = plt.subplots(1, len(lista_frames), figsize=(5 * len(lista_frames), 4.5), squeeze=False)
    for eixo, frames in zip(eixos[0], lista_frames):
        do_painel = [linha for linha in linhas if int(linha["frames"]) == frames]
        por_bits = defaultdict(list)
        for linha in do_painel:
            if linha["bits"]:
                por_bits[int(linha["bits"])].append((int(linha["intervalo"]), int(linha["falhas"])))
            else:
                estilo = {"OPT": ":", "LRU": "--"}[linha["algoritmo"]]
                eixo.axhline(int(linha["falhas"]), color="gray", linestyle=estilo, label=linha["algoritmo"])
        for bits in sorted(por_bits):
            pontos = sorted(por_bits[bits])
            eixo.plot([t for t, _ in pontos], [q for _, q in pontos], marker="o", label=f"N={bits}")
        eixo.set_xscale("log")
        eixo.set_title(f"{frames} frames")
        eixo.set_xlabel("Intervalo T (acessos)")
        eixo.yaxis.set_major_formatter(FORMATO_MILHAR)
        eixo.grid(True, alpha=0.3)
    eixos[0][0].set_ylabel("Falhas de página")
    eixos[0][-1].legend()
    figura.suptitle(f"Sensibilidade do LRU aproximado a N e T: {nome_base(trace)}")
    return salvar(figura, pasta, f"{nome_base(trace)}_sensibilidade.png")


def salvar(figura, pasta, nome_arquivo):
    """Salva a figura em PNG e libera a memória do matplotlib."""
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, nome_arquivo)
    figura.tight_layout()
    figura.savefig(destino, dpi=150)
    plt.close(figura)
    return destino


def main():
    """Gera um gráfico por trace presente no CSV."""
    args = ler_argumentos()
    desenhar = grafico_sensibilidade if args.sensibilidade else grafico_por_frames
    for trace, linhas in ler_csv(args.csv).items():
        print(f"Gráfico salvo em {desenhar(trace, linhas, args.pasta)}")


if __name__ == "__main__":
    main()
