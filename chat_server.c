// #define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define BUFFER_SIZE 1024
#define MAX_CLIENTS 100

typedef struct Client {
    int fd;
    char name[32];
    struct Client *next;
    pthread_t thread;
    unsigned long long bytes;
    int failed;
} Client;

Client *clients = NULL;
int num_clients = 0;

pthread_mutex_t clients_mutex = PTHREAD_MUTEX_INITIALIZER;

int duration;
struct timespec start_time;
pthread_barrier_t start_barrier;

int send_all(int fd, const char *data, size_t len) {
    size_t sent = 0;

    while (sent < len) {
        ssize_t n = send(fd, data + sent, len - sent,
                         MSG_NOSIGNAL);

        if (n == -1) {
            if (errno == EINTR)
                continue;
            return -1;
        }

        if (n == 0)
            return -1;

        sent += (size_t)n;
    }

    return 0;
}

/* Le uma linha terminada por '\n'. */
ssize_t read_line(int fd, char *buffer, size_t capacity) {
    size_t pos = 0;

    while (pos < capacity - 1) {
        char c;
        ssize_t n = recv(fd, &c, 1, 0);

        if (n == 0)
            return pos == 0 ? 0 : (ssize_t)pos;

        if (n == -1) {
            if (errno == EINTR)
                continue;
            return -1;
        }

        if (c == '\n')
            break;

        if (c != '\r')
            buffer[pos++] = c;
    }

    buffer[pos] = '\0';
    return (ssize_t)pos;
}

// /* Distribui uma mensagem aos demais clientes. */
// void broadcast(const char *message, Client *sender) {
//     pthread_mutex_lock(&clients_mutex);

//     Client *current = clients;

//     while (current != NULL) {
//         if (current != sender) {
//             if (send_all(current->fd, message,
//                          strlen(message)) == -1) {
//                 fprintf(stderr,
//                         "Falha ao enviar para %s.\n",
//                         current->name);
//             }
//         }

//         current = current->next;
//     }

//     pthread_mutex_unlock(&clients_mutex);
// }

double elapsed_seconds(struct timespec now) {
    return (double)(now.tv_sec - start_time.tv_sec)
        + (double)(now.tv_nsec - start_time.tv_nsec) / 1000000000.0;
}

void *handle_client(void *arg) {
    Client *client = arg;
    char buffer[BUFFER_SIZE];
    struct timespec now;

    if (read_line(client->fd, client->name, sizeof(client->name)) <= 0) {
        fprintf(stderr, "Erro recebendo o nome do cliente.\n");
        exit(EXIT_FAILURE);
    }

    pthread_mutex_lock(&clients_mutex);

    if (num_clients >= MAX_CLIENTS) {
        fprintf(stderr, "Servidor cheio.\n");
        exit(EXIT_FAILURE);
    }

    client->next = clients;
    clients = client;
    num_clients++;

    pthread_mutex_unlock(&clients_mutex);

    fprintf(stderr, "Usuario conectado: %s\n", client->name);

    // A primeira barreira prepara as threads; a segunda libera o envio.
    pthread_barrier_wait(&start_barrier);
    pthread_barrier_wait(&start_barrier);

    if (send_all(client->fd, "S", 1) == -1) {
        perror("send inicio");
        client->failed = 1;
        return NULL;
    }

    while (1) {
        ssize_t n = recv(client->fd, buffer, sizeof(buffer), 0);
        if (n == -1 && errno == EINTR)
            continue;
        clock_gettime(CLOCK_MONOTONIC, &now);
        if (n == -1) {
            perror("recv");
            client->failed = 1;
            break;
        }
        if (n == 0) {
            if (elapsed_seconds(now) < duration) {
                fprintf(stderr, "Cliente %s desconectou antes do fim do teste.\n", client->name);
                client->failed = 1;
            }
            break;
        }
        if (elapsed_seconds(now) < duration)
            client->bytes += (unsigned long long)n;
    }

    return NULL;
}

int main(int argc, char *argv[]) {
    int server_fd;
    struct sockaddr_in server_addr;

    if (argc != 4) {
        fprintf(stderr, "Uso: %s <porta> <clientes> <segundos>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int port = atoi(argv[1]);
    int expected_clients = atoi(argv[2]);
    duration = atoi(argv[3]);

    signal(SIGPIPE, SIG_IGN);

    server_fd = socket(AF_INET, SOCK_STREAM, 0);

    if (server_fd == -1) {
        perror("socket");
        return EXIT_FAILURE;
    }

    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR,
                   &opt, sizeof(opt)) == -1) {
        perror("setsockopt");
        close(server_fd);
        return EXIT_FAILURE;
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr *)&server_addr,
             sizeof(server_addr)) == -1
        || listen(server_fd, 10) == -1) {
        perror("bind/listen");
        close(server_fd);
        return EXIT_FAILURE;
    }
    if (pthread_barrier_init(&start_barrier, NULL, expected_clients + 1) != 0) {
        fprintf(stderr, "Erro criando a barreira de inicio.\n");
        close(server_fd);
        return EXIT_FAILURE;
    }
    fprintf(stderr, "READY\n");

    for (int i = 0; i < expected_clients; i++) {
        int client_fd = accept(
            server_fd,
            NULL,
            NULL
        );

        if (client_fd == -1) {
            perror("accept");
            close(server_fd);
            return EXIT_FAILURE;
        }

        Client *client = malloc(sizeof(Client));

        if (client == NULL) {
            perror("malloc");
            close(client_fd);
            close(server_fd);
            return EXIT_FAILURE;
        }

        client->fd = client_fd;
        client->name[0] = '\0';
        client->next = NULL;

        client->bytes = 0;
        client->failed = 0;

        if (pthread_create(&client->thread, NULL,
                           handle_client, client) != 0) {
            fprintf(stderr, "Erro criando a thread do cliente.\n");
            close(client_fd);
            free(client);
            close(server_fd);
            return EXIT_FAILURE;
        }
    }

    pthread_barrier_wait(&start_barrier);
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    struct timespec end_time = start_time;
    end_time.tv_sec += duration;
    pthread_barrier_wait(&start_barrier);

    if (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &end_time, NULL) != 0) {
        fprintf(stderr, "Erro aguardando o fim do teste.\n");
        return EXIT_FAILURE;
    }
    Client *current = clients;
    while (current != NULL) {
        if (send_all(current->fd, "E", 1) == -1) {
            perror("send fim");
            return EXIT_FAILURE;
        }
        current = current->next;
    }

    unsigned long long total_bytes = 0;
    int failed = 0;
    while (clients != NULL) {
        Client *client = clients;
        pthread_join(client->thread, NULL);
        total_bytes += client->bytes;
        failed |= client->failed;
        close(client->fd);
        fprintf(stderr, "Usuario desconectado: %s\n", client->name);
        clients = client->next;
        free(client);
        num_clients--;
    }

    close(server_fd);
    pthread_barrier_destroy(&start_barrier);
    pthread_mutex_destroy(&clients_mutex);
    if (failed)
        return EXIT_FAILURE;

    double seconds = elapsed_seconds(end_time);
    double mbps = (double)total_bytes * 8 / seconds / 1000000;
    printf("%d,%d,%.6f,%llu,%.6f\n", expected_clients, BUFFER_SIZE, seconds, total_bytes, mbps);

    return EXIT_SUCCESS;
}
