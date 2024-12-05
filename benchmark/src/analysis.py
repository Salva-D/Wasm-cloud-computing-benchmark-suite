import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pickle
from pathlib import Path

"""
Info per load and amount (All workloads and amounts in 1 table):
 - Number of requests
 - Throughput (Req/sec)
 - Tail latencies: 95%, 99%, 99.9%
 - Latency avg, std, min, max


Graphs (for 1 workload): -> figures
 - Throughput vs number of clients (wasm and native on same graph)
 - Tail latencies: 95%, 99%, 99.9% vs number of clients (wasm and native on same graph)



Tables:
 - 
"""

NATIVE_COLOR = 'orange'
WASM_COLOR = '#654ff0'


def gather_results():
    columns = {
        'type': [],
        'number of connections': [],
        'number of requests': [],
        'throughput (req/sec)': [],
        'latency mean': [],
        'latency std': [],
        'latency min': [],
        'latency max': [],
        'tail latency 95%': [],
        'tail latency 99%': [],
        'tail latency 99.9%': [],
    }
    index = []#machine learning (native) 
    results_dir = Path(__file__).parents[1] / "results"

    raw_data_dir = results_dir / "raw_data"
    for w_dir in raw_data_dir.iterdir():
        if w_dir.is_dir():
            w_name = ' '.join(w_dir.name.split('_'))
            for datafile in w_dir.iterdir():
                if datafile.suffix == '.pkl':
                    file = open(datafile, 'rb')
                    raw_data = pickle.load(file)
                    file.close()

                    index.append(w_name)
                    columns['type'].append(raw_data['type'])
                    columns['number of connections'].append(raw_data['connections'])

                    ls = list(l[1] for l in raw_data['latencies'])
                    columns['number of requests'].append(len(ls))
                    columns['throughput (req/sec)'].append(len(ls) / raw_data['duration'])
                    columns['latency mean'].append(np.mean(ls))
                    columns['latency std'].append(np.std(ls))
                    columns['latency min'].append(min(ls))
                    columns['latency max'].append(max(ls))
                    columns['tail latency 95%'].append(np.percentile(ls, 95))
                    columns['tail latency 99%'].append(np.percentile(ls, 99))
                    columns['tail latency 99.9%'].append(np.percentile(ls, 99.9))

    # Create dataframe
    df = pd.DataFrame(data=columns, index=index)
    df.index.name = 'workload'
    df.sort_values(by=['workload', 'type', 'number of connections'], inplace=True)

    # Store processed data
    path = raw_data_dir = results_dir / "processed_data" / "processed_data.pkl"
    file = open(path, 'wb')
    pickle.dump(df, file)
    file.close()


def draw_graphs():
    results_dir = Path(__file__).parents[1] / "results"
    df = pd.read_pickle(results_dir / "processed_data" / "processed_data.pkl")

    throughput_dir = results_dir / "figures" / "throughput"
    throughput_dir.mkdir(exist_ok=True)
    os.chmod(throughput_dir, 0o777)
    tail_latencies_dir = results_dir / "figures" / "tail_latencies"
    tail_latencies_dir.mkdir(exist_ok=True)
    os.chmod(tail_latencies_dir, 0o777)

    # Draw graphs
    for w_name in df.index.unique():
        df_w = df.loc[w_name]

        # Throuput
        plt.plot('number of connections', 'throughput (req/sec)', 's--', data=df_w[df_w['type'] == 'native'], label='Native', color=NATIVE_COLOR)
        plt.plot('number of connections', 'throughput (req/sec)', 's--', data=df_w[df_w['type'] == 'wasm'], label='Wasm', color=WASM_COLOR)
        plt.xlabel('number of connections')
        plt.ylabel('throughput (req/sec)')
        plt.legend(loc='best')
        plt.grid()
        plt.savefig(throughput_dir / f"{'_'.join(w_name.split(' '))}_throughput.png")
        plt.close()

        # Tail latencies



if __name__ == "__main__":
    gather_results()
    draw_graphs()