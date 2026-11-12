# tcp-multi-client-benchmark

Lucas de Oliveira Kwok - 163939

Felipe de Carvalho Frenhan - 147911

Renata Moura Barreto - 163983

Exercício UC Redes - Maximizar a taxa de transferência usando sockets TCP

Este repositório resolve o exercício proposto:

## Maximizar a taxa de transferência usando sockets TCP

Modifique a aplicação de chat TCP para avaliar sua capacidade efetiva máxima de transmissão de dados, dos clientes para o servidor.
Realize experimentos variando de 1 a 10 clientes simultâneos, medindo a taxa de transmissão agregada recebida pelo servidor em cada cenário.

### Requisitos:

Modifique o cliente e o servidor para permitir a transmissão contínua de dados durante um intervalo de tempo definido, sem a necessidade de digitação manual. Execute os experimentos com 1 a 10 clientes transmitindo simultaneamente para o servidor. Determine a taxa de transmissão, em Mbps, para cada quantidade de clientes.

### Elabore um relatório técnico contendo:

    - processador, memória RAM, sistema operacional, compilador, configuração da rede e características das máquinas utilizadas.
    - duração dos testes, quantidade de repetições, tamanho dos blocos transmitidos e procedimentos utilizados para garantir a comparabilidade dos resultados.
    - descreva como foi calculada a taxa de transmissão agregada, considerando o total de bytes efetivamente recebidos pelo servidor em diversas threads e o tempo de medição.
    - apresente tabelas, gráficos e uma discussão sobre o impacto do aumento do número de clientes na capacidade de transmissão do servidor.
    - identifique os limites observados e possíveis gargalos de desempenho.

#### Apresente, no mínimo:

    número de clientes simultâneos (1 a 10) versus throughput agregado máximo, em Mbps.

## Arquivos

| Arquivo | Descrição |
|---|---|
| `chat_server.c` | Servidor: espera N clientes, libera o envio para todos ao mesmo tempo, soma os bytes recebidos por cada thread durante o tempo do teste e imprime o throughput agregado. |
| `chat_client.c` | Cliente: envia continuamente blocos de tamanho fixo até o servidor sinalizar o fim do teste (sem digitação manual). |
| `run_benchmarks.py` | Automatiza os experimentos: compila, roda de 1 a 10 clientes com N repetições e grava `resultados/<data-hora>/resultados.csv`. |
| `analisar_resultados.py` | Lê o CSV e gera a tabela (`resumo.md`/`resumo.csv`) e o gráfico (`grafico.png`). |
| `legacy/` | Versão original do chat, antes das modificações. |

## Dependências

O código usa APIs POSIX (`pthread`, sockets BSD, `poll`), então precisa de **Linux**. No Windows, use o WSL (`wsl --install -d Ubuntu`).

No Ubuntu/Debian:

```bash
sudo apt install gcc python3 python3-matplotlib
```

No Fedora:

```bash
sudo dnf install gcc python3 python3-matplotlib
```

## Compilação

```bash
gcc -Wall -Wextra -O2 chat_server.c -o chat_server -pthread
gcc -Wall -Wextra -O2 chat_client.c -o chat_client -pthread
```

## Execução manual

```bash
./chat_server <porta> <clientes> <segundos> [bloco_bytes]
./chat_client <ip_servidor> <porta> <nome> [bloco_bytes]
```

O tamanho de bloco padrão é 65536 bytes. Exemplo com 2 clientes durante 10 segundos (3 terminais):

```bash
./chat_server 5000 2 10
./chat_client 127.0.0.1 5000 cliente1
./chat_client 127.0.0.1 5000 cliente2
```

O teste começa quando o último cliente se conecta. Ao final, o servidor imprime uma linha CSV:

```
clientes,bloco_bytes,duracao_segundos,bytes_recebidos,throughput_mbps
```

> A quantidade de clientes iniciados deve ser igual ao argumento `<clientes>` do servidor; caso contrário ele fica aguardando.

## Experimentos automatizados

```bash
python3 run_benchmarks.py [duracao] [repeticoes] [porta] [pasta_saida] [bloco_bytes]
```

Valores padrão: 30 s, 5 repetições, porta 5000, bloco de 65536 bytes. Exemplos:

```bash
python3 run_benchmarks.py 5 1     # teste rápido (~1 min)
python3 run_benchmarks.py 30 5    # rodada usada no relatório (~25 min)
```

## Tabela e gráfico

```bash
python3 analisar_resultados.py                       # rodada mais recente
python3 analisar_resultados.py resultados/<pasta>    # rodada específica
```

## Cálculo do throughput agregado

Cada thread do servidor acumula os bytes recebidos do seu cliente apenas enquanto o tempo decorrido desde o início sincronizado é menor que a duração do teste. Ao final, o servidor soma os bytes de todas as threads:

```
throughput (Mbps) = soma dos bytes recebidos × 8 / duração (s) / 1.000.000
```
