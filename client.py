from langchain_mcp_adapters.client import MultiServerMCPClient

from pathlib import Path

BASE_DIR = Path(__file__).parent
SERVER_DIR = BASE_DIR / "server"

# Add parent directory to PYTHONPATH so 'core' can be found
SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "uv",
        "env": {
            "PYTHONPATH": str(BASE_DIR)  # ← Add this!
        },
        "args": [
            "--directory",
            str(SERVER_DIR),
            "run",
            "fastmcp",
            "run",
            "local_server.py"
        ]
    }
}


def get_client_tools():
    client = MultiServerMCPClient(SERVERS)
    tools = client.get_tools()

    return tools