import asyncio
import time

# 1. Define an asynchronous function using 'async def'
# This function simulates an I/O-bound operation (e.g., fetching data from a network)
async def fetch_data(delay: int, item_name: str) -> str:
    """
    Simulates fetching data asynchronously.

    Args:
        delay (int): The time in seconds to 'wait' for the data.
        item_name (str): The name of the item being fetched.

    Returns:
        str: A message indicating the data was fetched.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Starting to fetch {item_name}...")
    # 2. Use 'await' to pause the execution of this function
    # until the 'asyncio.sleep' (simulating an I/O operation) completes.
    # The event loop can then run other tasks in the meantime.
    await asyncio.sleep(delay) # Simulate network delay or disk I/O
    print(f"[{time.strftime('%H:%M:%S')}] Finished fetching {item_name}.")
    return f"Data for {item_name} fetched after {delay} seconds."

# Another asynchronous function
async def process_item(item_id: int):
    """
    Processes an item, which involves fetching data.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Processing item {item_id}...")
    # 3. Call another async function using 'await'
    result = await fetch_data(2, f"item_{item_id}_details")
    print(f"[{time.strftime('%H:%M:%M')}] Item {item_id} processed: {result}")

# 4. The main asynchronous function that orchestrates other async tasks
async def main():
    """
    The main entry point for the asynchronous program.
    It creates and runs multiple concurrent tasks.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Starting main program.")

    # 5. Create multiple tasks to run concurrently
    # asyncio.create_task schedules the coroutine to run in the event loop.
    # These tasks will run 'in parallel' (concurrently) as the event loop switches
    # between them when they 'await' on something.
    task1 = asyncio.create_task(fetch_data(3, "User Profile"))
    task2 = asyncio.create_task(fetch_data(1, "Product Catalog"))
    task3 = asyncio.create_task(process_item(101))

    # 6. 'await' the completion of all tasks
    # asyncio.gather runs tasks concurrently and waits for all of them to finish.
    # The results will be returned in the order the tasks were passed to gather.
    results = await asyncio.gather(task1, task2, task3)

    print(f"[{time.strftime('%H:%M:%S')}] All tasks completed.")
    for res in results:
        print(f"- {res}")

# 7. Run the main asynchronous function
# asyncio.run() is the top-level entry point to run an async program.
# It handles the creation and closing of the event loop.
if __name__ == "__main__":
    print("--- Synchronous Start ---")
    start_time = time.monotonic()
    asyncio.run(main())
    end_time = time.monotonic()
    print(f"--- Synchronous End ---")
    print(f"Total execution time: {end_time - start_time:.2f} seconds")

    # For comparison, if these were synchronous calls:
    print("\n--- Synchronous Comparison (would take longer) ---")
    sync_start_time = time.monotonic()
    # fetch_data(3, "User Profile") # This would block
    # fetch_data(1, "Product Catalog") # This would block
    # process_item(101) # This would block
    # If run synchronously, the total time would be 3 + 1 + 2 = 6 seconds (sum of delays)
    # With async, it's closer to the longest single delay (3 seconds in this case).
    sync_end_time = time.monotonic()
    print(f"Total estimated synchronous time: 3 + 1 + 2 = 6 seconds (if run sequentially)")
