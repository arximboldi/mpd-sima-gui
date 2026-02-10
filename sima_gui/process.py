"""Process management for mpd-sima."""

import subprocess
import signal
import threading
from pathlib import Path
from typing import Callable

from .config import CONFIG_FILE, LOG_FILE, ensure_dirs


class SimaProcess:
    """Manages the mpd-sima subprocess."""

    def __init__(self, on_output: Callable[[str], None] | None = None):
        self._process: subprocess.Popen | None = None
        self._on_output = on_output
        self._output_thread: threading.Thread | None = None
        self._log_buffer: list[str] = []
        self._lock = threading.Lock()
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the process is currently running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def get_logs(self) -> list[str]:
        """Get the current log buffer."""
        with self._lock:
            return list(self._log_buffer)

    def clear_logs(self) -> None:
        """Clear the log buffer."""
        with self._lock:
            self._log_buffer.clear()

    def _read_output(self) -> None:
        """Read output from the process in a separate thread."""
        ensure_dirs()

        with open(LOG_FILE, "a") as log_file:
            while self._running and self._process:
                if self._process.stdout is None:
                    break

                line = self._process.stdout.readline()
                if not line:
                    # Check if process ended
                    if self._process.poll() is not None:
                        break
                    continue

                line_str = line.strip()
                if line_str:
                    # Write to log file
                    log_file.write(line_str + "\n")
                    log_file.flush()

                    # Add to buffer
                    with self._lock:
                        self._log_buffer.append(line_str)
                        # Keep only last 10000 lines
                        if len(self._log_buffer) > 10000:
                            self._log_buffer = self._log_buffer[-10000:]

                    # Notify callback
                    if self._on_output:
                        self._on_output(line_str)

    def start(self) -> bool:
        """Start the mpd-sima process."""
        if self.is_running:
            return True

        ensure_dirs()

        # Build command
        cmd = ["mpd-sima"]

        # Add config file if it exists
        if CONFIG_FILE.exists():
            cmd.extend(["-c", str(CONFIG_FILE)])

        try:
            self._running = True
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Start output reading thread
            self._output_thread = threading.Thread(target=self._read_output, daemon=True)
            self._output_thread.start()

            with self._lock:
                self._log_buffer.append(f"[sima-gui] Started mpd-sima (PID: {self._process.pid})")

            return True

        except FileNotFoundError:
            with self._lock:
                self._log_buffer.append("[sima-gui] Error: mpd-sima not found in PATH")
            self._running = False
            return False
        except Exception as e:
            with self._lock:
                self._log_buffer.append(f"[sima-gui] Error starting mpd-sima: {e}")
            self._running = False
            return False

    def stop(self) -> None:
        """Stop the mpd-sima process."""
        self._running = False

        if self._process is None:
            return

        if self._process.poll() is None:
            with self._lock:
                self._log_buffer.append(f"[sima-gui] Stopping mpd-sima (PID: {self._process.pid})")

            # Try graceful shutdown first
            self._process.terminate()

            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self._process.kill()
                self._process.wait()

            with self._lock:
                self._log_buffer.append("[sima-gui] mpd-sima stopped")

        self._process = None

        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=1)
        self._output_thread = None

    def restart(self) -> bool:
        """Restart the mpd-sima process."""
        self.stop()
        return self.start()

    def toggle(self) -> bool:
        """Toggle the process state. Returns new running state."""
        if self.is_running:
            self.stop()
            return False
        else:
            self.start()
            return True
