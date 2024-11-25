#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h> //Header file for sleep(). man 3 sleep for details.

int NUM_THREADS = 10;

// A normal C function that is executed as a thread
// when its name is specified in pthread_create()
void* myThreadFun(void* vargp)
{
    sleep(1);
    printf("Printing from Thread %d\n", *(int *)vargp);
    return NULL;
}

int main()
{
    printf("started\n");
    pthread_t thread_id[NUM_THREADS];
    int *arg = malloc(NUM_THREADS*sizeof(int));
    for(int i = 0; i < NUM_THREADS; ++i){
        arg[i] = i;
        pthread_create(&thread_id[i], NULL, myThreadFun, &arg[i]);
    }
    
    for(int i = 0; i < NUM_THREADS; ++i){
        pthread_join(thread_id[i], NULL);
    }
    printf("ended\n");

    exit(0);
}
