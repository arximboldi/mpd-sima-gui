"""Main entry point for sima-gui."""

import sys


def main():
    """Main entry point."""
    # Import here to avoid loading GTK before we're ready
    from .app import SimaApplication

    app = SimaApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
