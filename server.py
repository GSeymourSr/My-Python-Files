import http.server
import socketserver
import os
import argparse
import sys
import functools # Required for setting the directory in Python < 3.7 style or cleaner handler

DEFAULT_PORT = 8000
DEFAULT_DIR = '.' # Current directory

def run_server(port, directory):
    """Starts the HTTP server."""

    # Ensure the directory exists
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.", file=sys.stderr)
        sys.exit(1)

    # --- Handler Configuration ---
    # SimpleHTTPRequestHandler serves files relative to the CWD *by default*.
    # To serve from a specific directory without changing the script's CWD,
    # we need to customize the handler. functools.partial is a clean way.

    Handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=os.path.abspath(directory) # Serve from the absolute path
    )

    # Use '0.0.0.0' to make the server accessible on your network
    # Use 'localhost' or '127.0.0.1' to restrict access to only your machine
    server_address = ('0.0.0.0', port)

    try:
        httpd = socketserver.TCPServer(server_address, Handler)
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"Error: Port {port} is already in use.", file=sys.stderr)
            print("Try using a different port with the --port option.", file=sys.stderr)
        else:
            print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


    print(f"\nServing files from directory: {os.path.abspath(directory)}")
    print(f"Server running at:")
    print(f"  - http://localhost:{port}")
    print(f"  - http://127.0.0.1:{port}")
    print(f"(And possibly on other network addresses like http://<your-ip>:{port})")
    print("\nPress Ctrl+C to stop the server.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopping...")
        httpd.server_close() # Cleanly close the server socket
        print("Server stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        httpd.server_close()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple Python HTTP server.")
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default=DEFAULT_DIR,
        help=f"Directory to serve files from (default: current directory '{DEFAULT_DIR}')"
    )

    args = parser.parse_args()
    run_server(args.port, args.dir)