"""System tray indicator for sima-gui."""

import gi

gi.require_version("Gtk", "3.0")

# Try to use AyatanaAppIndicator3 (more common on modern systems)
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    HAS_INDICATOR = True
except (ValueError, ImportError):
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppIndicator
        HAS_INDICATOR = True
    except (ValueError, ImportError):
        HAS_INDICATOR = False
        AppIndicator = None

from gi.repository import Gtk, GLib

from .process import SimaProcess
from .settings_dialog import SettingsDialog
from .log_viewer import LogViewer


class SimaTrayApp:
    """System tray application for mpd-sima."""

    ICON_ACTIVE = "audio-x-generic"
    ICON_INACTIVE = "audio-x-generic-symbolic"

    def __init__(self):
        self.process = SimaProcess(on_output=self._on_process_output)
        self._log_viewer: LogViewer | None = None
        self._settings_dialog: SettingsDialog | None = None

        # Track if we're running
        self._enabled = True

        if HAS_INDICATOR:
            self._setup_indicator()
        else:
            print("Warning: No AppIndicator support found. Running without system tray.")
            self._indicator = None

    def _setup_indicator(self):
        """Set up the system tray indicator."""
        self._indicator = AppIndicator.Indicator.new(
            "sima-gui",
            self.ICON_INACTIVE,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_title("mpd-sima")

        # Create menu
        self._menu = Gtk.Menu()

        # Enable/Disable item
        self._enable_item = Gtk.CheckMenuItem(label="Enabled")
        self._enable_item.set_active(True)
        self._enable_item.connect("toggled", self._on_enable_toggled)
        self._menu.append(self._enable_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        # Show logs item
        logs_item = Gtk.MenuItem(label="Show Logs")
        logs_item.connect("activate", self._on_show_logs)
        self._menu.append(logs_item)

        # Settings item
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.connect("activate", self._on_show_settings)
        self._menu.append(settings_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        # Quit item
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        self._menu.append(quit_item)

        self._menu.show_all()
        self._indicator.set_menu(self._menu)

    def _on_process_output(self, line: str):
        """Handle process output."""
        # This is called from the output reading thread
        # Use GLib.idle_add to update UI from main thread if needed
        pass

    def _update_icon(self):
        """Update the tray icon based on process state."""
        if self._indicator:
            if self.process.is_running:
                self._indicator.set_icon_full(self.ICON_ACTIVE, "mpd-sima running")
            else:
                self._indicator.set_icon_full(self.ICON_INACTIVE, "mpd-sima stopped")

    def _on_enable_toggled(self, item):
        """Handle enable/disable toggle."""
        self._enabled = item.get_active()

        if self._enabled:
            self.process.start()
        else:
            self.process.stop()

        self._update_icon()

    def _on_show_logs(self, item):
        """Show the log viewer."""
        if self._log_viewer is None:
            self._log_viewer = LogViewer(
                parent=None,
                get_logs_callback=self.process.get_logs,
            )

        self._log_viewer.show_all()
        self._log_viewer.present()

    def _on_show_settings(self, item):
        """Show the settings dialog."""
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(parent=None)
            self._settings_dialog.set_apply_callback(self._on_settings_applied)

        self._settings_dialog.show_all()
        self._settings_dialog.present()

    def _on_settings_applied(self):
        """Handle settings being applied."""
        # Restart the process with new settings
        if self._enabled:
            self.process.restart()
            self._update_icon()

    def _on_quit(self, item):
        """Quit the application."""
        self.process.stop()
        Gtk.main_quit()

    def run(self):
        """Run the application."""
        # Start process immediately
        if self._enabled:
            self.process.start()
            self._update_icon()

        # Run GTK main loop
        Gtk.main()
