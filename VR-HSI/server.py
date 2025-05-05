# server.py
# local PC command: uvicorn server:app --host 0.0.0.0 --port 8000
# local network command: ws://10.150.52.215:8000/ws
# see apis running local command: ps aux | grep uvicorn  

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import asyncio
import json
from typing import List
import serial
import serial.tools.list_ports
import platform
import time
import atexit
import signal

# Global variable to store the serial connection
global_serial = None

def cleanup_serial():
    """
    Cleanup function to properly close the serial port
    """
    global global_serial
    if global_serial and global_serial.is_open:
        print("Cleaning up serial connection...")
        global_serial.close()
        print("Serial connection closed.")

def signal_handler(signum, frame):
    """
    Signal handler for graceful shutdown
    """
    print("\nReceived signal to terminate. Cleaning up...")
    cleanup_serial()
    exit(0)

# Register cleanup handlers
atexit.register(cleanup_serial)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events.
    Initializes the ConnectionManager and starts the periodic data sender.
    """
    print("Application startup")
    
    # Initialize the ConnectionManager and store it in app state for accessibility
    manager = ConnectionManager()
    app.state.manager = manager
    
    # Start the background task to send periodic data
    data_sender = asyncio.create_task(send_data(manager))
    
    try:
        yield
    finally:
        # Cancel the background task gracefully on shutdown
        data_sender.cancel()
        print("Application shutdown")

app = FastAPI(lifespan=lifespan)

class ConnectionManager:
    """
    Manages WebSocket connections and broadcasting messages to connected clients.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accepts a WebSocket connection and adds it to the active connections list.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        """
        Removes a WebSocket connection from the active connections list.
        """
        self.active_connections.remove(websocket)
        print(f"Client disconnected: {websocket.client}")

    async def broadcast(self, message: str):
        """
        Sends a message to all connected WebSocket clients.
        Removes clients that encounter errors during message sending.
        """
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message to {connection.client}: {e}")
                to_remove.append(connection)
        for connection in to_remove:
            self.disconnect(connection)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that manages client connections and keeps them alive.
    Receives and ignores incoming messages to maintain the connection.
    """
    manager: ConnectionManager = app.state.manager
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by receiving (and ignoring) messages from the client
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def find_emg_port():
    """
    Find the appropriate serial port for the EMG device.
    Returns the port name or None if not found.
    """
    system = platform.system()
    
    # List all available ports
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("No serial ports found!")
        return None
    
    print("\nAvailable ports:")
    for port in ports:
        print(f"- {port.device}: {port.description}")
    
    # Try to find the EMG device
    # Common identifiers for USB-to-Serial devices
    common_identifiers = ['USB', 'Serial', 'FTDI', 'CH340', 'CP210']
    
    for port in ports:
        # Check if any identifier is in the port description
        if any(identifier in port.description for identifier in common_identifiers):
            print(f"\nFound potential EMG device on port: {port.device}")
            return port.device
    
    # If no specific device found, return the first available port
    print(f"\nNo specific EMG device found. Using first available port: {ports[0].device}")
    return ports[0].device

async def send_data(manager):
    """
    Continuously read data from the EMG device and broadcast it to connected clients.
    """
    global global_serial
    port = None
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            if global_serial is None or not global_serial.is_open:
                if port is None:
                    port = find_emg_port()
                    if port is None:
                        print("No suitable port found. Retrying in 5 seconds...")
                        await asyncio.sleep(5)
                        continue
                
                # Try to close the port if it's busy
                try:
                    temp_ser = serial.Serial(port)
                    temp_ser.close()
                except:
                    pass
                
                print(f"Attempting to connect to {port}...")
                global_serial = serial.Serial(port=port, baudrate=115200, timeout=1)
                print(f"Successfully connected to {port}")
                retry_count = 0  # Reset retry count on successful connection
            
            if global_serial.in_waiting > 0:
                line = global_serial.readline()
                try:
                    decoded_line = line.decode('utf-8').strip()
                    emg_value = int(decoded_line)
                    
                    # Process EMG data
                    emg_data = 1 if emg_value > 100 else 0
                    print(f"Received EMG data: {emg_value} -> {emg_data}")
                    
                    # Broadcast the processed data
                    await manager.broadcast(str(emg_data))
                except ValueError as e:
                    print(f"Error decoding data: {e}")
                except Exception as e:
                    print(f"Error processing data: {e}")
            
            await asyncio.sleep(0.01)  # Small delay to prevent CPU overuse
            
        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            if global_serial and global_serial.is_open:
                global_serial.close()
            global_serial = None
            
            retry_count += 1
            if retry_count >= max_retries:
                print("Max retries reached. Resetting port detection...")
                port = None
                retry_count = 0
            
            print(f"Retrying in 5 seconds... (Attempt {retry_count}/{max_retries})")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            if global_serial and global_serial.is_open:
                global_serial.close()
            global_serial = None
            await asyncio.sleep(5)

if __name__ == "__main__":
    import sys
    import subprocess

    # Ensure pyngrok is installed
    try:
        from pyngrok import ngrok
    except ImportError:
        print("pyngrok not found, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
        from pyngrok import ngrok

    import uvicorn

    # Configure ngrok with authtoken
    ngrok.set_auth_token("2wecdhovZ3IDU2nSqZoYTZF9ozk_4a2QygnpmbPvquxroXtaT")

    # Start ngrok tunnel
    port = 8000
    public_url = ngrok.connect(port, "http").public_url
    print(f"ngrok tunnel established. Public URL: {public_url}/ws")
    print("You can share this URL with remote WebSocket clients.")

    # Start the FastAPI server
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)