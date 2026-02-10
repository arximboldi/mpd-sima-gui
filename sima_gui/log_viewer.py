"""Log viewer dialog for sima-gui using GTK3."""

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib, Pango

from .config import LOG_FILE


class LogViewer(Gtk.Window):
    """Log viewer window."""

    def __init__(self, parent: Gtk.Window | None = None, get_logs_callback=None):
        super().__init__(
            title="mpd-sima Logs",
            transient_for=parent,
            default_width=800,
            default_height=600,
            window_position=Gtk.WindowPosition.CENTER,
        )

        self._get_logs = get_logs_callback
        self._auto_scroll = True
        self._refresh_source = None

        self._build_ui()
        self._load_logs()

        # Set up periodic refresh
        self._refresh_source = GLib.timeout_add(1000, self._refresh_logs)

        self.connect("delete-event", self._on_delete)

    def _on_delete(self, window, event):
        """Clean up on close."""
        if self._refresh_source:
            GLib.source_remove(self._refresh_source)
            self._refresh_source = None
        self.hide()
        return True  # Prevent destruction, just hide

    def _build_ui(self):
        """Build the log viewer UI."""
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("mpd-sima Logs")
        self.set_titlebar(header)

        # Clear button
        clear_button = Gtk.Button.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.BUTTON)
        clear_button.set_tooltip_text("Clear logs")
        clear_button.connect("clicked", self._on_clear)
        header.pack_start(clear_button)

        # Open log file button
        open_button = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        open_button.set_tooltip_text("Open log file location")
        open_button.connect("clicked", self._on_open_file)
        header.pack_start(open_button)

        # Auto-scroll toggle
        self.auto_scroll_button = Gtk.ToggleButton()
        self.auto_scroll_button.set_image(
            Gtk.Image.new_from_icon_name("go-bottom-symbolic", Gtk.IconSize.BUTTON)
        )
        self.auto_scroll_button.set_tooltip_text("Auto-scroll to bottom")
        self.auto_scroll_button.set_active(True)
        self.auto_scroll_button.connect("toggled", self._on_auto_scroll_toggled)
        header.pack_end(self.auto_scroll_button)

        # Scrolled window for logs
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        main_box.pack_start(scrolled, True, True, 0)

        # Text view for logs
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_monospace(True)
        self.text_view.set_left_margin(10)
        self.text_view.set_right_margin(10)
        self.text_view.set_top_margin(10)
        self.text_view.set_bottom_margin(10)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.add(self.text_view)

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
        if not self.get_visible():
            return True  # Keep the timeout but don't update

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

        return True  # Continue the timeout

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

    def append_log(self, line: str):
        """Append a line to the log."""
        end_iter = self.text_buffer.get_end_iter()
        if self.text_buffer.get_char_count() > 0:
            self.text_buffer.insert(end_iter, "\n")
        self.text_buffer.insert(self.text_buffer.get_end_iter(), line)

        if self._auto_scroll:
            self._scroll_to_bottom()
