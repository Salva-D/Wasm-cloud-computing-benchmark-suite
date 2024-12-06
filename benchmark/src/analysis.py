import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pickle
from pathlib import Path


NATIVE_COLOR = 'darkorange'
WASM_COLOR = '#654ff0'


def gather_results():
    columns = {
        'type': [],
        'number of connections': [],
        'number of requests': [],
        'throughput (req/s)': [],
        'latency mean (s)': [],
        'latency std (s)': [],
        'latency min (s)': [],
        'latency max (s)': [],
        'tail latency 95% (s)': [],
        'tail latency 99% (s)': [],
        'tail latency 99.9% (s)': [],
        'errors': [],
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
                    columns['throughput (req/s)'].append(len(ls) / raw_data['duration'])
                    columns['latency mean (s)'].append(np.mean(ls))
                    columns['latency std (s)'].append(np.std(ls))
                    columns['latency min (s)'].append(min(ls))
                    columns['latency max (s)'].append(max(ls))
                    columns['tail latency 95% (s)'].append(np.percentile(ls, 95))
                    columns['tail latency 99% (s)'].append(np.percentile(ls, 99))
                    columns['tail latency 99.9% (s)'].append(np.percentile(ls, 99.9))

                    columns['errors'].append(raw_data['errors'])

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

        # Throughput
        plt.plot('number of connections', 'throughput (req/s)', 's-', data=df_w[df_w['type'] == 'native'], label='Native', color=NATIVE_COLOR)
        plt.plot('number of connections', 'throughput (req/s)', 's-', data=df_w[df_w['type'] == 'wasm'], label='Wasm', color=WASM_COLOR)
        plt.xlabel('Number of Connections')
        plt.ylabel('Throughput (req/s)')
        plt.legend(loc='best')
        plt.grid()
        plt.savefig(throughput_dir / f"{'_'.join(w_name.split(' '))}_throughput.png")
        plt.close()

        # Tail latencies



if __name__ == "__main__":
    gather_results()
    draw_graphs()