import asyncio
import random
import time

MEAN_DELAY = 1.0


async def client_rdb(id, start_time, host, port, warmup_d, total_d, debug=False):
    ...


async def client_nosql(id, start_time, host, port, warmup_d, total_d, debug=False):
    ...


async def client_ws(id, start_time, host, port, warmup_d, total_d, debug=False):
    ...


async def client_da(id, start_time, host, port, warmup_d, total_d, debug=False):
    ...


async def client_ml(id, host, port, warmup_end, deadline, debug=False):
    request_logs = []
    error_abort = False
    error_reconnect = False
    reader, writer = None, None

    while asyncio.get_running_loop().time() < deadline:
        try:
            # Connect to the server (with timeout)
            async with asyncio.timeout_at(deadline):
                reader, writer = await asyncio.open_connection(host, port)
            if debug:
                print(f"Client {id} connected to {host}:{port}")

            # Keep sending messages until time expires
            while asyncio.get_running_loop().time() < deadline:
                # Send a message
                message = str(random.randint(0, 9999))
                
                # Start measuring
                request_start_time = time.perf_counter_ns()
                writer.write(message.encode())

                # Ensure data is sent (with timeout)
                await writer.drain()

                async with asyncio.timeout_at(deadline):    
                    response = await reader.read(100)  # Adjust buffer size if needed
                    request_duration = time.perf_counter_ns() - request_start_time

                if asyncio.get_running_loop().time() - request_duration * 1e-9 >= warmup_end:
                    request_logs.append((request_start_time, request_duration))
                if debug:
                    print(f"Client {id} received: {response}")

                # Delay to mimic real-world traffic patterns
                async with asyncio.timeout_at(deadline):
                    await asyncio.sleep(min(random.expovariate(1 / MEAN_DELAY), 10))

            if debug:
                print(f"Client {id} finished at {asyncio.get_running_loop().time()}")

        except asyncio.TimeoutError as e:
            if debug:
                print(f"(to) Client {id} finished at {asyncio.get_running_loop().time()}")
            break
        except ConnectionError as e:
            error_reconnect = True
            if debug:
                print(f"Client {id} encountered a recoverable error: {e}\nReconnecting...")
        except Exception as e:
            error_abort = True
            if debug:
                print(f"Client {id} encountered an unrecoverable error: {e}\nAborting...")
        finally:
            if writer and not writer.is_closing():
                writer.close()
                await writer.wait_closed()

    return request_logs, error_abort, error_reconnect


def get_client_method(workload):
    if workload == 'rdb':
        return client_rdb
    elif workload == 'nosql':
        return client_nosql
    elif workload == 'ws':
        return client_ws
    elif workload == 'da':
        return client_da
    elif workload == 'ml':
        return client_ml
