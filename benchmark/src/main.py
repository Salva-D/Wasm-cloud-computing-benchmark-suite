import argparse
import asyncio
import bench
import subprocess
import time
import uvloop
from pathlib import Path
from tqdm import tqdm

WORKLOADS = {
    'rdb': 'relational_db', 
    'nosql': 'no_sql_db', 
    'ws': 'web_server', 
    'da': 'data_analytics', 
    'ml': 'machine_learning'
}
COOLDOWN = 5
DEFAULT_DURATION = 10

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def main(workloads, durations, host, port):
    # Gather workload executables
    native_exes = []
    wasm_exes = []
    runtimes = []
    full_w_names = {WORKLOADS[w] for w in workloads}
    workloads_dir = Path(__file__).parents[2] / "workloads"
    for w_dir in workloads_dir.iterdir():
        if w_dir.is_dir():
            w_dir_name = w_dir.name
            if w_dir_name in full_w_names:
                nexe = w_dir / "build" / w_dir_name
                wexe = w_dir / "build" / f"{w_dir_name}.wasm"
                iwasm = w_dir / "build" / "iwasm"
                assert nexe.exists(), f"Missing native binary for workload {w_dir_name}."
                assert wexe.exists(), f"Missing wasm binary for workload {w_dir_name}."
                assert iwasm.exists(), f"Missing runtime for workload {w_dir_name}."
                native_exes.append(nexe)
                wasm_exes.append(wexe)
                runtimes.append(iwasm)
                full_w_names.remove(w_dir_name)
    
    assert len(full_w_names) == 0, f"Missing folders for the following workloads: [" + ", ".join(full_w_names) + "]." 

    # Run benchmarks for varying loads
    for w, d, nexe, wexe, runtime in zip(workloads, durations, native_exes, wasm_exes, runtimes):
        # Native
        for connections in tqdm(range(100, 1100, 100), desc=WORKLOADS[w]):
            # Launch server
            server_process = subprocess.Popen(args=nexe, cwd=nexe.parent)
            time.sleep(1)
            # Run benchmark
            error = asyncio.run(bench.bench(w, False, d, connections, host, port))
            time.sleep(0.1)
            # Terminate server
            if server_process != None:
                server_process.terminate()
            time.sleep(COOLDOWN)
            if error: break

        # Wasm
        for connections in tqdm(range(100, 1100, 100), desc=WORKLOADS[w]+".wasm"):
            # Launch server
            server_process = subprocess.Popen(
                args=[runtime, "--dir=.", "--max-threads=1500", "--addr-pool=0.0.0.0/15", wexe], 
                cwd=nexe.parent
            )
            time.sleep(1)
            # Run benchmark
            error = asyncio.run(bench.bench(w, True, d, connections, host, port))
            time.sleep(0.1)
            # Terminate server
            if server_process != None:
                server_process.terminate()
            time.sleep(COOLDOWN)
            if error: break


class DefaultIfEmpty(argparse.Action):
    def __init__(self, option_strings, dest, default=None, required=False, **kwargs):
        super().__init__(option_strings, dest, nargs="?", default=argparse.SUPPRESS, required=required, **kwargs)
        self.explicit_default = default  # Store the explicit default value

    def __call__(self, parser, namespace, values, option_string=None):
        # If the argument appears without a value, set the explicit default
        if values is None:
            setattr(namespace, self.dest, self.explicit_default)
        else:
            setattr(namespace, self.dest, values)


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

    # Workloads and durations
    workload_group = parser.add_argument_group(title="Workloads", description=f"Select the workloads to benchmark with the following flags. You can select the benchmark duration of each workload by entering an amount in seconds after each flag. The default duration is {DEFAULT_DURATION} seconds.")
    for w, workload in WORKLOADS.items():
        workload_group.add_argument(
            f'-{w}', f'--{workload}',
            action=DefaultIfEmpty,
            default=DEFAULT_DURATION,
            type=int, 
            required=False, 
            metavar="duration",
            dest=w
        )

    args = parser.parse_args()
    
    # Extract host and port
    aux = args.host.split(':')
    host = ""
    for x in aux[:-1]:
        host += x
    port = aux[-1]

    # Extract selected workloads
    workloads, durations = zip(*list(filter(lambda x: x[0] != "host", vars(args).items())))

    main(workloads, durations, host, port)