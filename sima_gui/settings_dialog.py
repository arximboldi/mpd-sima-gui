"""Settings dialog for sima-gui using GTK3."""

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib, Pango

from .config import SimaConfig, load_config, save_config


class SettingsDialog(Gtk.Window):
    """Settings dialog for mpd-sima configuration."""

    def __init__(self, parent: Gtk.Window | None = None):
        super().__init__(
            title="mpd-sima Settings",
            transient_for=parent,
            modal=True,
            default_width=700,
            default_height=650,
            window_position=Gtk.WindowPosition.CENTER,
        )

        self.config = load_config()
        self._apply_callback = None

        self._build_ui()

    def set_apply_callback(self, callback):
        """Set callback to be called when settings are applied."""
        self._apply_callback = callback

    def _build_ui(self):
        """Build the settings UI."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("mpd-sima Settings")
        self.set_titlebar(header)

        # Apply button
        apply_button = Gtk.Button(label="Apply")
        apply_button.get_style_context().add_class("suggested-action")
        apply_button.connect("clicked", self._on_apply)
        header.pack_end(apply_button)

        # Notebook for tabs
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.LEFT)
        main_box.pack_start(notebook, True, True, 0)

        # Add pages
        notebook.append_page(self._create_mpd_page(), Gtk.Label(label="MPD"))
        notebook.append_page(self._create_sima_page(), Gtk.Label(label="General"))
        notebook.append_page(self._create_plugins_page(), Gtk.Label(label="Plugins"))
        notebook.append_page(self._create_lastfm_page(), Gtk.Label(label="Last.fm"))
        notebook.append_page(self._create_advanced_page(), Gtk.Label(label="Advanced"))

    def _on_apply(self, button):
        """Handle apply button click."""
        self._save_all_settings()
        save_config(self.config)

        if self._apply_callback:
            self._apply_callback()

        self.hide()

    def _create_frame(self, title: str, description: str = "") -> tuple[Gtk.Frame, Gtk.Grid]:
        """Create a frame with a grid inside."""
        frame = Gtk.Frame()
        frame.set_margin_top(10)
        frame.set_margin_bottom(10)
        frame.set_margin_start(10)
        frame.set_margin_end(10)

        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_halign(Gtk.Align.START)
        label_box.pack_start(title_label, False, False, 0)

        if description:
            desc_label = Gtk.Label(label=description)
            desc_label.set_halign(Gtk.Align.START)
            desc_label.get_style_context().add_class("dim-label")
            label_box.pack_start(desc_label, False, False, 0)

        frame.set_label_widget(label_box)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(12)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        frame.add(grid)

        return frame, grid

    def _add_entry_row(self, grid: Gtk.Grid, row: int, label: str, value: str,
                       tooltip: str = "", password: bool = False) -> Gtk.Entry:
        """Add an entry row to a grid."""
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.END)
        lbl.set_margin_end(5)
        grid.attach(lbl, 0, row, 1, 1)

        entry = Gtk.Entry()
        entry.set_text(value)
        entry.set_hexpand(True)
        if tooltip:
            entry.set_tooltip_text(tooltip)
        if password:
            entry.set_visibility(False)
            entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        grid.attach(entry, 1, row, 1, 1)

        return entry

    def _add_spin_row(self, grid: Gtk.Grid, row: int, label: str, value: int,
                      min_val: int, max_val: int, tooltip: str = "") -> Gtk.SpinButton:
        """Add a spin button row to a grid."""
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.END)
        lbl.set_margin_end(5)
        grid.attach(lbl, 0, row, 1, 1)

        adjustment = Gtk.Adjustment(
            value=value,
            lower=min_val,
            upper=max_val,
            step_increment=1,
            page_increment=10,
        )
        spin = Gtk.SpinButton()
        spin.set_adjustment(adjustment)
        spin.set_numeric(True)
        spin.set_hexpand(True)
        if tooltip:
            spin.set_tooltip_text(tooltip)
        grid.attach(spin, 1, row, 1, 1)

        return spin

    def _add_switch_row(self, grid: Gtk.Grid, row: int, label: str, value: bool,
                        tooltip: str = "") -> Gtk.Switch:
        """Add a switch row to a grid."""
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.END)
        lbl.set_margin_end(5)
        grid.attach(lbl, 0, row, 1, 1)

        switch = Gtk.Switch()
        switch.set_active(value)
        switch.set_halign(Gtk.Align.START)
        if tooltip:
            switch.set_tooltip_text(tooltip)
        grid.attach(switch, 1, row, 1, 1)

        return switch

    def _add_combo_row(self, grid: Gtk.Grid, row: int, label: str, options: list[str],
                       current: str, tooltip: str = "") -> Gtk.ComboBoxText:
        """Add a combo box row to a grid."""
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.END)
        lbl.set_margin_end(5)
        grid.attach(lbl, 0, row, 1, 1)

        combo = Gtk.ComboBoxText()
        for option in options:
            combo.append_text(option)

        # Set active item
        try:
            index = options.index(current)
            combo.set_active(index)
        except ValueError:
            combo.set_active(0)

        combo.set_hexpand(True)
        if tooltip:
            combo.set_tooltip_text(tooltip)
        grid.attach(combo, 1, row, 1, 1)

        return combo

    def _create_mpd_page(self) -> Gtk.ScrolledWindow:
        """Create MPD connection settings page."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.add(box)

        # Connection settings
        frame, grid = self._create_frame("Connection", "MPD server connection settings")
        box.pack_start(frame, False, False, 0)

        self.mpd_host = self._add_entry_row(
            grid, 0, "Host:",
            self.config.mpd.host,
            "MPD server address (IP or hostname)"
        )

        self.mpd_port = self._add_spin_row(
            grid, 1, "Port:",
            self.config.mpd.port,
            1, 65535,
            "MPD server port"
        )

        self.mpd_password = self._add_entry_row(
            grid, 2, "Password:",
            self.config.mpd.password,
            "Authentication password (leave empty if not required)",
            password=True
        )

        return scrolled

    def _create_sima_page(self) -> Gtk.ScrolledWindow:
        """Create core sima settings page."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.add(box)

        # Queue management
        frame, grid = self._create_frame("Queue Management", "Control how tracks are automatically queued")
        box.pack_start(frame, False, False, 0)

        self.queue_length = self._add_spin_row(
            grid, 0, "Queue Threshold:",
            self.config.sima.queue_length,
            0, 100,
            "Number of tracks remaining before autoqueue triggers"
        )

        self.history_duration = self._add_spin_row(
            grid, 1, "History Duration (hours):",
            self.config.sima.history_duration,
            0, 168,
            "How long to remember played tracks to avoid repeats"
        )

        # Behavior
        frame, grid = self._create_frame("Behavior", "Control when autoqueue is active")
        box.pack_start(frame, False, False, 0)

        self.musicbrainzid = self._add_switch_row(
            grid, 0, "Use MusicBrainz IDs:",
            self.config.sima.musicbrainzid,
            "Use MusicBrainz identifiers for more accurate matching"
        )

        self.repeat_disable = self._add_switch_row(
            grid, 1, "Disable in Repeat Mode:",
            self.config.sima.repeat_disable_queue,
            "Don't queue tracks when repeat mode is enabled"
        )

        self.single_disable = self._add_switch_row(
            grid, 2, "Disable in Single Mode:",
            self.config.sima.single_disable_queue,
            "Don't queue tracks when single mode is enabled"
        )

        # Logging
        frame, grid = self._create_frame("Logging", "Configure logging behavior")
        box.pack_start(frame, False, False, 0)

        self.verbosity = self._add_combo_row(
            grid, 0, "Log Level:",
            ["debug", "info", "warning", "error"],
            self.config.log.verbosity,
            "Amount of detail in logs"
        )

        return scrolled

    def _create_plugins_page(self) -> Gtk.ScrolledWindow:
        """Create plugins configuration page."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.add(box)

        # Active plugins
        frame, grid = self._create_frame("Active Plugins", "Comma-separated list of plugins to use")
        box.pack_start(frame, False, False, 0)

        self.internal_plugins = self._add_entry_row(
            grid, 0, "Plugins:",
            self.config.sima.internal,
            "Available: Lastfm, Random, Crop, Genre, Tags"
        )

        # Crop plugin
        frame, grid = self._create_frame("Crop Plugin", "Manages playlist length by removing old tracks")
        box.pack_start(frame, False, False, 0)

        self.crop_consume = self._add_spin_row(
            grid, 0, "Tracks to Keep:",
            self.config.crop.consume,
            -1, 1000,
            "Number of played tracks to retain (-1 = keep all)"
        )

        self.crop_priority = self._add_spin_row(
            grid, 1, "Priority:",
            self.config.crop.priority,
            0, 200,
            "Plugin execution order (lower = earlier)"
        )

        # Random plugin
        frame, grid = self._create_frame("Random Plugin", "Fallback random track selection")
        box.pack_start(frame, False, False, 0)

        self.random_tracks = self._add_spin_row(
            grid, 0, "Tracks to Add:",
            self.config.random.track_to_add,
            1, 50,
            "Number of random tracks to queue"
        )

        self.random_flavour = self._add_combo_row(
            grid, 1, "Flavour:",
            ["sensible", "pure"],
            self.config.random.flavour,
            "Selection mode: sensible respects history, pure is fully random"
        )

        self.random_priority = self._add_spin_row(
            grid, 2, "Priority:",
            self.config.random.priority,
            0, 200,
            "Plugin execution order (lower = earlier)"
        )

        return scrolled

    def _create_lastfm_page(self) -> Gtk.ScrolledWindow:
        """Create Last.fm plugin settings page."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.add(box)

        # Main settings
        frame, grid = self._create_frame("Recommendation Settings", "Configure how Last.fm recommendations work")
        box.pack_start(frame, False, False, 0)

        self.lastfm_queue_mode = self._add_combo_row(
            grid, 0, "Queue Mode:",
            ["track", "top", "album"],
            self.config.lastfm.queue_mode,
            "How to select tracks from similar artists"
        )

        self.lastfm_max_art = self._add_spin_row(
            grid, 1, "Max Similar Artists:",
            self.config.lastfm.max_art,
            1, 100,
            "Maximum number of similar artists to retrieve"
        )

        self.lastfm_depth = self._add_spin_row(
            grid, 2, "History Depth:",
            self.config.lastfm.depth,
            1, 10,
            "How many recent tracks to use for suggestions"
        )

        # Track selection
        frame, grid = self._create_frame("Track Selection", "Configure track and album queuing")
        box.pack_start(frame, False, False, 0)

        self.lastfm_track_to_add = self._add_spin_row(
            grid, 0, "Tracks to Add:",
            self.config.lastfm.track_to_add,
            1, 50,
            "Tracks per selection (track/top modes)"
        )

        self.lastfm_album_to_add = self._add_spin_row(
            grid, 1, "Albums to Add:",
            self.config.lastfm.album_to_add,
            1, 10,
            "Albums per selection (album mode)"
        )

        self.lastfm_tracks_from_album = self._add_spin_row(
            grid, 2, "Tracks from Album:",
            self.config.lastfm.track_to_add_from_album,
            0, 50,
            "Tracks per album (0 = queue entire album)"
        )

        self.lastfm_single_album = self._add_switch_row(
            grid, 3, "Prevent Same Album:",
            self.config.lastfm.single_album,
            "Don't queue multiple tracks from the same album"
        )

        # Advanced
        frame, grid = self._create_frame("Advanced", "Additional Last.fm settings")
        box.pack_start(frame, False, False, 0)

        self.lastfm_cache = self._add_switch_row(
            grid, 0, "Enable Cache:",
            self.config.lastfm.cache,
            "Cache Last.fm API responses for better performance"
        )

        self.lastfm_priority = self._add_spin_row(
            grid, 1, "Priority:",
            self.config.lastfm.priority,
            0, 200,
            "Plugin execution order (lower = earlier)"
        )

        return scrolled

    def _create_advanced_page(self) -> Gtk.ScrolledWindow:
        """Create advanced settings page with Genre and Tags plugins."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.add(box)

        # Genre plugin
        frame, grid = self._create_frame("Genre Plugin", "Tag-based offline recommendations using genre matching")
        box.pack_start(frame, False, False, 0)

        self.genre_queue_mode = self._add_combo_row(
            grid, 0, "Queue Mode:",
            ["track", "album"],
            self.config.genre.queue_mode,
            "Track or album selection"
        )

        self.genre_track_to_add = self._add_spin_row(
            grid, 1, "Tracks to Add:",
            self.config.genre.track_to_add,
            1, 50,
            "Number of tracks to queue"
        )

        self.genre_album_to_add = self._add_spin_row(
            grid, 2, "Albums to Add:",
            self.config.genre.album_to_add,
            1, 10,
            "Number of albums to queue (album mode)"
        )

        self.genre_single_album = self._add_switch_row(
            grid, 3, "Prevent Same Album:",
            self.config.genre.single_album,
            "Don't queue multiple tracks from the same album"
        )

        self.genre_priority = self._add_spin_row(
            grid, 4, "Priority:",
            self.config.genre.priority,
            0, 200,
            "Plugin execution order"
        )

        # Tags plugin
        frame, grid = self._create_frame("Tags Plugin", "Custom MPD filter-based queuing")
        box.pack_start(frame, False, False, 0)

        self.tags_queue_mode = self._add_combo_row(
            grid, 0, "Queue Mode:",
            ["track", "album"],
            self.config.tags.queue_mode,
            "Track or album selection"
        )

        self.tags_filter = self._add_entry_row(
            grid, 1, "Filter Expression:",
            self.config.tags.filter,
            "Raw MPD protocol filter expression"
        )

        self.tags_genre = self._add_entry_row(
            grid, 2, "Genre:",
            self.config.tags.genre,
            "Comma-separated genre names (OR logic)"
        )

        self.tags_date = self._add_entry_row(
            grid, 3, "Date:",
            self.config.tags.date,
            "Year range or filter expression"
        )

        self.tags_comment = self._add_entry_row(
            grid, 4, "Comment:",
            self.config.tags.comment,
            "Comma-separated values (OR logic)"
        )

        self.tags_label = self._add_entry_row(
            grid, 5, "Label:",
            self.config.tags.label,
            "Record label values"
        )

        self.tags_track_to_add = self._add_spin_row(
            grid, 6, "Tracks to Add:",
            self.config.tags.track_to_add,
            1, 50,
            "Number of tracks to queue"
        )

        self.tags_single_album = self._add_switch_row(
            grid, 7, "Prevent Same Album:",
            self.config.tags.single_album,
            "Don't queue multiple tracks from the same album"
        )

        self.tags_priority = self._add_spin_row(
            grid, 8, "Priority:",
            self.config.tags.priority,
            0, 200,
            "Plugin execution order"
        )

        return scrolled

    def _save_all_settings(self):
        """Save all settings from UI to config object."""
        # MPD
        self.config.mpd.host = self.mpd_host.get_text()
        self.config.mpd.port = int(self.mpd_port.get_value())
        self.config.mpd.password = self.mpd_password.get_text()

        # Sima
        self.config.sima.queue_length = int(self.queue_length.get_value())
        self.config.sima.history_duration = int(self.history_duration.get_value())
        self.config.sima.musicbrainzid = self.musicbrainzid.get_active()
        self.config.sima.repeat_disable_queue = self.repeat_disable.get_active()
        self.config.sima.single_disable_queue = self.single_disable.get_active()
        self.config.sima.internal = self.internal_plugins.get_text()

        # Log
        self.config.log.verbosity = self.verbosity.get_active_text()

        # Crop
        self.config.crop.consume = int(self.crop_consume.get_value())
        self.config.crop.priority = int(self.crop_priority.get_value())

        # Random
        self.config.random.track_to_add = int(self.random_tracks.get_value())
        self.config.random.flavour = self.random_flavour.get_active_text()
        self.config.random.priority = int(self.random_priority.get_value())

        # Lastfm
        self.config.lastfm.queue_mode = self.lastfm_queue_mode.get_active_text()
        self.config.lastfm.max_art = int(self.lastfm_max_art.get_value())
        self.config.lastfm.depth = int(self.lastfm_depth.get_value())
        self.config.lastfm.track_to_add = int(self.lastfm_track_to_add.get_value())
        self.config.lastfm.album_to_add = int(self.lastfm_album_to_add.get_value())
        self.config.lastfm.track_to_add_from_album = int(self.lastfm_tracks_from_album.get_value())
        self.config.lastfm.single_album = self.lastfm_single_album.get_active()
        self.config.lastfm.cache = self.lastfm_cache.get_active()
        self.config.lastfm.priority = int(self.lastfm_priority.get_value())

        # Genre
        self.config.genre.queue_mode = self.genre_queue_mode.get_active_text()
        self.config.genre.track_to_add = int(self.genre_track_to_add.get_value())
        self.config.genre.album_to_add = int(self.genre_album_to_add.get_value())
        self.config.genre.single_album = self.genre_single_album.get_active()
        self.config.genre.priority = int(self.genre_priority.get_value())

        # Tags
        self.config.tags.queue_mode = self.tags_queue_mode.get_active_text()
        self.config.tags.filter = self.tags_filter.get_text()
        self.config.tags.genre = self.tags_genre.get_text()
        self.config.tags.date = self.tags_date.get_text()
        self.config.tags.comment = self.tags_comment.get_text()
        self.config.tags.label = self.tags_label.get_text()
        self.config.tags.track_to_add = int(self.tags_track_to_add.get_value())
        self.config.tags.single_album = self.tags_single_album.get_active()
        self.config.tags.priority = int(self.tags_priority.get_value())
