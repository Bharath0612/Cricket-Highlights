# server.py
# Multi-user cricket highlights streaming server.
# Handles multiple clients concurrently using threads.
# Each client gets its own filter state stored in USER_SESSIONS.
#
# Usage:
#   python server.py
#
# Then connect clients with:
#   python client.py

import socket
import threading
import json
import time
import uuid

from events import CRICKET_EVENTS

# ─── Configuration ───────────────────────────────────────────────────────────

HOST = "127.0.0.1"   # Localhost — only accessible from this machine
PORT = 9998          # Arbitrary port; change if 9999 is in use
EVENT_DELAY = 2.0    # Seconds between events (simulates real-time pace)

# ─── Shared State ────────────────────────────────────────────────────────────
# USER_SESSIONS: maps user_id (str) → { "filters": set(), "socket": socket }
# LOCK: prevents two threads from editing USER_SESSIONS at the same time

USER_SESSIONS = {}
LOCK = threading.Lock()

# Valid filter names. Clients can only toggle these.
VALID_FILTERS = {"wicket", "six", "four", "other"}


# ─── Helper: Send a JSON message to one client ───────────────────────────────

def send_message(client_socket, data: dict):
    """Serialize data to JSON and send as a newline-terminated string."""
    try:
        message = json.dumps(data) + "\n"
        client_socket.sendall(message.encode("utf-8"))
    except (BrokenPipeError, OSError):
        # Client has disconnected; ignore silently
        pass


# ─── Helper: Check if an event passes a user's filter ───────────────────────

def passes_filter(event: dict, filters: set) -> bool:
    """
    Returns True if the event type is in the user's active filter set.
    An empty filter set means nothing is shown (user has toggled everything off).
    """
    if not filters:
        return False
    return event["type"] in filters


# ─── Handle incoming messages from one client ────────────────────────────────

def handle_client_messages(user_id: str, client_socket: socket.socket):
    """
    Runs in its own thread per client.
    Reads messages from the client (e.g., toggle requests) and updates
    that user's filter set in USER_SESSIONS.
    """
    buffer = ""
    while True:
        try:
            chunk = client_socket.recv(1024).decode("utf-8")
            if not chunk:
                # Empty string means the client disconnected
                break

            buffer += chunk
            # Messages are newline-delimited; process each complete line
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    send_message(client_socket, {
                        "type": "error",
                        "text": "Invalid JSON received by server."
                    })
                    continue

                action = msg.get("action")

                # ── Toggle a filter on/off ──
                if action == "toggle":
                    filter_name = msg.get("filter", "").lower()
                    if filter_name not in VALID_FILTERS:
                        send_message(client_socket, {
                            "type": "error",
                            "text": f"Unknown filter: '{filter_name}'. "
                                    f"Valid options: {sorted(VALID_FILTERS)}"
                        })
                        continue

                    with LOCK:
                        current_filters = USER_SESSIONS[user_id]["filters"]
                        if filter_name in current_filters:
                            current_filters.remove(filter_name)
                            action_word = "disabled"
                        else:
                            current_filters.add(filter_name)
                            action_word = "enabled"

                    send_message(client_socket, {
                        "type": "info",
                        "text": f"Filter '{filter_name}' {action_word}. "
                                f"Active: {sorted(current_filters)}"
                    })

                # ── Request current filter state ──
                elif action == "status":
                    with LOCK:
                        active = sorted(USER_SESSIONS[user_id]["filters"])
                    send_message(client_socket, {
                        "type": "info",
                        "text": f"Your active filters: {active}"
                    })

                else:
                    send_message(client_socket, {
                        "type": "error",
                        "text": f"Unknown action: '{action}'. "
                                "Use 'toggle' or 'status'."
                    })

        except (ConnectionResetError, OSError):
            break

    # ── Client disconnected: clean up session ──
    with LOCK:
        if user_id in USER_SESSIONS:
            del USER_SESSIONS[user_id]
    print(f"[Server] User {user_id[:8]} disconnected. "
          f"Active sessions: {len(USER_SESSIONS)}")


# ─── Broadcast events to all connected clients ───────────────────────────────

def broadcast_events():
    """
    Runs in its own thread.
    Iterates through CRICKET_EVENTS, pausing EVENT_DELAY seconds between each.
    For each event, checks every connected user's filter and sends only
    if the event type matches that user's active filters.
    """
    time.sleep(2)  # Give clients time to connect before events start
    print(f"[Server] Starting event broadcast ({len(CRICKET_EVENTS)} events)...")

    for event in CRICKET_EVENTS:
        time.sleep(EVENT_DELAY)

        with LOCK:
            # Snapshot current sessions to avoid issues if a client disconnects
            # mid-iteration
            sessions_snapshot = dict(USER_SESSIONS)

        if not sessions_snapshot:
            print("[Server] No clients connected; waiting...")
            continue

        for user_id, session in sessions_snapshot.items():
            if passes_filter(event, session["filters"]):
                send_message(session["socket"], {
                    "type": "event",
                    "event_type": event["type"],
                    "player":     event["player"],
                    "over":       event["over"],
                    "description": event["description"],
                })

    # Notify all connected clients that the match is over
    print("[Server] All events broadcast. Sending match-end signal.")
    with LOCK:
        sessions_snapshot = dict(USER_SESSIONS)

    for user_id, session in sessions_snapshot.items():
        send_message(session["socket"], {
            "type": "match_end",
            "text": "Match has ended. No more events."
        })


# ─── Accept new client connections ───────────────────────────────────────────

def accept_connections(server_socket: socket.socket):
    """
    Runs in the main thread.
    Accepts new TCP connections and registers each as a new user session.
    Spawns a dedicated message-handling thread per client.
    """
    print(f"[Server] Listening on {HOST}:{PORT}. Waiting for clients...")
    while True:
        try:
            client_socket, address = server_socket.accept()
        except OSError:
            break  # Server socket closed; exit cleanly

        user_id = str(uuid.uuid4())  # Unique ID for this user session

        with LOCK:
            USER_SESSIONS[user_id] = {
                "filters": {"wicket", "six", "four"},  # Default: show main highlights
                "socket":  client_socket,
            }

        print(f"[Server] New client from {address}. "
              f"User ID: {user_id[:8]}... "
              f"Active sessions: {len(USER_SESSIONS)}")

        # Send welcome message with the user's ID and default filters
        send_message(client_socket, {
            "type": "welcome",
            "user_id": user_id,
            "text": "Connected to Cricket Highlights Server!",
            "default_filters": ["wicket", "six", "four"],
            "help": (
                "Commands: 't wicket' | 't six' | 't four' | 't other' | 'status' | 'quit'"
            )
        })

        # Spawn a thread to handle incoming messages from this client
        msg_thread = threading.Thread(
            target=handle_client_messages,
            args=(user_id, client_socket),
            daemon=True  # Thread dies if main program exits
        )
        msg_thread.start()


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(50)  # Accept up to 50 queued connections

    # Start the event broadcaster in a background thread
    broadcast_thread = threading.Thread(target=broadcast_events, daemon=True)
    broadcast_thread.start()

    try:
        accept_connections(server_socket)
    except KeyboardInterrupt:
        print("\n[Server] Shutting down.")
    finally:
        server_socket.close()