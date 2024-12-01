import argparse
import asyncio
import clients
import pickle
import time
from heapq import merge

WARMUP_PROP = 0.2


async def main():
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
        '-d', '--duration', 
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

    args = parser.parse_args()
    warmup_d = WARMUP_PROP * args.duration
    aux = args.host.split(':')
    host = ""
    for x in aux[:-1]:
        host += x
    port = aux[-1]

    # Choose adequate client method for benchmark
    if args.workload == 'rdb':
        client_method = clients.client_rdb
    elif args.workload == 'nosql':
        client_method = clients.client_nosql
    elif args.workload == 'ws':
        client_method = clients.client_ws
    elif args.workload == 'da':
        client_method = clients.client_da
    elif args.workload == 'ml':
        client_method = clients.client_ml

    output_file = f"{args.workload}_d{args.duration}_c{args.connections}_{time.time_ns()}"

    # Run benchmark
    tasks = [None] * args.connections
    async with asyncio.TaskGroup() as tg:
        start_time = asyncio.get_running_loop().time()
        for i in range(args.connections):
            tasks[i] = tg.create_task(client_method(
                i, 
                start_time, 
                host, 
                port, 
                warmup_d, 
                args.duration
            ))
    
    results = list(merge([task.result() for task in tasks]))

    # Store results
    file = open(f"../../results/{output_file}.pkl", 'wb')
    pickle.dump(results, file)
    file.close()

if __name__ == "__main__":
    asyncio.run(main())