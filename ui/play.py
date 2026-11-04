import argparse
from pathlib import Path
import uvicorn

SERVER_FOLDER = Path(__file__).resolve().parent / "server"

def main():
    parser = argparse.ArgumentParser(description="Start the poker UI server.")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    parser.add_argument("--reload", action="store_true",
                        help="restart the server whenever a Python file in ui/server changes")
    args = parser.parse_args()
    if args.reload:
        print("To see web app edits too, run npm run dev in ui/web and open the address it prints")
    else:
        print(f"Open http://127.0.0.1:{args.port} in your browser")
    # Only this computer can connect. The app goes by name because reloading has to import it
    # afresh on every restart.
    uvicorn.run("server.app:app", host="127.0.0.1", port=args.port, reload=args.reload,
                reload_dirs=[str(SERVER_FOLDER)] if args.reload else None)

if __name__ == "__main__":
    main()
