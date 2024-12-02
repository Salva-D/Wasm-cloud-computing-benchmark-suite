import argparse
import asyncio
from bench import bench
import time
from bench import bench
from tqdm import tqdm

WORKLOADS = [('rdb', 'relational_db'), ('nosql', 'no_sql_db'), ('ws', 'web_server'), ('da', 'data_analytics'), ('ml', 'machine_learning')]
COOLDOWN = 5
DEFAULT_DURATION = 10


def main(workloads, durations, host, port):
    # Gather workload executables
    native_exes = []
    wasm_exes = []
    for _ in _:
        assert filename in [w[1] for w in WORKLOADS] #TODO

    for w, d, nexe, wexe in zip(workloads, durations, native_exes, wasm_exes):
        # Native
        for connections in tqdm(range(100, 1100, 100), desc=w):
            ### TODO create server
            time.sleep(1)
            asyncio.run(bench(w, d, connections, host, port))
            time.sleep(0.1)
            ### TODO kill server
            time.sleep(COOLDOWN)

        # Wasm
        for connections in tqdm(range(100, 1100, 100), desc=w+" (wasm)"):
            ### TODO create server
            time.sleep(1)
            asyncio.run(bench(w, d, connections, host, port))
            time.sleep(0.1)
            ### TODO kill server
            time.sleep(COOLDOWN)


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
        help="Host to benchmark e.g. \'-h http://127.0.0.1:5050\'.",
        dest="host"
    )

    # Workloads and durations
    workload_group = parser.add_argument_group(title="Workloads", description=f"Select the workloads to benchmark with the following flags. You can select the benchmark duration of each workload by entering an amount in seconds after each flag. The default duration is {DEFAULT_DURATION} seconds.")
    for w, workload in WORKLOADS:
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