import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pickle
from pathlib import Path
import math

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
        'error_abort': [],
        'error_reconnect': [],
    }
    index = []
    results_dir = Path(__file__).parents[1] / "results"

    raw_data_dir = results_dir / "raw_data"
    for w_dir in raw_data_dir.iterdir():
        if w_dir.is_dir():
            w_name = ' '.join(w_dir.name.split('_'))
            for datafile in w_dir.iterdir():
                if datafile.suffix == '.pkl':
                    with open(datafile, 'rb') as file:
                        raw_data = pickle.load(file)
                    
                    index.append(w_name)
                    columns['type'].append(raw_data['type'])
                    columns['number of connections'].append(raw_data['connections'])

                    ls = [l[1] * 1e-9 for l in raw_data['latencies']]  # Convert from ns to s
                    columns['number of requests'].append(len(ls))
                    columns['throughput (req/s)'].append(len(ls) / raw_data['duration'])
                    columns['latency mean (s)'].append(np.mean(ls))
                    columns['latency std (s)'].append(np.std(ls))
                    columns['latency min (s)'].append(min(ls))
                    columns['latency max (s)'].append(max(ls))
                    columns['tail latency 95% (s)'].append(np.percentile(ls, 95))
                    columns['tail latency 99% (s)'].append(np.percentile(ls, 99))
                    columns['tail latency 99.9% (s)'].append(np.percentile(ls, 99.9))

                    columns['error_abort'].append(raw_data['error_abort'])
                    columns['error_reconnect'].append(raw_data['error_reconnect'])

    # Create dataframe
    df = pd.DataFrame(data=columns, index=index)
    df.index.name = 'workload'
    df.sort_values(by=['workload', 'type', 'number of connections'], inplace=True)

    # Store processed data
    processed_data_dir = results_dir / "processed_data"
    processed_data_dir.mkdir(parents=True, exist_ok=True)
    path = processed_data_dir / "processed_data.pkl"
    with open(path, 'wb') as file:
        pickle.dump(df, file)


def draw_graphs():
    results_dir = Path(__file__).parents[1] / "results"
    df = pd.read_pickle(results_dir / "processed_data" / "processed_data.pkl")

    throughput_dir = results_dir / "figures" / "throughput"
    throughput_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(throughput_dir, 0o777)
    tail_latencies_dir = results_dir / "figures" / "tail_latencies"
    tail_latencies_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(tail_latencies_dir, 0o777)

    # Get unique benchmark names
    w_names = df.index.unique()
    n_w = len(w_names)

    # Determine subplot grid size: 1 column, n_w rows
    n_cols = 1
    n_rows = n_w

    # Parameters for latency plots
    lw = 1.2  # Line width
    ms = 7    # Marker size

    # Create figure for Throughput
    fig_throughput, axes_throughput = plt.subplots(
        n_rows, n_cols, figsize=(8, n_rows * 3), sharex=True, sharey=False
    )
    if n_w == 1:
        axes_throughput = [axes_throughput]  # Ensure it's iterable

    # Create figure for Latency
    fig_latency, axes_latency = plt.subplots(
        n_rows, n_cols, figsize=(8, n_rows * 3), sharex=True, sharey=False
    )
    if n_w == 1:
        axes_latency = [axes_latency]  # Ensure it's iterable

    for idx, w_name in enumerate(w_names):
        df_w = df.loc[w_name]


        if (w_name == 'machine learning') :
            title = 'Machine Learning'
        elif (w_name == 'no sql db') :
            title = 'NoSQL Database'
        else :
            title = 'UNKNOWN'
        fontsize = 18

        # --- Throughput Plot ---
        ax_t = axes_throughput[idx]
        
        # Plot Native Throughput
        native_data = df_w[df_w['type'] == 'native']
        ax_t.plot(
            native_data['number of connections'],
            native_data['throughput (req/s)'],
            's-',
            label='Native',
            color=NATIVE_COLOR
        )
        
        # Plot Wasm Throughput
        wasm_data = df_w[df_w['type'] == 'wasm']
        ax_t.plot(
            wasm_data['number of connections'],
            wasm_data['throughput (req/s)'],
            's-',
            label='Wasm',
            color=WASM_COLOR
        )
        
        ax_t.set_title(title, fontsize=fontsize)
        if idx == n_w - 1:
            ax_t.set_xlabel('Number of Connections')
        ax_t.set_ylabel('Throughput (req/s)')
        ax_t.legend(loc='best')
        ax_t.grid(True)

        # --- Latency Plot ---
        ax_l = axes_latency[idx]
        
        # Plot Native Latencies
        for p, m in [('95', 's'), ('99', '^')]:  # Add ('99.9', 'o') if needed
            latency_column = f'tail latency {p}% (s)'
            ax_l.plot(
                native_data['number of connections'],
                native_data[latency_column],
                f'{m}-',
                label=f'Native {p}%',
                color=NATIVE_COLOR,
                markerfacecolor='none',
                linewidth=lw,
                markersize=ms
            )
        
        # Plot Wasm Latencies
        for p, m in [('95', 's'), ('99', '^')]:  # Add ('99.9', 'o') if needed
            latency_column = f'tail latency {p}% (s)'
            ax_l.plot(
                wasm_data['number of connections'],
                wasm_data[latency_column],
                f'{m}-',
                label=f'Wasm {p}%',
                color=WASM_COLOR,
                markerfacecolor='none',
                linewidth=lw,
                markersize=ms
            )
        
        ax_l.set_title(title, fontsize=fontsize)
        if idx == n_w - 1:
            ax_l.set_xlabel('Number of Connections')
        ax_l.set_ylabel('Tail Latency (s)')
        ax_l.legend(loc='best')
        ax_l.grid(True)

    # Remove any unused subplots (if any)
    total_subplots = n_rows * n_cols
    if n_w < total_subplots:
        for j in range(n_w, total_subplots):
            fig_throughput.delaxes(axes_throughput[j])
            fig_latency.delaxes(axes_latency[j])

    # Adjust layout for better spacing
    fig_throughput.tight_layout()
    fig_latency.tight_layout()
    # Optionally, adjust the spacing between subplots
    # fig_throughput.subplots_adjust(hspace=0.4)
    # fig_latency.subplots_adjust(hspace=0.4)

    # Save the combined figures
    fig_throughput.savefig(throughput_dir / "throughput.png")
    fig_latency.savefig(tail_latencies_dir / "tail_latencies.png")

    # Close the figures to free up memory
    plt.close(fig_throughput)
    plt.close(fig_latency)


if __name__ == "__main__":
    gather_results()
    draw_graphs()
