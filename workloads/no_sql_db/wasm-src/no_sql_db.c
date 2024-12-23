#include "socket_utils.h"

#include "dbapi.h"
#include "indexapi.h"
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

    //////////////////
    //    WORLOAD    //
    //////////////////

#define DB_SIZE 10000000
#define RECORDS_NUMBER 30
const int rec_values[] = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100};

// writing the records
void run0(void* db, int value, int* result) {
    int i = 0;
    for(i = 0; i < RECORDS_NUMBER; i++) {
        void* rec = wg_create_record(db, 1);
        if (!rec) { 
            printf("record creation failed \n"); exit(0);
            break;
        }
        wg_set_new_field(db,rec,0,wg_encode_int(db,value)); // setting 0 field of the record
    }
    *result = i;
}

// counting the records
void run1(void* db, int value, int* result) {
    int count = 0;
    void* rec = wg_find_record_int(db, 0, WG_COND_EQUAL, value, NULL);
    while(rec) {
        count++;
        rec = wg_find_record_int(db, 0, WG_COND_EQUAL, value, rec);
    }
    *result = count;
}


void work(void* db, int index, int value, int* result) {
    if (index == 0) {
        run0(db, value, result);
    }
    else if (index == 1) {
        return run1(db, value, result);
    }
    else {
        perror("Work for index %d doesn't exist! Running run0...\n");;
        return run0(db, value, result);
    }
}

struct args {
    int socket;
    void* db;
};

void *
run(void *arg)
{
    int new_socket = ((struct args *) arg)->socket;
    void * db = ((struct args *) arg)->db;
    free(arg);

    char buffer[2];
    int bytes_read;

    if(DEBUG){
        printf("[Server] Communicate with the new connection #%u @ %p ..\n",
                new_socket, (void *)(uintptr_t)pthread_self());
        fflush(stdout);
    }

    bytes_read = read(new_socket, buffer, sizeof(buffer));
    while (bytes_read > 0){
        
        char arg1[] = {buffer[0], '\0'};
        char arg2[] = {buffer[1], '\0'};

        int work_index  = atoi(arg1);
        int value_index = atoi(arg2);

        if (value_index < 0 || value_index > 9) {
            perror("Value Index is incorrect!");
            break;
        }

        int value = rec_values[value_index];
        int result = 0;
        work(db, work_index, value, &result);

        if(write(new_socket, &result, sizeof(result)) < 0){
            perror("Write error");
        }
        else if(DEBUG){
            printf("Buffer sent (%d):", result);
            printf("\n");
            fflush(stdout);
        }
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

void fill_db(void* db) {

    const int rec_num[] = {100, 300, 500, 700, 900, 1000, 200, 400, 500, 1000};

    for (int n = 0; n < 10; ++n) {
        int num = rec_num[n];
            for(int i = 0; i < num; i++) {
            void* rec = wg_create_record(db, 1);
            if (!rec) { 
                printf("record creation failed \n"); 
                exit(0);
                break;
            }
            wg_set_new_field(db,rec,0,wg_encode_int(db,rec_values[n])); // setting 0 field of the record
        }
    }
}

int
main(int argc, char *argv[])
{
    void *db;
    char *name="12";
    db = wg_attach_database(name, DB_SIZE);
    if (!db) { 
        printf("db creation failed \n");
        goto fail; 
    }
    fill_db(db);

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
    }
    else {
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
        arguments->db = db;
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
    wg_detach_database(db);
    wg_delete_database(name);


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
    // Cleanup
    wg_detach_database(db);
    wg_delete_database(name);


    printf("[Server] Shutting down ..\n");
    fflush(stdout);
    if (socket_fd >= 0)
        close(socket_fd);
    sleep(3);
    return EXIT_FAILURE;
}
