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
from .config import ensure_dirs, CONFIG_FILE


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
        self._config_viewer = None
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

    def show_config(self):
        """Show the config viewer."""
        if self._config_viewer is None:
            self._config_viewer = ConfigViewer(self)
        self._config_viewer.load_config()
        self._config_viewer.present()

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


class ConfigViewer(Adw.Window):
    """Config viewer window."""

    def __init__(self, app: Adw.Application):
        super().__init__(
            application=app,
            title="Configuration",
            default_width=600,
            default_height=400,
        )

        self._build_ui()
        self.connect("close-request", self._on_close)

    def _on_close(self, window):
        """Hide on close instead of destroying."""
        window.set_visible(False)
        return True

    def _build_ui(self):
        """Build the config viewer UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Open config file button
        open_button = Gtk.Button(icon_name="folder-open-symbolic")
        open_button.set_tooltip_text("Open config folder")
        open_button.connect("clicked", self._on_open_folder)
        header.pack_start(open_button)

        # Scrolled window for config
        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vexpand=True,
            hexpand=True,
        )
        toolbar_view.set_content(scrolled)

        self.text_view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            left_margin=12,
            right_margin=12,
            top_margin=12,
            bottom_margin=12,
        )
        self.text_view.add_css_class("card")
        scrolled.set_child(self.text_view)

        self.text_buffer = self.text_view.get_buffer()

    def load_config(self):
        """Load and display the config file."""
        if CONFIG_FILE.exists():
            text = CONFIG_FILE.read_text()
        else:
            text = "(No configuration file yet - apply settings to create one)"
        self.text_buffer.set_text(text)

    def _on_open_folder(self, button):
        """Open the config folder."""
        import subprocess
        subprocess.run(["xdg-open", str(CONFIG_FILE.parent)])


class MainWindow(SettingsWindow):
    """Main window combining status and settings."""

    def __init__(self, app: SimaApplication):
        super().__init__(app, apply_callback=app.on_settings_applied)
        self._app = app

        # Modify the main page to add status section
        self._add_status_section()

    def _add_status_section(self):
        """Add a status section to the main page."""
        # Use the stored reference from parent class
        box = self._main_box

        # Create status group and insert at the top
        status_group = Adw.PreferencesGroup()

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

        # Config row
        config_row = Adw.ActionRow(
            title="View Config",
            subtitle="See current configuration file",
            activatable=True,
        )
        config_row.add_prefix(Gtk.Image(icon_name="document-properties-symbolic"))
        config_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        config_row.connect("activated", self._on_show_config)
        status_group.add(config_row)

        # Insert at the beginning
        box.prepend(status_group)

        # Add some spacing
        status_group.set_margin_bottom(12)

    def _on_enable_toggled(self, row, pspec):
        """Handle enable toggle."""
        enabled = row.get_active()
        self._app.toggle_service(enabled)

    def _on_show_logs(self, row):
        """Show the log viewer."""
        self._app.show_logs()

    def _on_show_config(self, row):
        """Show the config viewer."""
        self._app.show_config()

    def set_enabled(self, enabled: bool):
        """Set enabled state without triggering callback."""
        self.enable_row.handler_block_by_func(self._on_enable_toggled)
        self.enable_row.set_active(enabled)
        self.enable_row.handler_unblock_by_func(self._on_enable_toggled)

    def update_status(self, running: bool):
        """Update the status display (no-op, tray icon shows status)."""
        pass
