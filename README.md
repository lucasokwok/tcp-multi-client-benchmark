# tcp-multi-client-benchmark

Lucas de Oliveira Kwok - 163939

Felipe de Carvalho Frenhan - 147911

Renata -

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

## Dependências do projeto

Para compilar no Linux, instale o GCC

No Ubuntu/Debian:

```bash
sudo apt install gcc
```

No Fedora:

```bash
sudo dnf install gcc
```

## Exemplo de execução

### chat_example:

```bash
gcc -Wall -Wextra -g chat_server.c -o chat_server -pthread

gcc -Wall -Wextra -g chat_client.c -o chat_client -pthread
```

Em um terminal:

```bash
./chat_server 5000
```

Em outro terminal:

```bash
./chat_client 127.0.0.1 5000
```
