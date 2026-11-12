
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define BUFFER_SIZE 1024

int sockfd;
// pthread_mutex_t output_mutex = PTHREAD_MUTEX_INITIALIZER;

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

// void *receive_messages(void *arg) {
//     char buffer[BUFFER_SIZE];
//     size_t pos = 0;

//     (void)arg;

//     while (1) {
//         char c;
//         ssize_t n = recv(sockfd, &c, 1, 0);

//         if (n == 0) {
//             pthread_mutex_lock(&output_mutex);
//             printf("\nConexao encerrada pelo servidor.\n");
//             fflush(stdout);
//             pthread_mutex_unlock(&output_mutex);
//             break;
//         }

//         if (n == -1) {
//             if (errno == EINTR)
//                 continue;

//             pthread_mutex_lock(&output_mutex);
//             perror("recv");
//             pthread_mutex_unlock(&output_mutex);
//             break;
//         }

//         if (c == '\n') {
//             buffer[pos] = '\0';

//             pthread_mutex_lock(&output_mutex);
//             printf("\r%s\n", buffer);
//             fflush(stdout);
//             pthread_mutex_unlock(&output_mutex);

//             pos = 0;
//         } else if (c != '\r') {
//             if (pos < sizeof(buffer) - 1)
//                 buffer[pos++] = c;
//         }
//     }

//     return NULL;
// }

int main(int argc, char *argv[]) {
    struct sockaddr_in server_addr;
    char name[32];
    // a mensagem eh fixa para retirar a parte da digitacao
    char buffer[BUFFER_SIZE] = "Mensagem padrao de teste TCP.\n";
    char command;

    if (argc != 3) {
        fprintf(stderr, "Uso: %s <IP> <porta>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int port = atoi(argv[2]);

    signal(SIGPIPE, SIG_IGN);

    sockfd = socket(AF_INET, SOCK_STREAM, 0);

    if (sockfd == -1) {
        perror("socket");
        return EXIT_FAILURE;
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    if (inet_pton(AF_INET, argv[1],
                  &server_addr.sin_addr) != 1) {
        fprintf(stderr, "Endereco IPv4 invalido.\n");
        close(sockfd);
        return EXIT_FAILURE;
    }

    if (connect(sockfd, (struct sockaddr *)&server_addr,
                sizeof(server_addr)) == -1) {
        perror("connect");
        close(sockfd);
        return EXIT_FAILURE;
    }

    printf("Seu nome: ");

    if (fgets(name, sizeof(name), stdin) == NULL) {
        close(sockfd);
        return EXIT_FAILURE;
    }

    name[strcspn(name, "\r\n")] = '\0';

    if (name[0] == '\0' ||
        strchr(name, '\n') != NULL) {
        fprintf(stderr, "Nome invalido.\n");
        close(sockfd);
        return EXIT_FAILURE;
    }

    if (send_all(sockfd, name, strlen(name)) == -1 ||
        send_all(sockfd, "\n", 1) == -1) {
        perror("send");
        close(sockfd);
        return EXIT_FAILURE;
    }

    // aguarda todos os clientes ficarem prontos para enviar
    if (recv(sockfd, &command, 1, 0) != 1 || command != 'S') {
        fprintf(stderr, "Erro aguardando o inicio do teste.\n");
        close(sockfd);
        return EXIT_FAILURE;
    }

    struct pollfd server = {.fd = sockfd, .events = POLLIN};
    while (1) {
        int ready = poll(&server, 1, 0);
        if (ready == -1) {
            perror("poll");
            close(sockfd);
            return EXIT_FAILURE;
        }
        if (ready > 0) {
            if (recv(sockfd, &command, 1, 0) != 1 || command != 'E') {
                fprintf(stderr, "Erro aguardando o fim do teste.\n");
                close(sockfd);
                return EXIT_FAILURE;
            }
            break;
        }

        // repete o bloco ate receber o sinal de parada
        if (send_all(sockfd, buffer, sizeof(buffer)) == -1) {
            perror("send");
            close(sockfd);
            return EXIT_FAILURE;
        }
    }

    close(sockfd);

    return EXIT_SUCCESS;
}
