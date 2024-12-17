/*
 * Copyright (C) 2019 Intel Corporation.  All rights reserved.
 * SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 */
#include "socket_utils.h"

#include "sqlite3.h"

#include <math.h>

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#ifdef __wasi__
#include <wasi_socket_ext.h>
#endif

    //////////////////
    //    SERVER    //
    //////////////////

bool DEBUG = false;

struct args {
    int socket;
};

void *
run(void *arg)
{
    sqlite3 *db;
    int rc = sqlite3_open("test.db", &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 0;
    }
    int new_socket = ((struct args *) arg)->socket;
    free(arg);

    int batch_num;
    char buffer[20];
    int bytes_read;
    char *errmsg = NULL;

    if(DEBUG){
        printf("[Server] Communicate with the new connection #%u @ %p ..\n",
                new_socket, (void *)(uintptr_t)pthread_self());
        fflush(stdout);
    }

    bytes_read = read(new_socket, buffer, sizeof(buffer));
    while (bytes_read > 0){

        // execute sql command
        char *result = NULL;
        int rc = sqlite3_exec(db, buffer, NULL, NULL, &errmsg);
        if (rc != SQLITE_OK) {
            result = errmsg;
            sqlite3_free(errmsg);
        } else {
            result = "SQL command executed successfully.\n";
        }

        bytes_read = read(new_socket, buffer, 4);
    }
    
    if (bytes_read != 0) {
        perror("Read error");
    }
    else if(DEBUG){
        printf("Client disconnected.\n");
        fflush(stdout);
    }

    if(DEBUG){
        printf("[Server] Shutting down the new connection #%u ..\n", new_socket);
        fflush(stdout);
    }
    shutdown(new_socket, SHUT_RDWR);
    if (new_socket >= 0)
        close(new_socket);

    return NULL;
}

static void
init_sockaddr_inet(struct sockaddr_in *addr)
{
    /* 0.0.0.0:1234 */
    addr->sin_family = AF_INET;
    addr->sin_port = htons(1234);
    addr->sin_addr.s_addr = htonl(INADDR_ANY);
}

static void
init_sockaddr_inet6(struct sockaddr_in6 *addr)
{
    /* [::]:1234 */
    addr->sin6_family = AF_INET6;
    addr->sin6_port = htons(1234);
    addr->sin6_addr = in6addr_any;
}

int
main(int argc, char *argv[])
{
        //////////
        //SERVER//
        //////////

    int socket_fd = -1, addrlen = 0, af;
    struct sockaddr_storage addr = { 0 };
    char ip_string[64];

    if (argc > 1 && strcmp(argv[1], "inet6") == 0) {
        af = AF_INET6;
        addrlen = sizeof(struct sockaddr_in6);
        init_sockaddr_inet6((struct sockaddr_in6 *)&addr);
    } else {
        af = AF_INET;
        addrlen = sizeof(struct sockaddr_in6);
        init_sockaddr_inet((struct sockaddr_in *)&addr);
    }

    if(DEBUG){
        printf("[Server] Create socket\n");
        fflush(stdout);
    }
    socket_fd = socket(af, SOCK_STREAM, 0);
    if (socket_fd < 0) {
        perror("Create socket failed");
        goto fail;
    }

    int optval = 1;
    socklen_t optlen = sizeof(optval);
    if (setsockopt(socket_fd, SOL_SOCKET, SO_REUSEADDR, &optval, optlen) < 0) {
        perror("Error setting socket options");
        goto fail;
    }

    if(DEBUG){
        printf("[Server] Bind socket\n");
        fflush(stdout);
    }
    if (bind(socket_fd, (struct sockaddr *)&addr, addrlen) < 0) {
        perror("Bind failed");
        goto fail;
    }

    if(DEBUG){
        printf("[Server] Listening on socket\n");
        fflush(stdout);
    }
    if (listen(socket_fd, 128) < 0) {
        perror("Listen failed");
        goto fail;
    }

    int client_socket;
    struct args *arguments;
    if(DEBUG){
        printf("[Server] Wait for clients to connect ..\n");
        fflush(stdout);
    }
    while (true) {
        addrlen = sizeof(struct sockaddr);
        client_socket =
            accept(socket_fd, (struct sockaddr *)&addr, (socklen_t *)&addrlen);
        if (client_socket < 0) {
            perror("Accept failed");
            break;
        }

        if (sockaddr_to_string((struct sockaddr *)&addr, ip_string,
                               sizeof(ip_string) / sizeof(ip_string[0]))
            != 0) {
            printf("[Server] failed to parse client address\n");
            fflush(stdout);
            goto fail;
        }

        arguments = (struct args *)malloc(sizeof(struct args));
        arguments->socket = client_socket;
        pthread_t thread_id;
        if(DEBUG){
            printf("[Server] Client connected (%s)\n", ip_string);
            fflush(stdout);
        }
        if (pthread_create(&thread_id, NULL, run,
                           arguments)) {
            perror("Create a worker thread failed");
            free(arguments);
            shutdown(client_socket, SHUT_RDWR);
            if (client_socket >= 0)
                close(client_socket);
            break;
        }
        pthread_detach(thread_id);
    }

    // Cleanup

    printf("[Server] Shutting down ..\n");
    fflush(stdout);
    shutdown(socket_fd, SHUT_RDWR);
    if (socket_fd >= 0)
        close(socket_fd);
    sleep(3);
    printf("[Server] BYE \n");
    fflush(stdout);
    return EXIT_SUCCESS;

fail:

    printf("[Server] Shutting down ..\n");
    fflush(stdout);
    if (socket_fd >= 0)
        close(socket_fd);
    sleep(3);
    return EXIT_FAILURE;
}
