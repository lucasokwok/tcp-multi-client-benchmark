#!/usr/bin/env python3
"""Gera a tabela e o grafico do relatorio a partir do resultados.csv.

Uso:
    python3 analisar_resultados.py                      # usa a rodada mais recente em resultados/
    python3 analisar_resultados.py resultados/<pasta>   # usa uma rodada especifica

Arquivos gerados na mesma pasta do CSV:
    resumo.csv   -> tabela por numero de clientes (para planilha)
    resumo.md    -> mesma tabela em Markdown (para colar no relatorio)
    grafico.png  -> clientes x throughput agregado (Mbps)
"""
import csv
from pathlib import Path
import statistics
import sys

import matplotlib

matplotlib.use("Agg")  # gera a imagem sem abrir janela
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent

# cores e tons de texto do grafico
AZUL = "#2a78d6"
LARANJA = "#eb6834"
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
GRADE = "#e4e3df"


def escolher_pasta():
    if len(sys.argv) > 1:
        pasta = Path(sys.argv[1])
        if not pasta.is_absolute():
            pasta = ROOT / pasta
        return pasta
    rodadas = sorted(p for p in (ROOT / "resultados").glob("*") if (p / "resultados.csv").is_file())
    if not rodadas:
        raise FileNotFoundError("Nenhum resultados.csv encontrado em resultados/.")
    return rodadas[-1]


def ler_medicoes(arquivo):
    # agrupa o throughput (Mbps) de cada repeticao pelo numero de clientes
    por_clientes = {}
    bloco = duracao = None
    with arquivo.open(newline="") as f:
        for linha in csv.DictReader(f):
            clientes = int(linha["clientes"])
            por_clientes.setdefault(clientes, []).append(float(linha["throughput_mbps"]))
            bloco = int(linha["bloco_bytes"])
            duracao = float(linha["duracao_segundos"])
    if not por_clientes:
        raise ValueError(f"{arquivo} nao tem medicoes.")
    return por_clientes, bloco, duracao


def resumir(por_clientes):
    linhas = []
    for clientes in sorted(por_clientes):
        valores = por_clientes[clientes]
        media = statistics.mean(valores)
        desvio = statistics.stdev(valores) if len(valores) > 1 else 0.0
        linhas.append({
            "clientes": clientes,
            "repeticoes": len(valores),
            "media_mbps": media,
            "desvio_mbps": desvio,
            "minimo_mbps": min(valores),
            "maximo_mbps": max(valores),
            "media_por_cliente_mbps": media / clientes,
        })
    return linhas


def salvar_csv(linhas, destino):
    with destino.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(linhas[0]))
        writer.writeheader()
        for linha in linhas:
            writer.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in linha.items()})


def numero_br(valor):
    # 12345.6 -> "12.345,6"
    return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def salvar_markdown(linhas, destino, bloco, duracao):
    texto = [
        f"Bloco: {bloco} bytes | Duracao de cada teste: {duracao:g} s | "
        f"Repeticoes por cenario: {linhas[0]['repeticoes']}",
        "",
        "| Clientes | Média (Mbps) | Desvio padrão (Mbps) | Mínimo (Mbps) | Máximo (Mbps) | Média por cliente (Mbps) |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for l in linhas:
        texto.append(
            f"| {l['clientes']} | {numero_br(l['media_mbps'])} | {numero_br(l['desvio_mbps'])} | "
            f"{numero_br(l['minimo_mbps'])} | {numero_br(l['maximo_mbps'])} | "
            f"{numero_br(l['media_por_cliente_mbps'])} |"
        )
    destino.write_text("\n".join(texto) + "\n", encoding="utf-8")


def salvar_grafico(linhas, destino, bloco, duracao):
    clientes = [l["clientes"] for l in linhas]
    # converte para Gbps so no grafico, para os numeros ficarem legiveis
    media = [l["media_mbps"] / 1000 for l in linhas]
    desvio = [l["desvio_mbps"] / 1000 for l in linhas]
    maximo = [l["maximo_mbps"] / 1000 for l in linhas]

    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    fig.patch.set_facecolor("white")

    ax.errorbar(clientes, media, yerr=desvio, color=AZUL, linewidth=2, marker="o",
                markersize=7, capsize=4, elinewidth=1.2, label="Média ± desvio padrão", zorder=3)
    ax.plot(clientes, maximo, color=LARANJA, linewidth=0, marker="D", markersize=7,
            markeredgecolor="white", markeredgewidth=1.5, label="Máximo observado", zorder=4)

    # destaca o melhor cenario (maior media)
    melhor = max(linhas, key=lambda l: l["media_mbps"])
    ax.annotate(f"pico: {numero_br(melhor['media_mbps'] / 1000)} Gbps",
                xy=(melhor["clientes"], melhor["media_mbps"] / 1000),
                xytext=(0, 14), textcoords="offset points", ha="center",
                fontsize=9, color=TEXTO)

    ax.set_title("Throughput agregado recebido pelo servidor × número de clientes",
                 fontsize=12, color=TEXTO, loc="left", pad=22)
    repeticoes = linhas[0]["repeticoes"]
    ax.text(0, 1.02, f"Bloco de {bloco} bytes · {duracao:g} s por teste · "
            f"{repeticoes} {'repetição' if repeticoes == 1 else 'repetições'} por cenário",
            transform=ax.transAxes, fontsize=9, color=TEXTO_SECUNDARIO)
    ax.set_xlabel("Clientes simultâneos", color=TEXTO_SECUNDARIO)
    ax.set_ylabel("Throughput agregado (Gbps)", color=TEXTO_SECUNDARIO)
    ax.set_xticks(clientes)
    ax.set_ylim(bottom=0, top=max(maximo) * 1.15)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))

    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRADE)
    ax.tick_params(colors=TEXTO_SECUNDARIO)
    ax.legend(frameon=False, loc="lower right", fontsize=9)

    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def main():
    pasta = escolher_pasta()
    por_clientes, bloco, duracao = ler_medicoes(pasta / "resultados.csv")
    linhas = resumir(por_clientes)

    salvar_csv(linhas, pasta / "resumo.csv")
    salvar_markdown(linhas, pasta / "resumo.md", bloco, duracao)
    salvar_grafico(linhas, pasta / "grafico.png", bloco, duracao)

    print((pasta / "resumo.md").read_text(encoding="utf-8"))
    print(f"Arquivos gerados em: {pasta}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as erro:
        print(erro, file=sys.stderr)
        sys.exit(1)
