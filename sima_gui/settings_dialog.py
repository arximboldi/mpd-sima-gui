"""Settings dialog for sima-gui using GTK4/Adwaita."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

from .config import SimaConfig, load_config, save_config


# Plugin definitions with their settings
PLUGINS = {
    "Crop": {
        "description": "Remove old tracks from the queue",
    },
    "Random": {
        "description": "Queue random tracks as fallback",
    },
    "Lastfm": {
        "description": "Recommendations based on Last.fm data",
    },
    "Genre": {
        "description": "Queue tracks with similar genre tags",
    },
    "Tags": {
        "description": "Queue tracks using custom tag filters",
    },
}


class SettingsWindow(Adw.ApplicationWindow):
    """Settings window with all options on a single page."""

    def __init__(self, app: Adw.Application, apply_callback=None):
        super().__init__(
            application=app,
            title="Sima Settings",
            default_width=700,
            default_height=700,
        )

        self.config = load_config()
        self._apply_callback = apply_callback
        self._plugin_rows = {}
        self._plugin_widgets = {}
        self._plugin_order = []

        self._build_ui()

    def set_apply_callback(self, callback):
        """Set callback to be called when settings are applied."""
        self._apply_callback = callback

    def _build_ui(self):
        """Build the single-page settings UI."""
        # Toolbar view for header
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Apply button
        apply_button = Gtk.Button(label="Apply")
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", self._on_apply)
        header.pack_end(apply_button)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vexpand=True,
        )
        toolbar_view.set_content(scrolled)

        # Content box with clamp for proper width
        clamp = Adw.Clamp(maximum_size=600, margin_top=24, margin_bottom=24,
                         margin_start=12, margin_end=12)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(box)

        # Store reference for subclasses
        self._main_box = box

        # Build all sections
        self._create_mpd_section(box)
        self._create_general_section(box)
        self._create_plugins_section(box)

    def _create_spin_row(self, title: str, subtitle: str, value: int,
                         min_val: int, max_val: int) -> Adw.SpinRow:
        """Create a spin button row."""
        adjustment = Gtk.Adjustment(
            value=value, lower=min_val, upper=max_val,
            step_increment=1, page_increment=10,
        )
        return Adw.SpinRow(title=title, subtitle=subtitle, adjustment=adjustment)

    def _create_entry_row(self, title: str, value: str, password: bool = False):
        """Create an entry row."""
        if password:
            row = Adw.PasswordEntryRow(title=title)
        else:
            row = Adw.EntryRow(title=title)
        row.set_text(value)
        return row

    def _create_switch_row(self, title: str, subtitle: str, value: bool) -> Adw.SwitchRow:
        """Create a switch row."""
        return Adw.SwitchRow(title=title, subtitle=subtitle, active=value)

    def _create_combo_row(self, title: str, subtitle: str, options: list[str],
                          current: str) -> Adw.ComboRow:
        """Create a combo box row."""
        model = Gtk.StringList()
        selected_index = 0
        for i, option in enumerate(options):
            model.append(option)
            if option == current:
                selected_index = i
        row = Adw.ComboRow(title=title, subtitle=subtitle, model=model, selected=selected_index)
        return row

    def _create_mpd_section(self, box: Gtk.Box):
        """Create MPD connection section."""
        group = Adw.PreferencesGroup()
        box.append(group)

        expander = Adw.ExpanderRow(
            title="MPD Connection",
            subtitle="Server address and authentication",
        )
        expander.add_prefix(Gtk.Image(icon_name="network-server-symbolic"))
        group.add(expander)

        self.mpd_host = self._create_entry_row("Host", self.config.mpd.host)
        expander.add_row(self.mpd_host)

        self.mpd_port = self._create_spin_row(
            "Port", "", self.config.mpd.port, 1, 65535
        )
        expander.add_row(self.mpd_port)

        self.mpd_password = self._create_entry_row(
            "Password", self.config.mpd.password, password=True
        )
        expander.add_row(self.mpd_password)

    def _create_general_section(self, box: Gtk.Box):
        """Create general settings section."""
        group = Adw.PreferencesGroup()
        box.append(group)

        expander = Adw.ExpanderRow(
            title="General",
            subtitle="Queue behavior and logging",
        )
        expander.add_prefix(Gtk.Image(icon_name="preferences-system-symbolic"))
        group.add(expander)

        self.queue_length = self._create_spin_row(
            "Queue Threshold",
            "Tracks remaining before autoqueue",
            self.config.sima.queue_length, 0, 100,
        )
        expander.add_row(self.queue_length)

        self.history_duration = self._create_spin_row(
            "History Duration",
            "Hours to remember played tracks",
            self.config.sima.history_duration, 0, 168,
        )
        expander.add_row(self.history_duration)

        self.musicbrainzid = self._create_switch_row(
            "Use MusicBrainz IDs",
            "More accurate artist matching",
            self.config.sima.musicbrainzid,
        )
        expander.add_row(self.musicbrainzid)

        self.repeat_disable = self._create_switch_row(
            "Pause in Repeat Mode", "",
            self.config.sima.repeat_disable_queue,
        )
        expander.add_row(self.repeat_disable)

        self.single_disable = self._create_switch_row(
            "Pause in Single Mode", "",
            self.config.sima.single_disable_queue,
        )
        expander.add_row(self.single_disable)

        self.verbosity = self._create_combo_row(
            "Log Level", "",
            ["debug", "info", "warning", "error"],
            self.config.log.verbosity,
        )
        expander.add_row(self.verbosity)

    def _create_plugins_section(self, box: Gtk.Box):
        """Create plugins section."""
        # Parse current plugin order from config
        current_plugins = [p.strip() for p in self.config.sima.internal.split(",") if p.strip()]
        all_plugins = list(PLUGINS.keys())
        enabled_plugins = [p for p in current_plugins if p in all_plugins]
        disabled_plugins = [p for p in all_plugins if p not in enabled_plugins]

        self._plugins_group = Adw.PreferencesGroup(
            title="Plugins",
            description="Enable and reorder plugins (top = highest priority)",
        )
        box.append(self._plugins_group)

        # Add enabled plugins first, then disabled
        for plugin_name in enabled_plugins + disabled_plugins:
            is_enabled = plugin_name in enabled_plugins
            self._add_plugin_row(plugin_name, is_enabled)

    def _add_plugin_row(self, plugin_name: str, enabled: bool):
        """Add a plugin row with settings."""
        plugin_info = PLUGINS[plugin_name]

        expander = Adw.ExpanderRow(
            title=plugin_name,
            subtitle=plugin_info["description"],
        )

        # Enable switch
        switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        switch.set_active(enabled)
        expander.add_prefix(switch)

        # Reorder buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        button_box.set_valign(Gtk.Align.CENTER)

        up_btn = Gtk.Button(icon_name="go-up-symbolic")
        up_btn.add_css_class("flat")
        up_btn.connect("clicked", self._on_move_plugin_up, plugin_name)
        button_box.append(up_btn)

        down_btn = Gtk.Button(icon_name="go-down-symbolic")
        down_btn.add_css_class("flat")
        down_btn.connect("clicked", self._on_move_plugin_down, plugin_name)
        button_box.append(down_btn)

        expander.add_suffix(button_box)

        # Add plugin-specific settings
        self._add_plugin_settings(expander, plugin_name)

        self._plugin_rows[plugin_name] = {"expander": expander, "switch": switch}
        self._plugins_group.add(expander)
        self._plugin_order.append(plugin_name)

    def _add_plugin_settings(self, expander: Adw.ExpanderRow, plugin_name: str):
        """Add settings rows for a specific plugin."""
        if plugin_name == "Crop":
            row = self._create_spin_row("Tracks to Keep", "(-1 = all)", self.config.crop.consume, -1, 1000)
            self._plugin_widgets["crop_consume"] = row
            expander.add_row(row)

        elif plugin_name == "Random":
            row = self._create_spin_row("Tracks to Add", "", self.config.random.track_to_add, 1, 50)
            self._plugin_widgets["random_track_to_add"] = row
            expander.add_row(row)

            row = self._create_combo_row("Mode", "", ["sensible", "pure"], self.config.random.flavour)
            self._plugin_widgets["random_flavour"] = row
            expander.add_row(row)

        elif plugin_name == "Lastfm":
            row = self._create_combo_row("Queue Mode", "", ["track", "top", "album"], self.config.lastfm.queue_mode)
            self._plugin_widgets["lastfm_queue_mode"] = row
            expander.add_row(row)

            row = self._create_spin_row("Similar Artists Limit", "", self.config.lastfm.max_art, 1, 100)
            self._plugin_widgets["lastfm_max_art"] = row
            expander.add_row(row)

            row = self._create_spin_row("History Depth", "", self.config.lastfm.depth, 1, 10)
            self._plugin_widgets["lastfm_depth"] = row
            expander.add_row(row)

            row = self._create_spin_row("Tracks to Add", "", self.config.lastfm.track_to_add, 1, 50)
            self._plugin_widgets["lastfm_track_to_add"] = row
            expander.add_row(row)

            row = self._create_spin_row("Albums to Add", "", self.config.lastfm.album_to_add, 1, 10)
            self._plugin_widgets["lastfm_album_to_add"] = row
            expander.add_row(row)

            row = self._create_switch_row("Prevent Same Album", "", self.config.lastfm.single_album)
            self._plugin_widgets["lastfm_single_album"] = row
            expander.add_row(row)

            row = self._create_switch_row("Cache Responses", "", self.config.lastfm.cache)
            self._plugin_widgets["lastfm_cache"] = row
            expander.add_row(row)

        elif plugin_name == "Genre":
            row = self._create_combo_row("Queue Mode", "", ["track", "album"], self.config.genre.queue_mode)
            self._plugin_widgets["genre_queue_mode"] = row
            expander.add_row(row)

            row = self._create_spin_row("Tracks to Add", "", self.config.genre.track_to_add, 1, 50)
            self._plugin_widgets["genre_track_to_add"] = row
            expander.add_row(row)

            row = self._create_spin_row("Albums to Add", "", self.config.genre.album_to_add, 1, 10)
            self._plugin_widgets["genre_album_to_add"] = row
            expander.add_row(row)

            row = self._create_switch_row("Prevent Same Album", "", self.config.genre.single_album)
            self._plugin_widgets["genre_single_album"] = row
            expander.add_row(row)

        elif plugin_name == "Tags":
            row = self._create_combo_row("Queue Mode", "", ["track", "album"], self.config.tags.queue_mode)
            self._plugin_widgets["tags_queue_mode"] = row
            expander.add_row(row)

            row = self._create_entry_row("Filter Expression", self.config.tags.filter)
            self._plugin_widgets["tags_filter"] = row
            expander.add_row(row)

            row = self._create_entry_row("Genre", self.config.tags.genre)
            self._plugin_widgets["tags_genre"] = row
            expander.add_row(row)

            row = self._create_entry_row("Date", self.config.tags.date)
            self._plugin_widgets["tags_date"] = row
            expander.add_row(row)

            row = self._create_entry_row("Comment", self.config.tags.comment)
            self._plugin_widgets["tags_comment"] = row
            expander.add_row(row)

            row = self._create_entry_row("Label", self.config.tags.label)
            self._plugin_widgets["tags_label"] = row
            expander.add_row(row)

            row = self._create_spin_row("Tracks to Add", "", self.config.tags.track_to_add, 1, 50)
            self._plugin_widgets["tags_track_to_add"] = row
            expander.add_row(row)

            row = self._create_switch_row("Prevent Same Album", "", self.config.tags.single_album)
            self._plugin_widgets["tags_single_album"] = row
            expander.add_row(row)

    def _get_plugin_order(self) -> list[str]:
        """Get current plugin order."""
        return list(self._plugin_order)

    def _on_move_plugin_up(self, button, plugin_name):
        """Move plugin up in the list."""
        order = self._get_plugin_order()
        idx = order.index(plugin_name)
        if idx > 0:
            self._rebuild_plugin_list(order, idx, idx - 1)

    def _on_move_plugin_down(self, button, plugin_name):
        """Move plugin down in the list."""
        order = self._get_plugin_order()
        idx = order.index(plugin_name)
        if idx < len(order) - 1:
            self._rebuild_plugin_list(order, idx, idx + 1)

    def _rebuild_plugin_list(self, order: list[str], from_idx: int, to_idx: int):
        """Rebuild the plugin list with new order."""
        order[from_idx], order[to_idx] = order[to_idx], order[from_idx]

        # Save current switch states
        old_switches = {name: data["switch"].get_active() for name, data in self._plugin_rows.items()}

        # Remove all rows
        for name in list(self._plugin_rows.keys()):
            self._plugins_group.remove(self._plugin_rows[name]["expander"])

        self._plugin_rows.clear()
        self._plugin_order.clear()

        # Re-add in new order
        for plugin_name in order:
            self._add_plugin_row(plugin_name, old_switches[plugin_name])

    def _on_apply(self, button):
        """Handle apply button click."""
        self._save_all_settings()
        save_config(self.config)

        if self._apply_callback:
            self._apply_callback()

        self.close()

    def _save_all_settings(self):
        """Save all settings from UI to config object."""
        # MPD
        self.config.mpd.host = self.mpd_host.get_text()
        self.config.mpd.port = int(self.mpd_port.get_value())
        self.config.mpd.password = self.mpd_password.get_text()

        # General
        self.config.sima.queue_length = int(self.queue_length.get_value())
        self.config.sima.history_duration = int(self.history_duration.get_value())
        self.config.sima.musicbrainzid = self.musicbrainzid.get_active()
        self.config.sima.repeat_disable_queue = self.repeat_disable.get_active()
        self.config.sima.single_disable_queue = self.single_disable.get_active()

        model = self.verbosity.get_model()
        self.config.log.verbosity = model.get_string(self.verbosity.get_selected())

        # Plugins - build list and set priorities
        enabled_plugins = []
        for i, plugin_name in enumerate(self._plugin_order):
            switch = self._plugin_rows[plugin_name]["switch"]
            priority = 10 + (i * 10)

            if switch.get_active():
                enabled_plugins.append(plugin_name)

            # Set priority based on position
            if plugin_name == "Crop":
                self.config.crop.priority = priority
            elif plugin_name == "Random":
                self.config.random.priority = priority
            elif plugin_name == "Lastfm":
                self.config.lastfm.priority = priority
            elif plugin_name == "Genre":
                self.config.genre.priority = priority
            elif plugin_name == "Tags":
                self.config.tags.priority = priority

        self.config.sima.internal = ", ".join(enabled_plugins)

        # Plugin-specific settings
        if "crop_consume" in self._plugin_widgets:
            self.config.crop.consume = int(self._plugin_widgets["crop_consume"].get_value())

        if "random_track_to_add" in self._plugin_widgets:
            self.config.random.track_to_add = int(self._plugin_widgets["random_track_to_add"].get_value())
        if "random_flavour" in self._plugin_widgets:
            m = self._plugin_widgets["random_flavour"].get_model()
            self.config.random.flavour = m.get_string(self._plugin_widgets["random_flavour"].get_selected())

        if "lastfm_queue_mode" in self._plugin_widgets:
            m = self._plugin_widgets["lastfm_queue_mode"].get_model()
            self.config.lastfm.queue_mode = m.get_string(self._plugin_widgets["lastfm_queue_mode"].get_selected())
        if "lastfm_max_art" in self._plugin_widgets:
            self.config.lastfm.max_art = int(self._plugin_widgets["lastfm_max_art"].get_value())
        if "lastfm_depth" in self._plugin_widgets:
            self.config.lastfm.depth = int(self._plugin_widgets["lastfm_depth"].get_value())
        if "lastfm_track_to_add" in self._plugin_widgets:
            self.config.lastfm.track_to_add = int(self._plugin_widgets["lastfm_track_to_add"].get_value())
        if "lastfm_album_to_add" in self._plugin_widgets:
            self.config.lastfm.album_to_add = int(self._plugin_widgets["lastfm_album_to_add"].get_value())
        if "lastfm_single_album" in self._plugin_widgets:
            self.config.lastfm.single_album = self._plugin_widgets["lastfm_single_album"].get_active()
        if "lastfm_cache" in self._plugin_widgets:
            self.config.lastfm.cache = self._plugin_widgets["lastfm_cache"].get_active()

        if "genre_queue_mode" in self._plugin_widgets:
            m = self._plugin_widgets["genre_queue_mode"].get_model()
            self.config.genre.queue_mode = m.get_string(self._plugin_widgets["genre_queue_mode"].get_selected())
        if "genre_track_to_add" in self._plugin_widgets:
            self.config.genre.track_to_add = int(self._plugin_widgets["genre_track_to_add"].get_value())
        if "genre_album_to_add" in self._plugin_widgets:
            self.config.genre.album_to_add = int(self._plugin_widgets["genre_album_to_add"].get_value())
        if "genre_single_album" in self._plugin_widgets:
            self.config.genre.single_album = self._plugin_widgets["genre_single_album"].get_active()

        if "tags_queue_mode" in self._plugin_widgets:
            m = self._plugin_widgets["tags_queue_mode"].get_model()
            self.config.tags.queue_mode = m.get_string(self._plugin_widgets["tags_queue_mode"].get_selected())
        if "tags_filter" in self._plugin_widgets:
            self.config.tags.filter = self._plugin_widgets["tags_filter"].get_text()
        if "tags_genre" in self._plugin_widgets:
            self.config.tags.genre = self._plugin_widgets["tags_genre"].get_text()
        if "tags_date" in self._plugin_widgets:
            self.config.tags.date = self._plugin_widgets["tags_date"].get_text()
        if "tags_comment" in self._plugin_widgets:
            self.config.tags.comment = self._plugin_widgets["tags_comment"].get_text()
        if "tags_label" in self._plugin_widgets:
            self.config.tags.label = self._plugin_widgets["tags_label"].get_text()
        if "tags_track_to_add" in self._plugin_widgets:
            self.config.tags.track_to_add = int(self._plugin_widgets["tags_track_to_add"].get_value())
        if "tags_single_album" in self._plugin_widgets:
            self.config.tags.single_album = self._plugin_widgets["tags_single_album"].get_active()
