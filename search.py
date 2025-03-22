from mcstatus import JavaServer
import concurrent.futures
import random
import time
import socket
import threading
import json
import os

# Set a reasonable timeout for connections
socket.setdefaulttimeout(1.5)

# Create a lock for thread-safe file writing
file_lock = threading.Lock()

# ANSI color codes for prettier output
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"

# JSON file for storing servers
SERVERS_FILE = "discovered_servers.json"


def load_or_create_json():
    """Load existing JSON file or create new one with empty list"""
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"servers": [], "total_count": 0}
    return {"servers": [], "total_count": 0}


def is_reserved_ip(first, second, third, fourth):
    """Check if an IP address falls within reserved ranges"""
    # Private network ranges
    if first == 10:  # 10.0.0.0/8
        return True
    if first == 172 and 16 <= second <= 31:  # 172.16.0.0/12
        return True
    if first == 192 and second == 168:  # 192.168.0.0/16
        return True

    # Loopback
    if first == 127:  # 127.0.0.0/8
        return True

    # Link-local
    if first == 169 and second == 254:  # 169.254.0.0/16
        return True

    # IANA reserved
    if first == 0:  # 0.0.0.0/8
        return True
    if first == 100 and 64 <= second <= 127:  # 100.64.0.0/10 (CGN)
        return True
    if first == 192 and second == 0 and third == 0:  # 192.0.0.0/24
        return True
    if first == 192 and second == 0 and third == 2:  # 192.0.2.0/24 (TEST-NET-1)
        return True
    if first == 192 and second == 88 and third == 99:  # 192.88.99.0/24 (6to4 relay)
        return True
    if first == 198 and (second == 18 or second == 19):  # 198.18.0.0/15 (Benchmarking)
        return True
    if first == 198 and second == 51 and third == 100:  # 198.51.100.0/24 (TEST-NET-2)
        return True
    if first == 203 and second == 0 and third == 113:  # 203.0.113.0/24 (TEST-NET-3)
        return True

    # Multicast
    if 224 <= first <= 239:  # 224.0.0.0/4
        return True

    # Broadcast
    if first == 255 and second == 255 and third == 255 and fourth == 255:
        return True

    # Reserved for future use
    if 240 <= first <= 255:  # 240.0.0.0/4
        return True

    return False


def get_random_address():
    """Generate a random IP address using only valid public IP ranges"""
    while True:
        first = random.randint(1, 223)  # Avoid 224-255 (multicast and reserved)
        second = random.randint(0, 255)
        third = random.randint(0, 255)
        fourth = random.randint(0, 255)

        if not is_reserved_ip(first, second, third, fourth):
            ip = f"{first}.{second}.{third}.{fourth}"
            port = 25565  # Default Minecraft port
            return f"{ip}:{port}"


def query_server(address):
    """Query a Java edition server"""
    try:
        server = JavaServer.lookup(address, timeout=1)
        try:
            # Try status protocol first (faster)
            status = server.status()
            server_info = {
                "address": address,
                "type": "status",
                "players_online": status.players.online,
                "players_max": status.players.max,
                "version": status.version.name,
                "description": status.description,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            # Store these temporarily for console output only
            players_online = status.players.online
            latency = round(status.latency, 1)
        except Exception as e:
            print(f"Error querying status for {address}: {e}")
            try:
                # Fall back to query protocol if status fails
                query = server.query()
                server_info = {
                    "address": address,
                    "type": "query",
                    "players_online": query.players.online,
                    "players_max": query.players.max,
                    "version": query.software.version,
                    "description": query.motd.to_minecraft(),
                    "software": query.software.brand,
                    "plugins_count": len(query.software.plugins),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                # Store this temporarily for console output only
                players_online = query.players.online
            except Exception as e:
                print(f"Error querying query for {address}: {e}")
                return False

        # Write to JSON file when a server is found
        with file_lock:
            data = load_or_create_json()
            data["servers"].append(server_info)
            data["total_count"] = len(data["servers"])
            with open(SERVERS_FILE, "w") as f:
                json.dump(data, f, indent=2)

        # Print a more noticeable alert with server info
        print(f"\n{GREEN}{BOLD}🎮 SERVER FOUND! {address} ✅{RESET}")
        print(f"{GREEN}Players: {players_online}/{server_info['players_max']}")
        print(f"Version: {server_info['version']}")
        if server_info["type"] == "query":
            print(f"Software: {server_info['software']} with {server_info['plugins_count']} plugins")
        print(f"Description: {server_info['description']}")
        if server_info["type"] == "status":
            print(f"Latency: {latency}ms{RESET}\n")
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
