# Cricket Highlights (TCP Streaming Prototype)

A simple **multi-user cricket highlights streaming** prototype built in **Python** using raw **TCP sockets** + **threads**.

- Run `server.py` to start a local highlights server
- Run one or more instances of `client.py` to connect as different users
- Each connected user can **toggle filters** (wicket/six/four/other) and will only receive events that match their active filters
- Event data is simulated in `events.py`

## Features

- Multi-client support (each client handled in its own thread)
- Real-time style event broadcasting (simulated delay between events)
- Per-user session state (each user has independent filters)
- Simple JSON-over-TCP protocol (newline-delimited JSON messages)
- Basic automated tests (`tests.py`) for filter/toggle logic

## Project Structure

- `server.py` — TCP server, session management, broadcasts events to clients
- `client.py` — interactive client (connects, listens for events, sends commands)
- `events.py` — sample `CRICKET_EVENTS` list used by the server
- `tests.py` — unit tests for filter logic and toggling behavior

## Requirements

- Python 3.10+ recommended (works on most Python 3 versions)
- No external dependencies (standard library only)

## How to Run

### 1) Start the server

Open a terminal:

```bash
python server.py
```

By default, the server listens on:

- Host: `127.0.0.1`
- Port: `9998`

(You can change these in both `server.py` and `client.py` if needed.)

### 2) Start one or more clients

In a new terminal (you can run multiple clients in multiple terminals):

```bash
python client.py
```

Each client will receive a welcome message and then can start interacting.

## Client Commands

Once connected, type:

- `t wicket` — toggle wicket highlights on/off  
- `t six` — toggle six highlights on/off  
- `t four` — toggle four highlights on/off  
- `t other` — toggle “other” events on/off  
- `status` — show your current active filters  
- `quit` — disconnect and exit  

### Notes on filtering
- Each user starts with default filters: `wicket`, `six`, `four`
- If your filter set becomes empty, you won’t see any events

## Running Tests

Run:

```bash
python tests.py
```

This runs a unit test suite for:
- `passes_filter` behavior
- toggle behavior (enabled/disabled)
- edge cases and simulated multi-user scenarios

## Example (Quick Demo)

1. Start `server.py`
2. Start `client.py` in two terminals
3. In client A, type: `t four` (turn off fours)
4. In client B, keep fours enabled
5. Watch how the two clients receive different event streams based on filters

## Future Improvements (Ideas)

- Add `requirements.txt` / packaging
- Add a proper message schema/versioning
- Add match selection, teams, innings, etc.
- Replace sample events with a real feed / API
- Add a GUI client (Tkinter/Web)

## License

Add a license of your choice (MIT/Apache-2.0/etc.). If you want, tell me which license you prefer and I’ll generate a `LICENSE` file too.