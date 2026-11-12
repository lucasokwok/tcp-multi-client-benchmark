#!/usr/bin/env python3
import csv
from datetime import datetime
from pathlib import Path
import select
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def stop_processes(processes):
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait()


def wait_for_server(server):
    if not select.select([server.stderr], [], [], 10)[0]:
        raise TimeoutError("Servidor não iniciou em 10 segundos.")
    message = server.stderr.readline().strip()
    if message != "READY":
        raise RuntimeError(f"Erro ao iniciar servidor: {message}")


def run_scenario(port, clients, duration):
    processes = []
    try:
        server = subprocess.Popen(
            [str(ROOT / "chat_server"), str(port), str(clients), str(duration)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(server)
        wait_for_server(server)

        for number in range(1, clients + 1):
            client = subprocess.Popen([str(ROOT / "chat_client"), "127.0.0.1", str(port)],
                                       stdin=subprocess.PIPE, text=True)
            processes.append(client)
            # o nome eh passado pela entrada do terminal
            client.stdin.write(f"cliente{number:02d}\n")
            client.stdin.close()

        result, errors = server.communicate(timeout=duration + 10)
        if server.returncode != 0:
            raise RuntimeError(f"Erro no servidor: {errors.strip()}")
        for client in processes[1:]:
            if client.wait(timeout=5) != 0:
                raise RuntimeError("Um cliente encerrou com erro.")
        if not result.strip():
            raise RuntimeError("Servidor não retornou uma medição.")
        return next(csv.reader(result.splitlines()))
    finally:
        stop_processes(processes)


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    repetitions = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    output = ROOT / sys.argv[4] if len(sys.argv) > 4 else (
        ROOT / "resultados" / datetime.now().strftime("%Y%m%d-%H%M%S-%f"))

    for name in ("chat_server", "chat_client"):
        subprocess.run(["gcc", "-Wall", "-Wextra", "-O2", str(ROOT / f"{name}.c"),
                        "-o", str(ROOT / name), "-pthread"], check=True)

    output.mkdir(parents=True, exist_ok=True)
    with (output / "resultados.csv").open("x", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["repeticao", "clientes", "bloco_bytes", "duracao_segundos",
                         "bytes_recebidos", "throughput_mbps"])
        file.flush()
        # repete cada teste variando de 1 a 10 clientes
        for clients in range(1, 11):
            for repetition in range(1, repetitions + 1):
                print(f"Clientes: {clients}; repetição: {repetition}/{repetitions}", flush=True)
                row = run_scenario(port, clients, duration)
                # grava a medicao recebida do servidor
                writer.writerow([repetition, *row])
                file.flush()
    print(f"Resultados: {output / 'resultados.csv'}")


def interrupted(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        print("Execução interrompida.", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
