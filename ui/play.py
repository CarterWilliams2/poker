import argparse
import uvicorn
from server.app import app

def main():
    parser = argparse.ArgumentParser(description="Start the poker UI server.")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    args = parser.parse_args()
    print(f"Deal a hand at http://127.0.0.1:{args.port}/api/deal")
    # Only this computer can connect.
    uvicorn.run(app, host="127.0.0.1", port=args.port)

if __name__ == "__main__":
    main()
