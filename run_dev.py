import sys
import os
import subprocess
import time

def main():
    # Detect absolute paths
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    
    # Path to local Python environment's uvicorn
    if sys.platform == "win32":
        uvicorn_bin = os.path.join(root_dir, ".venv", "Scripts", "uvicorn.exe")
    else:
        uvicorn_bin = os.path.join(root_dir, ".venv", "bin", "uvicorn")

    # If virtual environment doesn't exist, fall back to global uvicorn
    if not os.path.exists(uvicorn_bin):
        uvicorn_bin = "uvicorn"
        
    print("🚀 Starting FastAPI backend and Vite frontend concurrently...")
    
    backend_cmd = [uvicorn_bin, "app.main:app", "--reload", "--port", "8000"]
    
    # On Windows, npm is a cmd file, so we need shell=True
    use_shell = sys.platform == "win32"
    if use_shell:
        frontend_cmd = ["cmd", "/c", "npm run dev"]
    else:
        frontend_cmd = ["npm", "run", "dev"]

    backend_proc = None
    frontend_proc = None

    try:
        # Start backend
        print(f"Starting Backend: {' '.join(backend_cmd)}")
        backend_proc = subprocess.Popen(
            backend_cmd, 
            cwd=root_dir,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Give backend a moment to bind to the port
        time.sleep(1)
        
        # Start frontend
        print(f"Starting Frontend: npm run dev (in {frontend_dir})")
        frontend_proc = subprocess.Popen(
            frontend_cmd, 
            cwd=frontend_dir,
            shell=use_shell,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Keep running and monitor processes
        while True:
            # Check if any process has exited early
            if backend_proc.poll() is not None:
                print("⚠️ Backend server exited unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("⚠️ Frontend server exited unexpectedly.")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping servers gracefully...")
    finally:
        # Clean shutdown
        if backend_proc and backend_proc.poll() is None:
            print("Terminating Backend...")
            backend_proc.terminate()
            backend_proc.wait(timeout=5)
            
        if frontend_proc and frontend_proc.poll() is None:
            print("Terminating Frontend...")
            # On Windows, npm spawns child processes, so we need to kill the tree
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                frontend_proc.terminate()
                frontend_proc.wait(timeout=5)
        print("Done. Both servers stopped.")

if __name__ == "__main__":
    main()
