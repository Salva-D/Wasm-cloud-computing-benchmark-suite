# WebAssembly-benchmark-suite
Benchmark suite for cloud computing workloads in WebAssembly.

## Installation and setup
1. Download wasm micro runtime (WAMR) and place it in the /opt folder:
    - Follow the instructions to download WAMR.
    - By the end, /opt should contain these folders:
      - /wabt
      - /wasi-sdk
      - /wasm-micro-runtime

2. Clone this repository (Can be placed anywhere).

3. Install the required packages in requirements.txt (you will need at least **python3.11**). Run this command from the benchmark/src folder.
```
pip install -r requirements.txt
```

4. Place workloads in the /workloads folder of this benchmark suite.
    - One folder per workload. Follow the same internal file structure as the machine_learning workload already available.
    - Valid names of workload folders are: relational_db, no_sql_db, web_server, data_analytics, machine_learning.
    - If you want to be able to benchmark additional workloads, their folder names and command line abbreviations have to be hard coded in the `src.main.WORKLOADS` dictionary. Additionally, a client method will have to be implemented for the workload in src.clients and added to the src.clients.get_client_method function (it should be returned if the workload argument equals the command-line abbreviation that you defined).

## Usage
* **benchmark.src.main:** Automatically runs and benchmarks all workloads specified in CLI for the specified durations for increasing loads and stores raw results in results/raw_data.
    - Must be run in sudo mode.
    - Automatically starts and kills servers in workloads folder.
    
    For example:
    ```
    sudo python3 main.py -H 127.0.0.1:1234 -ml 10
    ```
    _**Note:** Empty results/raw_data folder before running to ensure results do not get mixed up with results from previous runs._

* **benchmark.src.analysis:** Processes data and generates graphs for all workloads based on the raw data stored in results/raw_data.
    - Processed data is stored in a Pandas.DataFrame in results/processed_data/processed_data.pkl.
    - Graphs for throughput and tail latencies are stored in results/figures.
    
    For example:
    ```
    sudo python3 analysis.py
    ```

* **benchmark.src.bench:** Benchmark a single workload. Server must be started and run on a separate terminal manually.
    - Useful for testing and debugging.
    
    For example:
    ```
    sudo python3 bench.py -H 127.0.0.1:1234 -c 5000 -D 30 -w ml
    ```
### _Running a Wasm server workload example_
```
sudo ./iwasm --dir=. --max-threads=30000 --addr-pool=0.0.0.0/15 machine_learning.wasm
```
