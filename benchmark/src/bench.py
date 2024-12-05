import argparse
import asyncio
import main
import os
import pickle
from clients import get_client_method
from heapq import merge
from pathlib import Path


WARMUP_PROP = 0.2


async def bench(workload, wasm, duration, connections, host, port, debug=False):
    # Set warmup time
    warmup_d = WARMUP_PROP * duration

    # Choose adequate client method for benchmark
    client_method = get_client_method(workload)

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
                warmup_d + duration,
                debug=debug
            ))
    
    latencies = list(merge(*[task.result()[0] for task in tasks]))
    m = min([p[0] for p in latencies] + [float('inf')])
    results = {
        'type': 'wasm' if wasm else 'native',
        'duration': duration,
        'connections': connections,
        'latencies': [(t-m, l) for (t, l) in latencies]
    }
    error = any([task.result()[1] for task in tasks])

    # Select name of output file
    output_file = f"{workload}_{'wasm' if wasm else 'native'}_d{duration}_c{connections}"

    # Store results
    folder = Path(__file__).parents[1] / "results" / "raw_data" /main.WORKLOADS[workload]
    folder.mkdir(exist_ok=True)
    os.chmod(folder, 0o777)
    file = open(folder / f"{output_file}.pkl", 'wb')
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
        help="Host to benchmark e.g. \'-H http://127.0.0.1:5050\'.",
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
    workloads = main.WORKLOADS.keys()
    parser.add_argument(
        '-w', '--workload', 
        type=str, 
        choices = workloads,
        required=True, 
        help=f"Identifier of the workload to be benchmarked. Must be one of the following [" + ", ".join(workloads) + "]",
        dest="workload"
    )

    # Wasm
    parser.add_argument(
        '-W', '--wasm', 
        action='store_true',
        help="Changes the name of the output file according to the implementation of the workload being benchmarked.",
        dest="wasm"
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
    asyncio.run(bench(args.workload, args.wasm, args.duration, args.connections, host, port, args.debug))