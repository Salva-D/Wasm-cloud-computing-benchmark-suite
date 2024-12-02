import asyncio
import random

MEAN_DELAY = 1.0

async def client_rdb(id, start_time, host, port, warmup_d, measurement_d, debug=False):
    ...

async def client_nosql(id, start_time, host, port, warmup_d, measurement_d, debug=False):
    ...

async def client_ws(id, start_time, host, port, warmup_d, measurement_d, debug=False):
    ...

async def client_da(id, start_time, host, port, warmup_d, measurement_d, debug=False):
    ...

async def client_ml(id, start_time, host, port, warmup_d, measurement_d, debug=False):
    request_logs = []
    error = False
    try:
        # Connect to the server
        reader, writer = await asyncio.open_connection(host, port)

        if debug:
            print(f"Client {id} connected to {host}:{port}")
    
        # Keep sending requests until measurement_d expires
        while asyncio.get_running_loop().time() - start_time < measurement_d:
            # Send a message
            message = str(random.randint(0, 9999))
            writer.write(message.encode())
            await writer.drain()  # Ensure data is sent
            request_start_time = asyncio.get_running_loop().time()

            # Wait for a response
            response = await reader.read(100)  # Adjust buffer size if needed
            request_duration = asyncio.get_running_loop().time() - request_start_time
            if asyncio.get_running_loop().time() - start_time - request_duration < warmup_d:
                request_logs.append((request_start_time, request_duration))
            if debug:
                print(f"Client {id} received: {response}")

            # Optional: add delay to mimic real-world traffic patterns
            await asyncio.sleep(random.expovariate(1 / MEAN_DELAY))

        if debug:
            print(f"Client {id} finished after {measurement_d} seconds")

        # Close the connection
        writer.close()
        await writer.wait_closed()

    except Exception as e:
        error = True
        if debug:
            print(f"Client {id} encountered an error: {e}")

    return request_logs, error
