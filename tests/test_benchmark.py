#!/usr/bin/env python3
from contextlib import contextmanager
import csv
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from run_benchmarks import interrupted, stop_processes, wait_for_server


@contextmanager
def start_server(work, port, clients):
    server = subprocess.Popen([str(work / "server"), str(port), str(clients), "1"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_for_server(server)
        yield server
    finally:
        stop_processes([server])


def run_automation(port, output, repetitions):
    process = subprocess.Popen([sys.executable, str(ROOT / "run_benchmarks.py"),
                                "1", str(repetitions), str(port), str(output)])
    try:
        return process.wait(timeout=40)
    finally:
        stop_processes([process])


def read_results(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 55100
    work = Path(tempfile.mkdtemp(prefix="tcp-benchmark-tests."))
    print(f"Arquivos de validação: {work}", flush=True)
    for source, target in (("chat_server.c", "server"), ("chat_client.c", "client")):
        subprocess.run(["gcc", "-Wall", "-Wextra", "-Werror", "-O2", str(ROOT / source),
                        "-o", str(work / target), "-pthread"], check=True)

    print("Teste: contagem exata com dois clientes", flush=True)
    with start_server(work, port, 2) as server:
        clients = []
        try:
            for number in range(1, 3):
                client = socket.create_connection(("127.0.0.1", port), timeout=5)
                clients.append(client)
                client.sendall(f"cliente{number:02d}\n".encode())
            for client, size in zip(clients, (12345, 54321)):
                assert client.recv(1) == b"S"
                client.sendall(b"A" * size)
            for client in clients:
                assert client.recv(1) == b"E"
        finally:
            for client in clients:
                client.close()
        result, errors = server.communicate(timeout=5)
        assert server.returncode == 0, errors
        assert result.strip() == "2,1024,1.000000,66666,0.533328"
        for name in ("cliente01", "cliente02"):
            assert f"Usuario conectado: {name}" in errors
            assert f"Usuario desconectado: {name}" in errors

    print("Teste: desconexão antecipada não produz medição", flush=True)
    with start_server(work, port, 1) as server:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.sendall(b"cliente01\n")
            assert client.recv(1) == b"S"
            client.sendall(b"teste")
        result, errors = server.communicate(timeout=5)
        assert server.returncode != 0 and result == ""
        assert errors.strip()

    print("Teste: 1 a 10 clientes, com duas repetições", flush=True)
    assert run_automation(port, work / "bateria", 2) == 0
    rows = read_results(work / "bateria" / "resultados.csv")
    assert len(rows) == 20
    assert {(int(row["repeticao"]), int(row["clientes"])) for row in rows} == {
        (repetition, clients) for repetition in (1, 2) for clients in range(1, 11)}
    for row in rows:
        assert len(row) == 6 and int(row["bloco_bytes"]) == 1024
        assert float(row["duracao_segundos"]) == 1
        assert int(row["bytes_recebidos"]) > 0 and float(row["throughput_mbps"]) > 0

    print("Teste: erro interrompe a bateria sem preencher o CSV", flush=True)
    with start_server(work, port, 1) as server:
        assert run_automation(port, work / "porta-ocupada", 1) != 0
        assert read_results(work / "porta-ocupada" / "resultados.csv") == []
        assert server.poll() is None
    print("Testes concluídos.")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
