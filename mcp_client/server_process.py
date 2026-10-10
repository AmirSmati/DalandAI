import subprocess
import sys
import time


class MCPServerProcess:

    def __init__(self):
        self.process = None

    def start(self):
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mcp_servers.email_server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )

        # Give Uvicorn time to start
        time.sleep(2)

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None