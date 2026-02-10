"""Main entry point for sima-gui."""

import signal
import sys


def main():
    """Main entry point."""
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Import here to avoid loading GTK before signal setup
    from .app import SimaApplication

    app = SimaApplication()

    try:
        app.run(sys.argv)
    except KeyboardInterrupt:
        app.process.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
