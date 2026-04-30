import json
import os
import select
import subprocess
import time
from pathlib import Path

IN_FILE = Path("bridge/incoming_from_chatgpt.json")
OUT_FILE = Path("bridge/outgoing_to_chatgpt.json")
STATE_FILE = Path("bridge/bridge_daemon_state.json")
DECISION_FILE = Path("bridge/decision_required.json")

POLL_INTERVAL = 0.5
PROJECT_ROOT = Path("/home/chris/jarvis")
HOME_DIR = Path("/home/chris")
JARVIS_CMD = [str(PROJECT_ROOT / "venv/bin/python"), "jarvis.py"]


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default or {}


def write_json_atomic(path, data):
    """Write JSON atomically via a temp file to avoid corrupt reads mid-write."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(path)


def clear_file(path):
    write_json_atomic(path, {})


def decision_pending():
    data = read_json(DECISION_FILE, {})
    return bool(data and data != {})


def clear_decision():
    clear_file(DECISION_FILE)


def load_state():
    return read_json(STATE_FILE, {}) or {"processed_keys": []}


def save_state(state):
    write_json_atomic(STATE_FILE, state)


class JarvisSession:
    def __init__(self):
        self.proc = None

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        if self.is_running():
            return

        self.proc = subprocess.Popen(
            JARVIS_CMD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
            text=False,
            bufsize=0,
        )

        # Drain startup banner/prompt with a short quiet period
        self._read_until_quiet_or_prompt(timeout=10, quiet_period=1.5)
        time.sleep(0.5)  # ensure Jarvis is fully ready

    def stop(self):
        if not self.is_running():
            self.proc = None
            return

        try:
            if self.proc.stdin:
                self.proc.stdin.write(b"exit\n")
                self.proc.stdin.flush()
            time.sleep(0.5)
        except Exception:
            pass

        if self.is_running():
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                pass

        if self.is_running():
            try:
                self.proc.kill()
            except Exception:
                pass

        self.proc = None

    def send_command(self, command, timeout=60):
        self.start()

        if not self.is_running():
            return "[ERROR] Jarvis session is not running"

        if self.proc.stdin is None:
            return "[ERROR] Jarvis stdin unavailable"

        try:
            self.proc.stdin.write((command.strip() + "\n").encode("utf-8"))
            self.proc.stdin.flush()

            # Small settle delay so Jarvis has time to start producing output
            time.sleep(2.0)

            # Wait until Jarvis finishes and output goes quiet
            output = self._read_until_quiet_or_prompt(timeout=timeout, quiet_period=2.5)

        except Exception as e:
            return f"[ERROR] {e}"

        return output.strip() if output.strip() else "[NO OUTPUT]"

    def _read_until_quiet_or_prompt(self, timeout=120, quiet_period=2.5):
        """
        Reads stdout from Jarvis until no new output has appeared for quiet_period
        seconds, or until timeout is reached. Returns all captured output.
        """
        if not self.is_running() or self.proc.stdout is None:
            return ""

        fd = self.proc.stdout.fileno()
        chunks = []
        start_time = time.time()
        last_data_time = time.time()

        while time.time() - start_time < timeout:
            if not self.is_running():
                break

            ready, _, _ = select.select([fd], [], [], 0.5)
            if ready:
                try:
                    data = os.read(fd, 4096)
                except BlockingIOError:
                    data = b""

                if data:
                    decoded = data.decode("utf-8", errors="replace")
                    chunks.append(decoded)
                    last_data_time = time.time()

            if time.time() - last_data_time >= quiet_period:
                break

        return "".join(chunks)


def run_terminal(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(HOME_DIR),
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "[NO OUTPUT]"
    except Exception as e:
        return f"[ERROR] {e}"


def main():
    state = load_state()
    processed_keys = set(state.get("processed_keys", []))
    jarvis = JarvisSession()

    print("Bridge daemon running.")
    print(f"Watching: {IN_FILE.resolve()}")
    print(f"Jarvis python: {JARVIS_CMD[0]}")

    while True:
        try:
            if not IN_FILE.exists():
                time.sleep(POLL_INTERVAL)
                continue

            raw = IN_FILE.read_text().strip()
            if not raw or raw == "{}":
                time.sleep(POLL_INTERVAL)
                continue

            data = read_json(IN_FILE, {})
            if not data:
                time.sleep(POLL_INTERVAL)
                continue

            key = data.get("dedupe_key", "").strip()
            command = data.get("command", "").strip()
            mode = data.get("mode", "jarvis").strip()

            if not command:
                clear_file(IN_FILE)
                time.sleep(POLL_INTERVAL)
                continue

            if command.lower() == "approve":
                clear_decision()
                print("[DAEMON] Decision gate cleared")
                write_json_atomic(
                    OUT_FILE,
                    {
                        "text": "[APPROVED] Decision gate cleared.",
                        "timestamp": time.time(),
                        "dedupe_key": key,
                    },
                )
                if key:
                    processed_keys.add(key)
                    save_state({"processed_keys": sorted(processed_keys)})
                clear_file(IN_FILE)
                time.sleep(POLL_INTERVAL)
                continue

            if decision_pending():
                print("[DAEMON] Decision pending; command paused")
                time.sleep(POLL_INTERVAL)
                continue

            if key and key in processed_keys:
                print(f"[DAEMON] Duplicate skipped ({mode}): {command}")
                clear_file(IN_FILE)
                time.sleep(POLL_INTERVAL)
                continue

            print(f"[DAEMON] Received ({mode}): {command}")

            if mode == "jarvis":
                output = jarvis.send_command(command)
            else:
                jarvis.stop()
                output = run_terminal(command)

            write_json_atomic(
                OUT_FILE,
                {
                    "text": output,
                    "timestamp": time.time(),
                    "dedupe_key": key,
                },
            )

            print(f"[DAEMON] Output written ({len(output)} chars)")

            if key:
                processed_keys.add(key)
                save_state({"processed_keys": sorted(processed_keys)})

            clear_file(IN_FILE)

        except Exception as e:
            print(f"[DAEMON ERROR] {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
