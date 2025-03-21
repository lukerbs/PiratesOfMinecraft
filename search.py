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


def get_random_address():
    """Generate a random IP address"""
    ip = f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
    # 95% chance to use default port
    port = 25565
    return f"{ip}:{port}"


def query_server(address):
    """Query a Java edition server"""
    try:
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
        return False


def scan_batch(batch_size=1000):
    """Scan a batch of addresses"""
    addresses = [get_random_address() for _ in range(batch_size)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(query_server, address) for address in addresses]
        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

    return sum(1 for f in futures if f.result())


print(f"{BOLD}Searching for Minecraft Java servers...{RESET}")
print("Scanning random IP addresses...")

try:
    total_servers_found = 0
    batch_counter = 0

    while True:
        # Scan a batch and count found servers
        servers_found = scan_batch()
        total_servers_found += servers_found
        batch_counter += 1

        # Show progress every 3 batches
        if batch_counter % 3 == 0:
            print(f"Processed {batch_counter * 1000} addresses... Found {total_servers_found} servers so far")

except KeyboardInterrupt:
    print(f"\n{BOLD}Search stopped. Found {total_servers_found} servers in total.{RESET}")
