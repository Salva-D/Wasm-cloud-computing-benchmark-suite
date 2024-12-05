import numpy as np
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


def gather_results():
    columns = {
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
                    print(datafile)
                    file = open(datafile, 'rb')
                    raw_data = pickle.load(file)
                    file.close()

                    index.append(f"{w_name} ({raw_data['type']})")
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
    print(columns)
    print(index)
    df = pd.DataFrame(data=columns, index=index)
    df.index.name = 'workload'
    df.sort_values(by=['workload', 'number of connections'], inplace=True)

    # Store processed data
    path = raw_data_dir = results_dir / "processed_data" / "processed_data.pkl"
    file = open(path, 'wb')
    pickle.dump(df, file)
    file.close()

def draw_graphs():
    ...

if __name__ == "__main__":
    gather_results()
    draw_graphs()