# Pirates of Minecraft

A set of Python tools for finding and connecting to public Minecraft servers.

## Features

- **Server Discovery**: Scan random IP addresses to find open Minecraft servers using `search.py`
- **Server Browser**: View and manage discovered servers with real-time player counts
- **Launcher**: Connect to servers using either the official Minecraft launcher or offline mode
- **Authentication**: Microsoft account authentication for online play

## Getting Started

### Installing Dependencies

1. Clone this repository
2. Install dependencies using pip:

```bash
pip install -r requirements.txt
```

Or install dependencies individually:

```bash
pip install mcstatus minecraft-launcher-lib fastapi uvicorn rich pyperclip
```

### Discovering Servers

Run the server discovery tool to find Minecraft servers:

```bash
python search.py
```

The tool will scan random IP addresses and save discovered servers to `discovered_servers.json`. Let it run as long as you like - the longer it runs, the more servers it will find.

### Launching Minecraft and Connecting to Servers

Once you've discovered some servers, you can browse and connect to them:

```bash
python launcher.py
```

The launcher provides the following options:
1. Join a server
2. List installed Minecraft versions
3. View servers with real-time player counts

## How It Works

- `search.py` uses the mcstatus library to scan random IP addresses, filtering out reserved ranges
- `launcher.py` provides a rich UI for browsing servers and launching Minecraft
- Servers are stored in `discovered_servers.json`
- The launcher can create profiles for the official Minecraft launcher or launch in offline mode

## Requirements

- Python 3.6+
- Minecraft Java Edition (installed via the official launcher)
- Internet connection




