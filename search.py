from mcstatus import JavaServer
import concurrent.futures
import random
import time
import socket
import threading

# Set a reasonable timeout for connections
socket.setdefaulttimeout(1.5)

# Create a lock for thread-safe file writing
file_lock = threading.Lock()

# ANSI color codes for prettier output
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"


def random_address():
    # More efficient IP generation
    return f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}:25565"


def query_address(address):
    try:
        # Use a shorter timeout for initial connection
        server = JavaServer.lookup(address, timeout=1)

        try:
            # Try status protocol first (faster)
            status = server.status(retries=0)
            server_info = {
                "type": "status",
                "players": f"{status.players.online}/{status.players.max}",
                "version": status.version.name,
                "description": status.description,
                "latency": f"{status.latency:.1f}ms",
            }
        except Exception:
            try:
                # Fall back to query protocol if status fails
                query = server.query()
                server_info = {
                    "type": "query",
                    "players": f"{query.players.online}/{query.players.max}",
                    "version": query.software.version,
                    "description": query.motd.to_minecraft(),
                    "software": f"{query.software.brand} with {len(query.software.plugins)} plugins",
                }
            except Exception:
                return False

        # Write to file immediately when a server is found
        with file_lock:
            with open("servers.txt", "a") as file:
                file.write(f"{address} - {server_info['version']} - {server_info['players']}\n")

        # Print a more noticeable alert with server info
        print(f"\n{GREEN}{BOLD}🎮 SERVER FOUND! {address} ✅{RESET}")
        print(f"{GREEN}Players: {server_info['players']}")
        print(f"Version: {server_info['version']}")
        if server_info["type"] == "query":
            print(f"Software: {server_info['software']}")
        print(f"Description: {server_info['description']}")
        if "latency" in server_info:
            print(f"Latency: {server_info['latency']}{RESET}\n")
        else:
            print(f"{RESET}\n")
        return True

    except Exception:
        # Minimize output for failed servers to reduce overhead
        return False


print(f"{BOLD}Searching for open Minecraft servers...{RESET}")
try:
    batch_counter = 0
    while True:
        # Generate addresses more efficiently
        ip_addresses = [random_address() for _ in range(1000)]  # Increased batch size

        # Use more workers to increase throughput
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            # Submit all tasks
            futures = []
            for address in ip_addresses:
                futures.append(executor.submit(query_address, address))

            # Wait for all futures to complete - no timeout handling needed here
            concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        # Track progress
        batch_counter += 1
        if batch_counter % 3 == 0:
            print(f"Processed {batch_counter * 1000} addresses...")

except KeyboardInterrupt:
    print(f"\n{BOLD}Search stopped.{RESET}")
