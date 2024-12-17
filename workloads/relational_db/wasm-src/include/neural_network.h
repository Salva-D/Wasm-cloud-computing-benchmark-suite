#ifndef NEURAL_NETWORK_H_
#define NEURAL_NETWORK_H_

#include "mnist_file.h"

typedef struct neural_network_t_ {
    float b[MNIST_LABELS];
    float W[MNIST_LABELS][MNIST_IMAGE_SIZE];
} neural_network_t;

void neural_network_random_weights(neural_network_t * network);
void neural_network_hypothesis(mnist_image_t * image, neural_network_t * network, float activations[MNIST_LABELS]);
void neural_network_inference(mnist_dataset_t * dataset, neural_network_t * network, int predictions[]);

#endif
