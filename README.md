# EMG Data Streaming Server

A real-time EMG (Electromyography) data streaming server built with FastAPI and WebSocket. This server reads EMG data from a serial device and broadcasts it to connected clients in real-time.

## Features

- Real-time EMG data streaming via WebSocket
- Automatic serial port detection
- Cross-platform support (Windows, macOS, Linux)
- Automatic ngrok tunnel creation for remote access
- Robust error handling and reconnection logic
- Support for multiple simultaneous client connections

## Prerequisites

- Python 3.7+
- EMG device connected via USB
- ngrok account (for remote access)

## Installation

1. Clone the repository:
   ```bash
   git clone [your-repo-url]
   cd [repo-name]
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure ngrok (optional, for remote access):
   - Sign up for a free ngrok account at https://ngrok.com
   - Get your authtoken from the ngrok dashboard
   - Update the authtoken in `server.py`

## Usage

1. Connect your EMG device to your computer

2. Start the server:
   ```bash
   cd VR-HSI
   python server.py
   ```

3. The server will:
   - Automatically detect available serial ports
   - Connect to the EMG device
   - Create an ngrok tunnel (if configured)
   - Start streaming data

4. Connect clients using the WebSocket URL:
   - Local: `ws://localhost:8000/ws`
   - Remote: Use the ngrok URL provided in the console

## Data Format

The server broadcasts binary data (0 or 1) based on EMG threshold:
- 0: EMG value below threshold
- 1: EMG value above threshold

## Development

- Server runs on port 8000 by default
- WebSocket endpoint: `/ws`
- Serial communication: 115200 baud rate

## License

[Your chosen license]

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
