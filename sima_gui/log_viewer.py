"""Log viewer dialog for sima-gui using GTK4/Adwaita."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

from .config import LOG_FILE


class LogViewer(Adw.Window):
    """Log viewer window with GTK4/Adwaita."""

    def __init__(self, app: Adw.Application, get_logs_callback=None):
        super().__init__(
            application=app,
            title="Logs",
            default_width=800,
            default_height=500,
        )

        self._get_logs = get_logs_callback
        self._auto_scroll = True
        self._refresh_source = None

        self._build_ui()
        self._load_logs()

        # Set up periodic refresh
        self._refresh_source = GLib.timeout_add(1000, self._refresh_logs)

        self.connect("close-request", self._on_close)
        self.connect("show", self._on_show)

    def _on_close(self, window):
        """Hide on close instead of destroying."""
        window.set_visible(False)
        return True  # Prevent destruction

    def _on_show(self, window):
        """Refresh logs when window is shown."""
        self._load_logs()

    def _build_ui(self):
        """Build the log viewer UI."""
        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Clear button
        clear_button = Gtk.Button(icon_name="edit-clear-symbolic")
        clear_button.set_tooltip_text("Clear display")
        clear_button.connect("clicked", self._on_clear)
        header.pack_start(clear_button)

        # Open log file button
        open_button = Gtk.Button(icon_name="folder-open-symbolic")
        open_button.set_tooltip_text("Open log folder")
        open_button.connect("clicked", self._on_open_file)
        header.pack_start(open_button)

        # Auto-scroll toggle
        self.auto_scroll_button = Gtk.ToggleButton(icon_name="go-bottom-symbolic")
        self.auto_scroll_button.set_tooltip_text("Auto-scroll")
        self.auto_scroll_button.set_active(True)
        self.auto_scroll_button.connect("toggled", self._on_auto_scroll_toggled)
        header.pack_end(self.auto_scroll_button)

        # Scrolled window for logs
        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vexpand=True,
            hexpand=True,
        )
        toolbar_view.set_content(scrolled)

        # Text view for logs
        self.text_view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            left_margin=12,
            right_margin=12,
            top_margin=12,
            bottom_margin=12,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
        )
        self.text_view.add_css_class("card")
        scrolled.set_child(self.text_view)

        self.text_buffer = self.text_view.get_buffer()

        # Store scrolled window for auto-scroll
        self._scrolled = scrolled

    def _load_logs(self):
        """Load logs from the process."""
        if self._get_logs:
            logs = self._get_logs()
            text = "\n".join(logs)
            self.text_buffer.set_text(text)
            self._scroll_to_bottom()

    def _refresh_logs(self) -> bool:
        """Refresh logs periodically."""
        if not self.is_visible():
            return True

        if self._get_logs:
            logs = self._get_logs()
            start_iter = self.text_buffer.get_start_iter()
            end_iter = self.text_buffer.get_end_iter()
            current_text = self.text_buffer.get_text(start_iter, end_iter, False)
            new_text = "\n".join(logs)

            if new_text != current_text:
                self.text_buffer.set_text(new_text)
                if self._auto_scroll:
                    self._scroll_to_bottom()

        return True

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the log."""
        def do_scroll():
            adj = self._scrolled.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
            return False

        GLib.idle_add(do_scroll)

    def _on_clear(self, button):
        """Clear the log display."""
        self.text_buffer.set_text("")

    def _on_open_file(self, button):
        """Open the log file location."""
        import subprocess
        subprocess.run(["xdg-open", str(LOG_FILE.parent)])

    def _on_auto_scroll_toggled(self, button):
        """Toggle auto-scroll."""
        self._auto_scroll = button.get_active()
        if self._auto_scroll:
            self._scroll_to_bottom()
