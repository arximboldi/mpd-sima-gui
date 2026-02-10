# Copyright (c) 2026 Juan Pedro Bolívar Puente
# SPDX-License-Identifier: MIT

"""Main entry point for mpd-sima-gui."""

import sys


def main():
    """Main entry point."""
    # Import here to avoid loading GTK before we're ready
    from .app import SimaApplication

    app = SimaApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
