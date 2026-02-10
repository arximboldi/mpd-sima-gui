"""Main entry point for sima-gui."""

import signal
import sys

from .tray import SimaTrayApp


def main():
    """Main entry point."""
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = SimaTrayApp()

    try:
        app.run()
    except KeyboardInterrupt:
        app.process.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
