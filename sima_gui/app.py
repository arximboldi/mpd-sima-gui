"""Main GTK4/Adwaita application for sima-gui."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

from .process import SimaProcess
from .settings_dialog import SettingsWindow
from .log_viewer import LogViewer
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

        # Connect signals
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

    def _on_activate(self, app):
        """Handle application activation."""
        ensure_dirs()

        if self._window is None:
            self._window = MainWindow(self)
            self._window.set_apply_callback(self._on_settings_applied)

        self._window.present()

        # Start the process if enabled
        if self._window.is_enabled():
            self.process.start()
            self._window.update_status(True)

    def _on_shutdown(self, app):
        """Handle application shutdown."""
        self.process.stop()

    def _on_settings_applied(self):
        """Handle settings being applied."""
        if self._window and self._window.is_enabled():
            self.process.restart()
            self._window.update_status(self.process.is_running)

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
        if enabled:
            self.process.start()
        else:
            self.process.stop()

        if self._window:
            self._window.update_status(self.process.is_running)


class MainWindow(SettingsWindow):
    """Main window combining status and settings."""

    def __init__(self, app: SimaApplication):
        super().__init__(app)
        self._app = app
        self._enabled = True

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
        self._enabled = row.get_active()
        self._app.toggle_service(self._enabled)

    def _on_show_logs(self, row):
        """Show the log viewer."""
        self._app.show_logs()

    def is_enabled(self) -> bool:
        """Check if service is enabled."""
        return self._enabled

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
