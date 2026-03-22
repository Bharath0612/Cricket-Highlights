# Commands once connected:
#   t wicket   → toggle wicket highlights on/off
#   t six      → toggle six highlights on/off
#   t four     → toggle four highlights on/off
#   t other    → toggle "other events" on/off
#   status     → show your current active filters
#   quit       → disconnect and exit

import socket
import threading
import json

HOST = "127.0.0.1"
PORT = 9998


# ─── Formatting helpers ───────────────────────────────────────────────────────

# Emoji labels for event types (purely cosmetic)
EVENT_ICONS = {
    "wicket": "🎯 WICKET",
    "six":    "💥 SIX",
    "four":   "🏏 FOUR",
    "other":  "📌 EVENT",
}


def format_event(data: dict) -> str:
    icon = EVENT_ICONS.get(data.get("event_type", "other"), "📌")
    return (
        f"\n  {icon} | Over {data['over']} | {data['player']}\n"
        f"  {data['description']}\n"
        f"  {'─' * 50}"
    )


# ─── Receive messages from server (runs in background thread) ─────────────────

def receive_messages(client_socket: socket.socket):
    """
    Continuously reads JSON messages from the server and prints them.
    Runs as a daemon thread alongside the main input-reading loop.
    """
    buffer = ""
    while True:
        try:
            chunk = client_socket.recv(4096).decode("utf-8")
            if not chunk:
                print("\n[Client] Server closed the connection.")
                break

            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "welcome":
                    print(f"\n{'=' * 54}")
                    print(f"  🏏 {msg['text']}")
                    print(f"  Your User ID : {msg['user_id'][:8]}...")
                    print(f"  Default filters: {msg['default_filters']}")
                    print(f"\n  {msg['help']}")
                    print(f"{'=' * 54}\n")

                elif msg_type == "event":
                    print(format_event(msg))

                elif msg_type == "info":
                    print(f"\n  ℹ  {msg['text']}\n")

                elif msg_type == "error":
                    print(f"\n  ⚠  ERROR: {msg['text']}\n")

                elif msg_type == "match_end":
                    print(f"\n  🏁 {msg['text']}")
                    print("  You may type 'quit' to exit.\n")

        except (ConnectionResetError, OSError):
            print("\n[Client] Lost connection to server.")
            break


# ─── Send a message to the server ────────────────────────────────────────────

def send_message(client_socket: socket.socket, data: dict):
    try:
        message = json.dumps(data) + "\n"
        client_socket.sendall(message.encode("utf-8"))
    except OSError:
        pass


# ─── Main: connect and start interactive input loop ──────────────────────────

def main():
    print(f"[Client] Connecting to {HOST}:{PORT}...")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("[Client] Could not connect. Is the server running?")
        return

    print("[Client] Connected! Waiting for server welcome message...\n")

    # Start background thread to receive events
    recv_thread = threading.Thread(
        target=receive_messages,
        args=(client_socket,),
        daemon=True
    )
    recv_thread.start()

    # ── Main input loop ──
    # Read commands from the user's keyboard and send to the server.
    print("  Type a command ('t wicket', 't six', 't four', 'status', 'quit'):\n")
    while True:
        try:
            raw = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw:
            continue

        if raw == "quit":
            print("[Client] Disconnecting...")
            break

        elif raw == "status":
            send_message(client_socket, {"action": "status"})

        elif raw.startswith("t "):
            # Toggle command: "t wicket", "t six", etc.
            parts = raw.split()
            if len(parts) == 2:
                filter_name = parts[1]
                send_message(client_socket, {
                    "action": "toggle",
                    "filter": filter_name
                })
            else:
                print("  Usage: t <filter>   e.g. t wicket")

        else:
            print(f"  Unknown command: '{raw}'. Try: t wicket | t six | status | quit")

    client_socket.close()
    print("[Client] Connection closed. Goodbye!")


if __name__ == "__main__":
    main()