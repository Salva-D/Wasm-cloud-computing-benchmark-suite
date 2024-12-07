import argparse
import asyncio
import main
import multiprocessing
import os
import pickle
from clients import get_client_method
from heapq import merge
from pathlib import Path


WARMUP_PROP = 0.2
BATCH_SIZE = 250


async def group(group_id, client_method, warmup_d, duration, connections, host, port, debug, results_q):
    # Run benchmark
    tasks = []
    remaining = connections
    async with asyncio.TaskGroup() as tg:
        start_time = asyncio.get_running_loop().time()
        warmup_end = start_time + warmup_d
        deadline = warmup_end + duration
        while remaining > 0:
            for j in range(min(BATCH_SIZE, remaining)):
                tasks.append(tg.create_task(client_method(
                    id=group_id + connections - remaining + j, 
                    host=host, 
                    port=port, 
                    warmup_end=warmup_end, 
                    deadline=deadline,
                    debug=debug
                )))
            await asyncio.sleep(0.01) # Small delay between batch creation to not overload the server
            remaining -= BATCH_SIZE

    
    latencies = list(merge(*[task.result()[0] for task in tasks]))
    error_abort = any([task.result()[1] for task in tasks])
    error_reconnect = any([task.result()[2] for task in tasks])
    results_q.put((latencies, error_abort, error_reconnect))

def group_runner(group_id, client_method, warmup_d, duration, connections, host, port, debug, results_q):
    asyncio.run(group(group_id, client_method, warmup_d, duration, connections, host, port, debug, results_q))

async def bench(workload, wasm, duration, connections, host, port, debug=False):
    # Set warmup time
    warmup_d = WARMUP_PROP * duration

    # Choose adequate client method for benchmark
    client_method = get_client_method(workload)

    # Balance load
    n_cpu = os.cpu_count()
    n_processes = max(1, min(n_cpu, connections // BATCH_SIZE))
    div_ = connections // n_processes
    rem_ = connections % n_processes
    # connections = rem_ * (div_ + 1) + (n_processes - rem_) * div_ (Most balanced distribution)

    processes = []
    results_q = multiprocessing.Queue()
    group_id = 0
    for i in range(n_processes):
        if i < rem_:
            group_connections = div_ + 1
        else:
            group_connections = div_

        process = multiprocessing.Process(
            target=group_runner, 
            args=(group_id, client_method, warmup_d, duration, group_connections, host, port, debug, results_q)
        )
        processes.append(process)
        process.start()
        group_id += group_connections

    # Gather results
    error_abort = False
    error_reconnect = False
    ls = []
    for _ in processes:
        r = results_q.get()
        ls.append(r[0])
        if r[1]: error_abort = True
        if r[2]: error_reconnect = True

    # Join processes
    for process in processes:
        process.join()

    # Finish processing results
    latencies = list(merge(*ls))
    m = min([p[0] for p in latencies] + [float('inf')])
    results = {
        'type': 'wasm' if wasm else 'native',
        'duration': duration,
        'connections': connections,
        'error_abort': error_abort,
        'error_reconnect': error_reconnect,
        'latencies': [(t-m, l) for (t, l) in latencies]
    }
    
    # Select name of output file
    output_file = f"{workload}_{'wasm' if wasm else 'native'}_d{duration}_c{connections}"

    # Store results
    folder = Path(__file__).parents[1] / "results" / "raw_data" /main.WORKLOADS[workload]
    folder.mkdir(exist_ok=True)
    os.chmod(folder, 0o777)
    file = open(folder / f"{output_file}.pkl", 'wb')
    pickle.dump(results, file)
    file.close()

    return error_abort


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
        help=f"Duration of the benchmark's measurement phase in seconds. A warmup phase will precede it, lasting {round(WARMUP_PROP * 100, 2)}%% of the measurement phase duration.",
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