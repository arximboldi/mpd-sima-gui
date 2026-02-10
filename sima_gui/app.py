"""Main GTK4/Adwaita application for sima-gui."""

import signal
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

from .process import SimaProcess
from .settings_dialog import SettingsWindow
from .log_viewer import LogViewer
from .tray import StatusIcon
from .config import ensure_dirs


class SimaApplication(Adw.Application):
    """Main application for sima-gui."""

    def __init__(self):
        super().__init__(
            application_id="io.github.sima_gui",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

        self.process = SimaProcess()
        self._window = None
        self._log_viewer = None
        self._status_icon = None
        self._enabled = True
        self._first_activation = True

        # Connect signals
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

        # Handle SIGINT/SIGTERM for clean shutdown
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self._on_signal)
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._on_signal)

    def _on_signal(self):
        """Handle termination signals."""
        self.quit()
        return GLib.SOURCE_REMOVE

    def _on_activate(self, app):
        """Handle application activation."""
        ensure_dirs()

        # Create status icon on first activation
        if self._status_icon is None:
            self._status_icon = StatusIcon(self)
            # Hold the application so it doesn't quit when window closes
            self.hold()

        # On first activation, just start the service (don't show window)
        if self._first_activation:
            self._first_activation = False
            # Start the process
            if self._enabled:
                self.process.start()
                self._update_status()
            return

        # On subsequent activations (e.g., running command again), show settings
        self.show_settings()

    def _on_shutdown(self, app):
        """Handle application shutdown."""
        self.process.stop()
        if self._status_icon:
            self._status_icon.cleanup()

    def _update_status(self):
        """Update status in window and tray."""
        running = self.process.is_running

        if self._window and self._window.is_visible():
            self._window.update_status(running)

        if self._status_icon:
            self._status_icon.update_icon(running)

    def show_settings(self):
        """Show the settings window."""
        if self._window is None:
            self._window = MainWindow(self)
            self._window.connect("close-request", self._on_window_close)

        self._window.update_status(self.process.is_running)
        self._window.set_enabled(self._enabled)
        self._window.present()

    def _on_window_close(self, window):
        """Handle window close - hide instead of quit."""
        window.set_visible(False)
        return True  # Prevent destruction

    def show_logs(self):
        """Show the log viewer."""
        if self._log_viewer is None:
            self._log_viewer = LogViewer(
                self,
                get_logs_callback=self.process.get_logs,
            )
        self._log_viewer.present()

    def toggle_service(self, enabled: bool):
        """Toggle the service state."""
        self._enabled = enabled

        if enabled:
            self.process.start()
        else:
            self.process.stop()

        self._update_status()

        # Sync window toggle if visible
        if self._window and self._window.is_visible():
            self._window.set_enabled(enabled)

        # Sync tray checkbox
        if self._status_icon:
            self._status_icon.set_enabled(enabled)

    def is_enabled(self) -> bool:
        """Check if service is enabled."""
        return self._enabled

    def on_settings_applied(self):
        """Handle settings being applied."""
        if self._enabled:
            self.process.restart()
            self._update_status()


class MainWindow(SettingsWindow):
    """Main window combining status and settings."""

    def __init__(self, app: SimaApplication):
        super().__init__(app)
        self._app = app

        # Modify the main page to add status section
        self._add_status_section()

    def _add_status_section(self):
        """Add a status section to the main page."""
        # Use the stored reference from parent class
        box = self._main_box

        # Create status group and insert at the top
        status_group = Adw.PreferencesGroup()

        # Service status banner
        self.status_banner = Adw.Banner(
            title="mpd-sima is running",
            revealed=False,
        )
        self.status_banner.set_button_label(None)

        # Enable switch row
        self.enable_row = Adw.SwitchRow(
            title="Enable mpd-sima",
            subtitle="Automatically queue similar tracks",
            active=True,
        )
        self.enable_row.connect("notify::active", self._on_enable_toggled)
        status_group.add(self.enable_row)

        # Logs row
        logs_row = Adw.ActionRow(
            title="View Logs",
            subtitle="See mpd-sima activity",
            activatable=True,
        )
        logs_row.add_prefix(Gtk.Image(icon_name="utilities-terminal-symbolic"))
        logs_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        logs_row.connect("activated", self._on_show_logs)
        status_group.add(logs_row)

        # Insert at the beginning
        box.prepend(status_group)
        box.prepend(self.status_banner)

        # Add some spacing
        status_group.set_margin_bottom(12)

    def _on_enable_toggled(self, row, pspec):
        """Handle enable toggle."""
        enabled = row.get_active()
        self._app.toggle_service(enabled)

    def _on_show_logs(self, row):
        """Show the log viewer."""
        self._app.show_logs()

    def set_enabled(self, enabled: bool):
        """Set enabled state without triggering callback."""
        self.enable_row.handler_block_by_func(self._on_enable_toggled)
        self.enable_row.set_active(enabled)
        self.enable_row.handler_unblock_by_func(self._on_enable_toggled)

    def update_status(self, running: bool):
        """Update the status display."""
        if running:
            self.status_banner.set_title("mpd-sima is running")
            self.status_banner.add_css_class("success")
            self.status_banner.remove_css_class("error")
        else:
            self.status_banner.set_title("mpd-sima is stopped")
            self.status_banner.remove_css_class("success")
            self.status_banner.add_css_class("error")

        self.status_banner.set_revealed(True)
