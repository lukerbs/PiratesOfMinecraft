import minecraft_launcher_lib
import subprocess
import json
import os
import sys
import re
import webbrowser
import random
import pyperclip
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
import time
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import asyncio
import threading
import concurrent.futures
from contextlib import contextmanager
import uuid
import requests
import datetime
from mcstatus import JavaServer

# Initialize Rich console for pretty output
console = Console()

# Constants
SERVERS_FILE = "discovered_servers.json"
MINECRAFT_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()
CLIENT_ID = "46061691-069a-400f-9cef-a636d076ccdb"  # You'll need to register an Azure application
REDIRECT_URL = "http://localhost:8000/callback"
# These are the correct endpoints for Minecraft authentication
AUTH_URL = "https://login.live.com/oauth20_authorize.srf"
TOKEN_URL = "https://login.live.com/oauth20_token.srf"

# Load or create the config file for storing authentication data
CONFIG_FILE = os.path.join(MINECRAFT_DIR, "launcher_config.json")

# Add these near the top of the file with other imports
callback_data = {"code": None}
app = FastAPI()


@app.get("/callback")
async def callback(code: str = None, state: str = None, error: str = None, error_description: str = None):
    """Handle the OAuth callback with detailed logging"""

    # Log all request data
    console.print("\n[yellow]Debug: OAuth Callback Data:[/yellow]")
    console.print(f"[yellow]Code:[/yellow] {code[:10]}..." if code else "None")
    console.print(f"[yellow]State:[/yellow] {state}")

    if error:
        console.print(f"[red]Error:[/red] {error}")
        console.print(f"[red]Error Description:[/red] {error_description}")
        callback_data["error"] = error
        callback_data["error_description"] = error_description
        return HTMLResponse(
            """
            <html>
                <body style="background: #2d2d2d; color: #ffffff; font-family: Arial; text-align: center; padding-top: 2em;">
                    <h1>Authentication Error</h1>
                    <p>There was an error during authentication. Please return to the launcher.</p>
                    <script>window.close()</script>
                </body>
            </html>
            """
        )

    # Store the code for the main application to use
    callback_data["code"] = code

    return HTMLResponse(
        """
        <html>
            <body style="background: #2d2d2d; color: #ffffff; font-family: Arial; text-align: center; padding-top: 2em;">
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to the launcher.</p>
                <script>window.close()</script>
            </body>
        </html>
        """
    )


@contextmanager
def run_auth_server():
    """Temporarily run the FastAPI server"""
    server = uvicorn.Server(config=uvicorn.Config(app=app, host="localhost", port=8000, log_level="error"))

    # Run server in a thread
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()

    try:
        yield
    finally:
        # Shutdown server
        server.should_exit = True
        thread.join()


def parse_minecraft_version(version_string):
    """Extract the base Minecraft version from server version string"""
    # Common server software prefixes to remove
    server_softwares = ["Paper", "Spigot", "Bukkit", "Forge", "Fabric", "Vanilla"]

    # First try to extract version using regex
    version_pattern = r"(?:[\w\s-]+)?(?:^|\s)(\d+\.\d+(?:\.\d+)?)"
    match = re.search(version_pattern, version_string)

    if match:
        return match.group(1)

    # If regex fails, try removing known server software names
    cleaned_version = version_string
    for software in server_softwares:
        cleaned_version = cleaned_version.replace(software, "").strip()

    # Return cleaned version or original if no modification was needed
    return cleaned_version if cleaned_version else version_string


def load_servers():
    """Load discovered servers from JSON file"""
    if not os.path.exists(SERVERS_FILE):
        console.print("[red]No servers file found. Please run search.py first to discover servers.[/red]")
        sys.exit(1)

    try:
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        console.print("[red]Error reading servers file. The file may be corrupted.[/red]")
        sys.exit(1)


def display_servers(servers_data):
    """Display servers in a pretty table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("Server Address", style="blue")
    table.add_column("Status", style="bold")
    table.add_column("Players", style="green")
    table.add_column("Version")
    table.add_column("Description")

    for idx, server in enumerate(servers_data["servers"], 1):
        # Get player count information
        current_players = server.get("players_online", 0)
        max_players = server.get("players_max", "?")

        # Determine server status based on player count
        if current_players > 0:
            status = "[green]Online[/green]"
            players = f"[green]{current_players}[/green]/{max_players}"
        else:
            # Check if we have timestamp to determine if server was ever reachable
            if server.get("timestamp", ""):
                status = "[yellow]Offline[/yellow]"
            else:
                status = "[red]Unknown[/red]"
            players = f"0/{max_players}"

        table.add_row(
            str(idx),
            server["address"],
            status,
            players,
            server.get("version", "Unknown"),
            (
                str(server.get("description", ""))[:50] + "..."
                if len(str(server.get("description", ""))) > 50
                else str(server.get("description", ""))
            ),
        )

    console.print(table)


def ensure_version_installed(version):
    """Ensure the required Minecraft version is installed"""
    with Progress() as progress:
        task = progress.add_task(f"[green]Installing Minecraft {version}...", total=100)

        def set_progress(value):
            progress.update(task, completed=value)

        def set_max(value):
            progress.update(task, total=value)

        callback = {"setProgress": set_progress, "setMax": set_max}

        minecraft_launcher_lib.install.install_minecraft_version(version, MINECRAFT_DIR, callback=callback)


def load_config():
    """Load the launcher configuration"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {"refresh_token": None, "username": None}
    return {"refresh_token": None, "username": None}


def save_config(config):
    """Save the launcher configuration"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def microsoft_login():
    """Handle Microsoft account login with no fallback to offline mode"""
    console.print("\n[yellow]Microsoft authentication is required for online play.[/yellow]")

    try:
        # First, let's examine the library function signature to ensure we're calling it correctly
        console.print("[blue]Initializing Microsoft authentication...[/blue]")

        # Get the login URL
        auth_url = minecraft_launcher_lib.microsoft_account.get_login_url(CLIENT_ID, REDIRECT_URL)

        console.print("[yellow]Debug: Generated OAuth URL[/yellow]")
        console.print(f"[yellow]Auth URL (truncated):[/yellow] {auth_url[:100]}...")

        # Reset callback data
        callback_data.clear()
        callback_data["code"] = None

        # Start temporary server and open browser
        with run_auth_server():
            webbrowser.open(auth_url)

            console.print("[blue]Waiting for Microsoft authentication...[/blue]")
            console.print("[yellow]Please complete the login in your browser[/yellow]")

            # Wait for callback with timeout
            timeout = 300  # 5 minutes timeout
            start_time = time.time()
            while not callback_data.get("code") and not callback_data.get("error"):
                if time.time() - start_time > timeout:
                    raise Exception("Authentication timed out")
                time.sleep(0.1)

            # Check for error
            if callback_data.get("error"):
                raise Exception(
                    f"Authentication error: {callback_data.get('error')} - {callback_data.get('error_description')}"
                )

            auth_code = callback_data["code"]
            console.print("[green]Authentication code received:[/green] " + auth_code[:10] + "...")

        # Now complete the authentication process
        console.print("[blue]Completing authentication process...[/blue]")

        # Inspect our auth_code to make sure it's valid
        console.print(f"[yellow]Auth code length: {len(auth_code)}[/yellow]")

        # Try a direct call to complete_login with the CORRECT parameter names
        try:
            # Based on the signature:
            # (client_id: str, client_secret: str | None, redirect_uri: str, auth_code: str, code_verifier: str | None = None)
            login_data = minecraft_launcher_lib.microsoft_account.complete_login(
                client_id=CLIENT_ID,
                client_secret=None,  # We don't have a client secret for public clients
                redirect_uri=REDIRECT_URL,  # Notice the "uri" not "url"
                auth_code=auth_code,
            )

            console.print("[green]Authentication successful![/green]")
            console.print(f"[blue]Logged in as: {login_data.get('name', 'Unknown')}[/blue]")

            # Save the refresh token if available
            if "refresh_token" in login_data:
                config = load_config()
                config["refresh_token"] = login_data["refresh_token"]
                config["username"] = login_data["name"]
                save_config(config)
                console.print("[green]Saved refresh token for future use[/green]")

            return login_data

        except Exception as e:
            console.print(f"[red]Authentication failed: {str(e)}[/red]")

            # Try manual token exchange with correct parameters
            console.print("[yellow]Attempting manual token exchange...[/yellow]")

            # Construct token request
            token_url = "https://login.live.com/oauth20_token.srf"
            token_data = {
                "client_id": CLIENT_ID,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URL,
            }

            # Make token request
            token_response = requests.post(token_url, data=token_data)
            console.print(f"[yellow]Token response status: {token_response.status_code}[/yellow]")

            if token_response.status_code == 200:
                ms_token = token_response.json()
                console.print("[green]Microsoft token obtained[/green]")

                # We got the Microsoft token, but we need to convert it to a Minecraft token
                # This would require implementing the Xbox Live and Minecraft authentication flow
                console.print(
                    "[yellow]Microsoft token obtained, but Xbox and Minecraft authentication required[/yellow]"
                )
                console.print(f"[yellow]Token contains keys: {list(ms_token.keys())}[/yellow]")

                # Without implementing the full flow, we need to use the library
                # Try one more direct attempt with correct parameters
                try:
                    # Use positional arguments in the correct order
                    login_data = minecraft_launcher_lib.microsoft_account.complete_login(
                        CLIENT_ID, None, REDIRECT_URL, auth_code  # client_secret
                    )
                    console.print("[green]Authentication successful![/green]")
                    return login_data
                except Exception as retry_error:
                    console.print(f"[red]Final authentication attempt failed: {str(retry_error)}[/red]")
                    raise Exception("Unable to complete Minecraft authentication flow")
            else:
                console.print(f"[red]Token exchange failed: {token_response.text}[/red]")
                raise Exception(f"Token exchange failed with status {token_response.status_code}")

    except Exception as e:
        console.print(f"[red]Authentication failed: {str(e)}[/red]")
        raise Exception("Microsoft authentication is required but failed. Cannot continue.")


def launch_minecraft(version, server_address, auth_data=None):
    """Launch Minecraft with the specified version and connect to server"""
    # Parse the version to get base Minecraft version
    base_version = parse_minecraft_version(version)
    console.print(f"[blue]Using Minecraft version: {base_version}[/blue]")

    if auth_data:
        # Use authenticated account
        options = {"username": auth_data["name"], "uuid": auth_data["id"], "token": auth_data["access_token"]}
    else:
        # Fallback to offline mode with custom username
        username = Prompt.ask("Enter your desired username", default="Player" + str(random.randint(100, 999)))
        options = minecraft_launcher_lib.utils.generate_test_options()
        options["username"] = username

    # Add server connection arguments
    host, port = server_address.split(":")
    options["gameArguments"] = ["--server", host, "--port", port]

    # Get the Minecraft command
    minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(base_version, MINECRAFT_DIR, options)

    # Launch Minecraft
    console.print(f"[green]Launching Minecraft {base_version}...[/green]")
    subprocess.run(minecraft_command, cwd=MINECRAFT_DIR)


def list_installed_versions():
    """List all installed Minecraft versions"""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Installed Versions")
    table.add_column("Type")
    table.add_column("Release Date")

    versions = minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR)

    if not versions:
        console.print("[yellow]No Minecraft versions installed yet.[/yellow]")
        return

    console.print("\n[bold green]Installed Minecraft Versions:[/bold green]")

    # Sort versions by release time, handling potential string or datetime objects
    def get_release_time(version):
        release_time = version.get("releaseTime", "")
        if isinstance(release_time, str):
            return release_time
        # If it's a datetime object, convert to ISO format string
        return release_time.isoformat() if hasattr(release_time, "isoformat") else ""

    for version in sorted(versions, key=get_release_time, reverse=True):
        # Get release date, handling both string and datetime objects
        release_time = version.get("releaseTime", "Unknown")
        if hasattr(release_time, "isoformat"):
            release_date = release_time.isoformat()[:10]  # Get just the date part
        else:
            release_date = str(release_time)[:10]  # Get first 10 chars if it's a string

        table.add_row(version.get("id", "Unknown"), version.get("type", "Unknown"), release_date)

    console.print(table)


def show_menu():
    """Display the main menu"""
    while True:
        console.print("\n[bold cyan]Pirates of Minecraft Launcher[/bold cyan]")
        console.print("\n1. [green]Join a server[/green]")
        console.print("2. [blue]List installed versions[/blue]")
        console.print("3. [blue]View servers with real-time player counts[/blue]")
        console.print("4. [yellow]Exit[/yellow]")

        choice = Prompt.ask("\nSelect an option", default="1")

        if choice == "1":
            join_server()
        elif choice == "2":
            list_installed_versions()
        elif choice == "3":
            view_servers()
        elif choice == "4":
            console.print("[yellow]Goodbye![/yellow]")
            sys.exit(0)
        else:
            console.print("[red]Invalid option. Please try again.[/red]")


def get_server_status(server_address):
    """Query a server to get real-time status information"""
    try:
        server = JavaServer.lookup(server_address, timeout=1)  # Shorter timeout for faster response
        status = server.status()
        return {
            "online": True,
            "players_online": status.players.online,
            "players_max": status.players.max,
            "version": status.version.name,
            "description": status.description,
            "latency": round(status.latency, 1),
        }
    except Exception:
        # Don't print the error message to avoid cluttering the console
        return {"online": False}


def refresh_server_data(servers_data):
    """Refresh all servers with current player counts using concurrent requests"""
    total_servers = len(servers_data["servers"])
    responsive_servers = 0
    offline_servers = 0

    # Create a lock for thread-safe counter updates
    counter_lock = threading.Lock()

    # Create a shared progress tracker
    progress_dict = {"completed": 0, "total": total_servers}

    # Use Progress to show status
    with Progress() as progress:
        refresh_task = progress.add_task("[blue]Refreshing server data...", total=total_servers)

        # Function to check a single server in a thread
        def check_server(server):
            nonlocal responsive_servers, offline_servers
            server_address = server["address"]

            try:
                status = get_server_status(server_address)

                with counter_lock:
                    if status["online"]:
                        server["players_online"] = status["players_online"]
                        server["players_max"] = status["players_max"]
                        responsive_servers += 1
                    else:
                        # Mark as offline but keep existing data
                        server["players_online"] = 0
                        offline_servers += 1

                    # Update progress
                    progress_dict["completed"] += 1
                    completion = progress_dict["completed"]
                    progress.update(
                        refresh_task,
                        completed=completion,
                        description=f"[green]Processed {completion}/{total_servers} servers",
                    )
            except Exception:
                with counter_lock:
                    # If refresh fails, set to 0 players
                    server["players_online"] = 0
                    offline_servers += 1

                    # Update progress
                    progress_dict["completed"] += 1
                    completion = progress_dict["completed"]
                    progress.update(
                        refresh_task,
                        completed=completion,
                        description=f"[green]Processed {completion}/{total_servers} servers",
                    )

        # Use ThreadPoolExecutor to query servers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all server checks to the thread pool
            futures = [executor.submit(check_server, server) for server in servers_data["servers"]]

            # Wait for all futures to complete
            concurrent.futures.wait(futures)

    # Sort servers by player count (highest first)
    servers_data["servers"] = sorted(servers_data["servers"], key=lambda x: x.get("players_online", 0), reverse=True)

    console.print(f"[green]Found {responsive_servers} active servers with players online[/green]")
    return servers_data


def join_server():
    """Handle server selection and joining with the official Minecraft launcher"""
    try:
        # Load servers
        console.print("[bold blue]Loading discovered servers...[/bold blue]")
        servers_data = load_servers()

        if not servers_data["servers"]:
            console.print("[red]No servers found in the database.[/red]")
            return

        # Always refresh server data with current player counts
        console.print("[blue]Getting real-time player counts...[/blue]")
        servers_data = refresh_server_data(servers_data)

        # Display servers
        display_servers(servers_data)

        # Get user selection
        while True:
            try:
                choice = int(Prompt.ask("\nEnter the number of the server you want to join", default="1"))
                if 1 <= choice <= len(servers_data["servers"]):
                    break
                console.print("[red]Invalid selection. Please choose a valid server number.[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number.[/red]")

        selected_server = servers_data["servers"][choice - 1]
        server_address = selected_server["address"]

        # Get real-time server status
        status = get_server_status(server_address)
        if status["online"]:
            console.print(
                f"[green]Server is online with {status['players_online']}/{status['players_max']} players[/green]"
            )
            console.print(f"[blue]Latency: {status['latency']}ms[/blue]")
            # Update version if needed
            version = status["version"]
        else:
            console.print("[yellow]Could not connect to server for status update. Using cached data.[/yellow]")
            version = selected_server["version"]

        # Copy server address to clipboard
        pyperclip.copy(server_address)
        console.print(f"[green]Server address '{server_address}' copied to clipboard![/green]")

        # Parse the version to get base Minecraft version
        base_version = parse_minecraft_version(version)
        console.print("")  # Empty line for spacing
        console.print("[blue]Server is running: " + version + "[/blue]")
        console.print("[blue]Using compatible Minecraft version: " + base_version + "[/blue]")

        # Ensure version is installed
        console.print("\n[bold blue]Checking Minecraft version " + base_version + "...[/bold blue]")
        ensure_version_installed(base_version)

        # Ask if user wants to use the official launcher or offline mode
        console.print("\n[yellow]CONNECTION OPTIONS:[/yellow]")
        console.print("1. [green]Use the official Minecraft launcher (uses your normal account)[/green]")
        console.print("2. [green]Launch in offline mode (some servers will reject this connection)[/green]")

        launcher_choice = Prompt.ask("Choose connection method", choices=["1", "2"], default="1")

        if launcher_choice == "1":
            # Create and use official launcher profile
            profile_name = f"Server_{choice}_{base_version}"
            console.print(f"[blue]Creating launcher profile for: {server_address}[/blue]")

            # Create a launcher profile for the official launcher
            launcher_profiles_path = os.path.join(MINECRAFT_DIR, "launcher_profiles.json")

            try:
                if os.path.exists(launcher_profiles_path):
                    with open(launcher_profiles_path, "r") as f:
                        profiles = json.load(f)
                else:
                    profiles = {"profiles": {}}

                # Generate a profile ID
                profile_id = str(uuid.uuid4())

                # Add our server profile
                profiles["profiles"][profile_id] = {
                    "name": profile_name,
                    "type": "custom",
                    "created": datetime.datetime.now().isoformat(),
                    "lastUsed": datetime.datetime.now().isoformat(),
                    "icon": "Grass",
                    "lastVersionId": base_version,
                    "gameDir": MINECRAFT_DIR,
                    "javaArgs": "-Xmx2G -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M",
                    "serverInfo": {"name": f"Server {choice}", "ip": server_address},
                }

                # Save the updated profiles
                with open(launcher_profiles_path, "w") as f:
                    json.dump(profiles, f, indent=2)

                console.print(f"[green]Created launcher profile for server {server_address}[/green]")

                # Launch the official Minecraft launcher
                import platform

                system = platform.system()

                launcher_path = None
                if system == "Windows":
                    launcher_path = os.path.expandvars("%PROGRAMFILES(X86)%\\Minecraft Launcher\\MinecraftLauncher.exe")
                    if not os.path.exists(launcher_path):
                        launcher_path = os.path.expandvars("%PROGRAMFILES%\\Minecraft Launcher\\MinecraftLauncher.exe")
                elif system == "Darwin":  # macOS
                    launcher_path = "/Applications/Minecraft.app/Contents/MacOS/launcher"
                elif system == "Linux":
                    launcher_path = "/usr/bin/minecraft-launcher"

                if launcher_path and os.path.exists(launcher_path):
                    console.print(f"[green]Launching official Minecraft launcher...[/green]")
                    console.print(
                        f"[yellow]Select the profile named '{profile_name}' to connect to the server[/yellow]"
                    )
                    # Use different approach based on OS
                    if system == "Darwin":  # macOS
                        # Use 'open' command for macOS
                        subprocess.Popen(["open", "-a", "Minecraft"])
                    else:
                        # Use direct path for Windows/Linux
                        subprocess.Popen([launcher_path])
                else:
                    console.print("[red]Could not find the official Minecraft launcher.[/red]")
                    console.print("[yellow]Please install the official launcher or use offline mode.[/yellow]")
                    if Confirm.ask("[yellow]Try offline mode instead?[/yellow]", default=True):
                        launcher_choice = "2"
                    else:
                        return
            except Exception as e:
                console.print(f"[red]Error creating launcher profile: {str(e)}[/red]")
                if Confirm.ask("[yellow]Try offline mode instead?[/yellow]", default=True):
                    launcher_choice = "2"
                else:
                    return

        # If offline mode was chosen (or fallback from failed official launcher)
        if launcher_choice == "2":
            # Set up offline mode with custom username
            username = Prompt.ask("Enter your desired username", default="Player" + str(random.randint(100, 999)))
            console.print(f"[yellow]Launching Minecraft in offline mode as: {username}[/yellow]")

            # Generate offline options
            options = minecraft_launcher_lib.utils.generate_test_options()
            options["username"] = username

            # Add server connection arguments
            host, port = server_address.split(":")
            options["gameArguments"] = ["--server", host, "--port", port]

            # Get the Minecraft command
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                base_version, MINECRAFT_DIR, options
            )

            # Launch Minecraft
            console.print(f"[green]Launching Minecraft {base_version}...[/green]")
            subprocess.run(minecraft_command, cwd=MINECRAFT_DIR)

    except Exception as e:
        console.print(f"\n[red]Error joining server: {str(e)}[/red]")
        return


def create_official_launcher_profile(server_address, version):
    """Create a profile in the official launcher for this server"""
    profile_name = f"Server_{server_address.split(':')[0]}"

    # Path to profiles file
    profiles_path = os.path.join(MINECRAFT_DIR, "launcher_profiles.json")

    try:
        if os.path.exists(profiles_path):
            with open(profiles_path, "r") as f:
                profiles = json.load(f)
        else:
            profiles = {"profiles": {}}

        # Generate a profile ID
        profile_id = str(uuid.uuid4())

        # Add our profile
        profiles["profiles"][profile_id] = {
            "name": profile_name,
            "type": "custom",
            "created": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "lastVersionId": version,
            "lastUsed": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "icon": "Grass",
            "serverInfo": {"name": "Minecraft Server", "ip": server_address},
        }

        # Save updated profiles
        with open(profiles_path, "w") as f:
            json.dump(profiles, f, indent=2)

        return profile_name
    except Exception as e:
        console.print(f"[red]Error creating launcher profile: {str(e)}[/red]")
        return None


def view_servers():
    """View available servers with refreshed player counts"""
    try:
        # Load servers
        console.print("[bold blue]Loading discovered servers...[/bold blue]")
        servers_data = load_servers()

        if not servers_data["servers"]:
            console.print("[red]No servers found in the database.[/red]")
            return

        # Always refresh server data with current player counts
        servers_data = refresh_server_data(servers_data)

        # Display servers
        display_servers(servers_data)

        # Wait for user to press Enter before returning to menu
        Prompt.ask("[yellow]Press Enter to return to menu[/yellow]", default="")

    except Exception as e:
        console.print(f"\n[red]Error viewing servers: {str(e)}[/red]")
        return


def main():
    while True:
        try:
            show_menu()
        except KeyboardInterrupt:
            console.print("\n[yellow]Launcher terminated by user.[/yellow]")
            break
        except Exception as e:
            console.print("\n[red]An unexpected error occurred: " + str(e) + "[/red]")
            # Add a small delay before showing the menu again
            time.sleep(1)


if __name__ == "__main__":
    main()
