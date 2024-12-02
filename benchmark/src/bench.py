import argparse
import asyncio
import os
import pickle
import time
from clients import get_client
from heapq import merge

WARMUP_PROP = 0.2


async def bench(workload, duration, connections, host, port):
    # Set warmup time
    warmup_d = WARMUP_PROP * duration

    # Choose adequate client method for benchmark
    client_method = get_client(workload)

    # Select name of output file
    output_file = f"{workload}_d{duration}_c{connections}_{time.time_ns()}"

    # Run benchmark
    tasks = [None] * connections
    async with asyncio.TaskGroup() as tg:
        start_time = asyncio.get_running_loop().time()
        for i in range(connections):
            tasks[i] = tg.create_task(client_method(
                i, 
                start_time, 
                host, 
                port, 
                warmup_d, 
                duration
            ))
    
    results = list(merge([task.result()[0] for task in tasks]))
    error = any([task.result()[1] for task in tasks])

    # Store results
    filepath = os.path.join(
        os.path.realpath(os.path.dirname(os.path.dirname(__file__))), 
        "results", 
        f"{output_file}.pkl"
    )
    file = open(filepath, 'wb')
    pickle.dump(results, file)
    file.close()

    return error


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()

    # Host
    parser.add_argument(
        '-H', '--host', 
        type=str, 
        required=True, 
        help="Host to benchmark e.g. \'-h http://127.0.0.1:5050\'.",
        dest="host"
    )

    # Connections
    parser.add_argument(
        '-c', '--connections', 
        type=int, 
        required=True, 
        help="Total number of connections.",
        dest="connections"
    )

    # Duration
    parser.add_argument(
        '-D', '--duration', 
        type=int, 
        required=True, 
        help=f"Duration of the benchmark's measurement phase in seconds. A warmup phase will precede it, lasting {round(WARMUP_PROP * 100, 2)}% of the measurement phase duration.",
        dest="duration"
    )

    # Workload
    parser.add_argument(
        '-w', '--workload', 
        type=str, 
        choices = ['rdb', 'nosql', 'ws', 'da', 'ml'],
        required=True, 
        help=f"Identifier of the workload to be benchmarked. Must be one of the following [rdb, nosql, ws, da, ml].",
        dest="workload"
    )

    # Debug
    parser.add_argument(
        '-d', '--debug', 
        action='store_true',
        help="Messages will be printed on screen if this flag is set.",
        dest="debug"
    )

    args = parser.parse_args()
    
    aux = args.host.split(':')
    host = ""
    for x in aux[:-1]:
        host += x
    port = aux[-1]

    # Run benchmark
    asyncio.run(bench(args.workload, args.duration, args.connections, host, port))