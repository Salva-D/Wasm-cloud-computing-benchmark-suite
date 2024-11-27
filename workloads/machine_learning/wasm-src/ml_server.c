/*
 * Copyright (C) 2019 Intel Corporation.  All rights reserved.
 * SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 */
#include "socket_utils.h"

#include "include/mnist_file.h"
#include "include/neural_network.h"
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


    /////////////////
    //    MNIST    //
    /////////////////


//-----------------mnist.c

#define BATCH_SIZE 20 //Must divide the dataset size (10000)!

/**
 * Downloaded from: http://yann.lecun.com/exdb/mnist/
 */
const char * test_images_file = "data/t10k-images-idx3-ubyte";

//-----------------mnist_file.c
/**
 * Convert from the big endian format in the dataset if we're on a little endian
 * machine.
 */
uint32_t map_uint32(uint32_t in)
{
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    return (
        ((in & 0xFF000000) >> 24) |
        ((in & 0x00FF0000) >>  8) |
        ((in & 0x0000FF00) <<  8) |
        ((in & 0x000000FF) << 24)
    );
#else
    return in;
#endif
}

/**
 * Read images from file.
 * 
 * File format: http://yann.lecun.com/exdb/mnist/
 */
mnist_image_t * get_images(const char * path, uint32_t * number_of_images)
{
    FILE * stream;
    mnist_image_file_header_t header;
    mnist_image_t * images;

    stream = fopen(path, "rb");

    if (NULL == stream) {
        fprintf(stderr, "Could not open file: %s\n", path);
        return NULL;
    }

    if (1 != fread(&header, sizeof(mnist_image_file_header_t), 1, stream)) {
        fprintf(stderr, "Could not read image file header from: %s\n", path);
        fclose(stream);
        return NULL;
    }

    header.magic_number = map_uint32(header.magic_number);
    header.number_of_images = map_uint32(header.number_of_images);
    header.number_of_rows = map_uint32(header.number_of_rows);
    header.number_of_columns = map_uint32(header.number_of_columns);

    if (MNIST_IMAGE_MAGIC != header.magic_number) {
        fprintf(stderr, "Invalid header read from image file: %s (%08X not %08X)\n", path, header.magic_number, MNIST_IMAGE_MAGIC);
        fclose(stream);
        return NULL;
    }

    if (MNIST_IMAGE_WIDTH != header.number_of_rows) {
        fprintf(stderr, "Invalid number of image rows in image file %s (%d not %d)\n", path, header.number_of_rows, MNIST_IMAGE_WIDTH);
    }

    if (MNIST_IMAGE_HEIGHT != header.number_of_columns) {
        fprintf(stderr, "Invalid number of image columns in image file %s (%d not %d)\n", path, header.number_of_columns, MNIST_IMAGE_HEIGHT);
    }

    *number_of_images = header.number_of_images;
    images = malloc(*number_of_images * sizeof(mnist_image_t));

    if (images == NULL) {
        fprintf(stderr, "Could not allocated memory for %d images\n", *number_of_images);
        fclose(stream);
        return NULL;
    }

    if (*number_of_images != fread(images, sizeof(mnist_image_t), *number_of_images, stream)) {
        fprintf(stderr, "Could not read %d images from: %s\n", *number_of_images, path);
        free(images);
        fclose(stream);
        return NULL;
    }

    fclose(stream);

    return images;
}

mnist_dataset_t * mnist_get_dataset(const char * image_path)
{
    mnist_dataset_t * dataset;
    uint32_t number_of_images;

    dataset = calloc(1, sizeof(mnist_dataset_t));

    if (NULL == dataset) {
        return NULL;
    }

    dataset->images = get_images(image_path, &number_of_images);

    if (NULL == dataset->images) {
        mnist_free_dataset(dataset);
        return NULL;
    }

    dataset->size = number_of_images;

    return dataset;
}

/**
 * Free all the memory allocated in a dataset. This should not be used on a
 * batched dataset as the memory is allocated to the parent.
 */
void mnist_free_dataset(mnist_dataset_t * dataset)
{
    free(dataset->images);
    free(dataset);
}

/**
 * Fills the batch dataset with a subset of the parent dataset.
 */
int mnist_batch(mnist_dataset_t * dataset, mnist_dataset_t * batch, int size, int number)
{
    unsigned int start_offset;

    start_offset = size * number;

    if (start_offset >= dataset->size) {
        return 0;
    }

    batch->images = &dataset->images[start_offset];
    batch->size = size;

    if (start_offset + batch->size > dataset->size) {
        batch->size = dataset->size - start_offset;
    }

    return 1;
}

//-----------------neural-network.c

// Convert a pixel value from 0-255 to one from 0 to 1
#define PIXEL_SCALE(x) (((float) (x)) / 255.0f)

// Returns a random value between 0 and 1
#define RAND_FLOAT() (((float) rand()) / ((float) RAND_MAX))

/**
 * Initialise the weights and bias vectors with values between 0 and 1
 */
void neural_network_random_weights(neural_network_t * network)
{
    int i, j;

    for (i = 0; i < MNIST_LABELS; i++) {
        network->b[i] = RAND_FLOAT();

        for (j = 0; j < MNIST_IMAGE_SIZE; j++) {
            network->W[i][j] = RAND_FLOAT();
        }
    }
}

/**
 * Calculate the softmax vector from the activations. This uses a more
 * numerically stable algorithm that normalises the activations to prevent
 * large exponents.
 */
void neural_network_softmax(float * activations, int length)
{
    int i;
    float sum, max;

    for (i = 1, max = activations[0]; i < length; i++) {
        if (activations[i] > max) {
            max = activations[i];
        }
    }

    for (i = 0, sum = 0; i < length; i++) {
        activations[i] = exp(activations[i] - max);
        sum += activations[i];
    }

    for (i = 0; i < length; i++) {
        activations[i] /= sum;
    }
}

/**
 * Use the weights and bias vector to forward propogate through the neural
 * network and calculate the activations.
 */
void neural_network_hypothesis(mnist_image_t * image, neural_network_t * network, float activations[MNIST_LABELS])
{
    int i, j;

    for (i = 0; i < MNIST_LABELS; i++) {
        activations[i] = network->b[i];

        for (j = 0; j < MNIST_IMAGE_SIZE; j++) {
            activations[i] += network->W[i][j] * PIXEL_SCALE(image->pixels[j]);
        }
    }

    neural_network_softmax(activations, MNIST_LABELS);
}

/**
 * Perform inference on dataset.
 */
void neural_network_inference(mnist_dataset_t * dataset, neural_network_t * network, int predictions[])
{
    unsigned int i, j, predict;
    float activations[MNIST_LABELS], max_activation;


    // Perform inference on an image
    for (i = 0; i < dataset->size; i++) {
        neural_network_hypothesis(&dataset->images[i], network, activations);

        // Set predict to the index of the greatest activation
        for (j = 0, predict = 0, max_activation = activations[0]; j < MNIST_LABELS; j++) {
            if (max_activation < activations[j]) {
                max_activation = activations[j];
                predict = j;
                
            }
        }
        predictions[i] = predict;
    }

}


    //////////////////
    //    SERVER    //
    //////////////////

struct args {
    int socket;
    mnist_dataset_t * dataset;
    neural_network_t * network;
    int n_batches;
};

void *
run(void *arg)
{
    int new_socket = ((struct args *) arg)->socket;
    mnist_dataset_t * dataset = ((struct args *) arg)->dataset;
    neural_network_t * network = ((struct args *) arg)->network;
    int n_batches = ((struct args *) arg)->n_batches;
    free(arg);

    int batch_num;
    char buffer[20];
    int bytes_read;

    printf("[Server] Communicate with the new connection #%u @ %p ..\n",
           new_socket, (void *)(uintptr_t)pthread_self());
    fflush(stdout);

    bytes_read = read(new_socket, buffer, sizeof(buffer));
    while (bytes_read > 0){
        batch_num = atoi(buffer);
        batch_num %= n_batches;
        mnist_dataset_t batch;

        //// Initialise batch
        mnist_batch(dataset, &batch, BATCH_SIZE, batch_num);

        // Perform inference on batch
        int predictions[BATCH_SIZE];
        neural_network_inference(&batch, network, predictions);

        if(write(new_socket, predictions, sizeof(predictions)) < 0){
            perror("Write error");
        }
        else{
            printf("Buffer sent (%d):", batch_num);
            for(int i = 0; i < BATCH_SIZE; ++i){
                printf("%d ", predictions[i]);
            }
            printf("\n");
            fflush(stdout);
        }
        bytes_read = read(new_socket, buffer, 4);
    }
    
    if (bytes_read == 0) {
        printf("Client disconnected.\n");
        fflush(stdout);
    } 
    else {
        perror("Read error");
    }

    printf("[Server] Shutting down the new connection #%u ..\n", new_socket);
    fflush(stdout);
    shutdown(new_socket, SHUT_RDWR);

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
    //LOAD DATA AND MODEL
    mnist_dataset_t * test_dataset;
    neural_network_t * network = malloc(sizeof(neural_network_t));

    // Read the datasets from the files
    test_dataset = mnist_get_dataset(test_images_file);

    // Initialise weights and biases with random values
    neural_network_random_weights(network);

    // Calculate how many batches (so we know when to wrap around)
    int batches = test_dataset->size / BATCH_SIZE;


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

    printf("[Server] Create socket\n");
    fflush(stdout);
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

    printf("[Server] Bind socket\n");
    fflush(stdout);
    if (bind(socket_fd, (struct sockaddr *)&addr, addrlen) < 0) {
        perror("Bind failed");
        goto fail;
    }

    printf("[Server] Listening on socket\n");
    fflush(stdout);
    if (listen(socket_fd, 128) < 0) {
        perror("Listen failed");
        goto fail;
    }

    int client_socket;
    struct args *arguments;
    printf("[Server] Wait for clients to connect ..\n");
    fflush(stdout);
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
        arguments->dataset = test_dataset;
        arguments->network = network;
        arguments->n_batches = batches;
        pthread_t thread_id;
        printf("[Server] Client connected (%s)\n", ip_string);
        fflush(stdout);
        if (pthread_create(&thread_id, NULL, run,
                           arguments)) {
            perror("Create a worker thread failed");
            free(arguments);
            shutdown(client_socket, SHUT_RDWR);
            break;
        }
        pthread_detach(thread_id);
    }

    // Cleanup
    mnist_free_dataset(test_dataset);
    free(network);

    printf("[Server] Shutting down ..\n");
    fflush(stdout);
    shutdown(socket_fd, SHUT_RDWR);
    sleep(3);
    printf("[Server] BYE \n");
    fflush(stdout);
    return EXIT_SUCCESS;

fail:
    // Cleanup
    mnist_free_dataset(test_dataset);
    free(network);

    printf("[Server] Shutting down ..\n");
    fflush(stdout);
    if (socket_fd >= 0)
        close(socket_fd);
    sleep(3);
    return EXIT_FAILURE;
}
