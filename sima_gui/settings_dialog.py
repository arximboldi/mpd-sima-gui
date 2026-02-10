"""Settings dialog for sima-gui using GTK4/Adwaita with GNOME Control Center style."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

from .config import SimaConfig, load_config, save_config


# Plugin definitions with their settings
PLUGINS = {
    "Crop": {
        "description": "Remove old tracks from the queue",
        "settings": ["consume"],
    },
    "Random": {
        "description": "Queue random tracks as fallback",
        "settings": ["random_track_to_add", "random_flavour"],
    },
    "Lastfm": {
        "description": "Recommendations based on Last.fm data",
        "settings": [
            "lastfm_queue_mode", "lastfm_max_art", "lastfm_depth",
            "lastfm_track_to_add", "lastfm_album_to_add",
            "lastfm_single_album", "lastfm_cache"
        ],
    },
    "Genre": {
        "description": "Queue tracks with similar genre tags",
        "settings": [
            "genre_queue_mode", "genre_track_to_add",
            "genre_album_to_add", "genre_single_album"
        ],
    },
    "Tags": {
        "description": "Queue tracks using custom tag filters",
        "settings": [
            "tags_queue_mode", "tags_filter", "tags_genre",
            "tags_date", "tags_comment", "tags_label",
            "tags_track_to_add", "tags_single_album"
        ],
    },
}


class SettingsWindow(Adw.ApplicationWindow):
    """Settings window with GNOME Control Center-like navigation."""

    def __init__(self, app: Adw.Application, apply_callback=None):
        super().__init__(
            application=app,
            title="Sima",
            default_width=900,
            default_height=650,
        )

        self.config = load_config()
        self._apply_callback = apply_callback
        self._plugin_rows = {}  # Store plugin rows for reordering
        self._plugin_widgets = {}  # Store setting widgets
        self._plugin_order = []  # Track plugin order explicitly

        self._build_ui()

    def set_apply_callback(self, callback):
        """Set callback to be called when settings are applied."""
        self._apply_callback = callback

    def _build_ui(self):
        """Build the Control Center-style UI."""
        # Main navigation view
        self.nav_view = Adw.NavigationView()
        self.set_content(self.nav_view)

        # Create main page with sidebar-style list
        self._create_main_page()

        # Create subpages
        self._create_mpd_page()
        self._create_general_page()
        self._create_plugins_page()

    def _create_main_page(self):
        """Create the main navigation page."""
        page = Adw.NavigationPage(title="Sima", tag="main")

        # Toolbar view for header
        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

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
        clamp = Adw.Clamp(maximum_size=600, margin_top=24, margin_bottom=24)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(box)

        # Store reference for subclasses
        self._main_box = box

        # Navigation items styled like Control Center
        nav_group = Adw.PreferencesGroup()
        box.append(nav_group)

        # MPD Connection
        row = self._create_nav_row(
            "MPD Connection",
            "Server address, port, and authentication",
            "network-server-symbolic",
            "mpd",
        )
        nav_group.add(row)

        # General
        row = self._create_nav_row(
            "General",
            "Queue behavior and logging",
            "preferences-system-symbolic",
            "general",
        )
        nav_group.add(row)

        # Plugins
        row = self._create_nav_row(
            "Plugins",
            "Configure recommendation sources",
            "application-x-addon-symbolic",
            "plugins",
        )
        nav_group.add(row)

        self.nav_view.push(page)

    def _create_nav_row(self, title: str, subtitle: str, icon: str, tag: str) -> Adw.ActionRow:
        """Create a navigation row."""
        row = Adw.ActionRow(
            title=title,
            subtitle=subtitle,
            activatable=True,
        )
        row.add_prefix(Gtk.Image(icon_name=icon))
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda r: self.nav_view.push_by_tag(tag))
        return row

    def _create_subpage(self, title: str, tag: str) -> tuple[Adw.NavigationPage, Gtk.Box]:
        """Create a subpage with standard layout."""
        page = Adw.NavigationPage(title=title, tag=tag)

        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vexpand=True,
        )
        toolbar_view.set_content(scrolled)

        clamp = Adw.Clamp(maximum_size=600, margin_top=24, margin_bottom=24)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(box)

        self.nav_view.add(page)
        return page, box

    def _create_spin_row(self, title: str, subtitle: str, value: int,
                         min_val: int, max_val: int, step: int = 1) -> Adw.SpinRow:
        """Create a spin button row."""
        adjustment = Gtk.Adjustment(
            value=value,
            lower=min_val,
            upper=max_val,
            step_increment=step,
            page_increment=10,
        )
        row = Adw.SpinRow(
            title=title,
            subtitle=subtitle,
            adjustment=adjustment,
        )
        return row

    def _create_entry_row(self, title: str, value: str,
                          password: bool = False) -> Adw.EntryRow | Adw.PasswordEntryRow:
        """Create an entry row."""
        if password:
            row = Adw.PasswordEntryRow(title=title)
        else:
            row = Adw.EntryRow(title=title)
        row.set_text(value)
        return row

    def _create_switch_row(self, title: str, subtitle: str, value: bool) -> Adw.SwitchRow:
        """Create a switch row."""
        row = Adw.SwitchRow(
            title=title,
            subtitle=subtitle,
            active=value,
        )
        return row

    def _create_combo_row(self, title: str, subtitle: str, options: list[str],
                          current: str) -> Adw.ComboRow:
        """Create a combo box row."""
        model = Gtk.StringList()
        selected_index = 0
        for i, option in enumerate(options):
            model.append(option)
            if option == current:
                selected_index = i

        row = Adw.ComboRow(
            title=title,
            subtitle=subtitle,
            model=model,
            selected=selected_index,
        )
        return row

    def _create_mpd_page(self):
        """Create MPD connection settings page."""
        page, box = self._create_subpage("MPD Connection", "mpd")

        group = Adw.PreferencesGroup(
            title="Server",
            description="Configure the MPD server connection",
        )
        box.append(group)

        self.mpd_host = self._create_entry_row("Host", self.config.mpd.host)
        group.add(self.mpd_host)

        self.mpd_port = self._create_spin_row(
            "Port", "Default: 6600",
            self.config.mpd.port, 1, 65535,
        )
        group.add(self.mpd_port)

        # Authentication group
        auth_group = Adw.PreferencesGroup(
            title="Authentication",
        )
        box.append(auth_group)

        self.mpd_password = self._create_entry_row(
            "Password", self.config.mpd.password, password=True
        )
        auth_group.add(self.mpd_password)

    def _create_general_page(self):
        """Create general settings page."""
        page, box = self._create_subpage("General", "general")

        # Queue group
        queue_group = Adw.PreferencesGroup(
            title="Queue",
            description="Control automatic track queuing",
        )
        box.append(queue_group)

        self.queue_length = self._create_spin_row(
            "Queue Threshold",
            "Tracks remaining before autoqueue triggers",
            self.config.sima.queue_length, 0, 100,
        )
        queue_group.add(self.queue_length)

        self.history_duration = self._create_spin_row(
            "History Duration",
            "Hours to remember played tracks",
            self.config.sima.history_duration, 0, 168,
        )
        queue_group.add(self.history_duration)

        # Behavior group
        behavior_group = Adw.PreferencesGroup(
            title="Behavior",
        )
        box.append(behavior_group)

        self.musicbrainzid = self._create_switch_row(
            "Use MusicBrainz IDs",
            "More accurate artist matching",
            self.config.sima.musicbrainzid,
        )
        behavior_group.add(self.musicbrainzid)

        self.repeat_disable = self._create_switch_row(
            "Pause in Repeat Mode",
            "Don't queue tracks during repeat",
            self.config.sima.repeat_disable_queue,
        )
        behavior_group.add(self.repeat_disable)

        self.single_disable = self._create_switch_row(
            "Pause in Single Mode",
            "Don't queue tracks during single mode",
            self.config.sima.single_disable_queue,
        )
        behavior_group.add(self.single_disable)

        # Logging group
        log_group = Adw.PreferencesGroup(
            title="Logging",
        )
        box.append(log_group)

        self.verbosity = self._create_combo_row(
            "Log Level",
            "Amount of detail in logs",
            ["debug", "info", "warning", "error"],
            self.config.log.verbosity,
        )
        log_group.add(self.verbosity)

    def _create_plugins_page(self):
        """Create unified plugins configuration page."""
        page, box = self._create_subpage("Plugins", "plugins")

        # Parse current plugin order from config
        current_plugins = [p.strip() for p in self.config.sima.internal.split(",") if p.strip()]

        # Ensure all known plugins are in the list (disabled ones at the end)
        all_plugins = list(PLUGINS.keys())
        enabled_plugins = [p for p in current_plugins if p in all_plugins]
        disabled_plugins = [p for p in all_plugins if p not in enabled_plugins]

        # Info text
        info_group = Adw.PreferencesGroup(
            description="Enable plugins and drag to reorder. Plugins are executed from top to bottom.",
        )
        box.append(info_group)

        # Plugin list
        self._plugins_group = Adw.PreferencesGroup(
            title="Active Plugins",
        )
        box.append(self._plugins_group)

        # Add enabled plugins first (in order), then disabled ones
        for plugin_name in enabled_plugins + disabled_plugins:
            is_enabled = plugin_name in enabled_plugins
            self._add_plugin_row(plugin_name, is_enabled)

    def _add_plugin_row(self, plugin_name: str, enabled: bool):
        """Add a plugin row with settings."""
        plugin_info = PLUGINS[plugin_name]

        # Create expander row for plugin
        expander = Adw.ExpanderRow(
            title=plugin_name,
            subtitle=plugin_info["description"],
        )

        # Enable switch
        switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        switch.set_active(enabled)
        switch.connect("notify::active", self._on_plugin_toggled, plugin_name)
        expander.add_prefix(switch)

        # Reorder buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        button_box.set_valign(Gtk.Align.CENTER)

        up_button = Gtk.Button(icon_name="go-up-symbolic")
        up_button.add_css_class("flat")
        up_button.set_tooltip_text("Move up")
        up_button.connect("clicked", self._on_move_plugin_up, plugin_name)
        button_box.append(up_button)

        down_button = Gtk.Button(icon_name="go-down-symbolic")
        down_button.add_css_class("flat")
        down_button.set_tooltip_text("Move down")
        down_button.connect("clicked", self._on_move_plugin_down, plugin_name)
        button_box.append(down_button)

        expander.add_suffix(button_box)

        # Add plugin-specific settings
        self._add_plugin_settings(expander, plugin_name)

        # Store references
        self._plugin_rows[plugin_name] = {
            "expander": expander,
            "switch": switch,
            "up_button": up_button,
            "down_button": down_button,
        }

        self._plugins_group.add(expander)
        self._plugin_order.append(plugin_name)

    def _add_plugin_settings(self, expander: Adw.ExpanderRow, plugin_name: str):
        """Add settings rows for a specific plugin."""
        if plugin_name == "Crop":
            row = self._create_spin_row(
                "Tracks to Keep",
                "Played tracks to retain (-1 = all)",
                self.config.crop.consume, -1, 1000,
            )
            self._plugin_widgets["consume"] = row
            expander.add_row(row)

        elif plugin_name == "Random":
            row = self._create_spin_row(
                "Tracks to Add", "",
                self.config.random.track_to_add, 1, 50,
            )
            self._plugin_widgets["random_track_to_add"] = row
            expander.add_row(row)

            row = self._create_combo_row(
                "Mode", "Selection strategy",
                ["sensible", "pure"],
                self.config.random.flavour,
            )
            self._plugin_widgets["random_flavour"] = row
            expander.add_row(row)

        elif plugin_name == "Lastfm":
            row = self._create_combo_row(
                "Queue Mode", "",
                ["track", "top", "album"],
                self.config.lastfm.queue_mode,
            )
            self._plugin_widgets["lastfm_queue_mode"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "Similar Artists Limit", "",
                self.config.lastfm.max_art, 1, 100,
            )
            self._plugin_widgets["lastfm_max_art"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "History Depth", "",
                self.config.lastfm.depth, 1, 10,
            )
            self._plugin_widgets["lastfm_depth"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "Tracks to Add", "",
                self.config.lastfm.track_to_add, 1, 50,
            )
            self._plugin_widgets["lastfm_track_to_add"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "Albums to Add", "",
                self.config.lastfm.album_to_add, 1, 10,
            )
            self._plugin_widgets["lastfm_album_to_add"] = row
            expander.add_row(row)

            row = self._create_switch_row(
                "Prevent Same Album", "",
                self.config.lastfm.single_album,
            )
            self._plugin_widgets["lastfm_single_album"] = row
            expander.add_row(row)

            row = self._create_switch_row(
                "Cache Responses", "",
                self.config.lastfm.cache,
            )
            self._plugin_widgets["lastfm_cache"] = row
            expander.add_row(row)

        elif plugin_name == "Genre":
            row = self._create_combo_row(
                "Queue Mode", "",
                ["track", "album"],
                self.config.genre.queue_mode,
            )
            self._plugin_widgets["genre_queue_mode"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "Tracks to Add", "",
                self.config.genre.track_to_add, 1, 50,
            )
            self._plugin_widgets["genre_track_to_add"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "Albums to Add", "",
                self.config.genre.album_to_add, 1, 10,
            )
            self._plugin_widgets["genre_album_to_add"] = row
            expander.add_row(row)

            row = self._create_switch_row(
                "Prevent Same Album", "",
                self.config.genre.single_album,
            )
            self._plugin_widgets["genre_single_album"] = row
            expander.add_row(row)

        elif plugin_name == "Tags":
            row = self._create_combo_row(
                "Queue Mode", "",
                ["track", "album"],
                self.config.tags.queue_mode,
            )
            self._plugin_widgets["tags_queue_mode"] = row
            expander.add_row(row)

            row = self._create_entry_row(
                "Filter Expression", self.config.tags.filter
            )
            self._plugin_widgets["tags_filter"] = row
            expander.add_row(row)

            row = self._create_entry_row(
                "Genre", self.config.tags.genre
            )
            self._plugin_widgets["tags_genre"] = row
            expander.add_row(row)

            row = self._create_entry_row(
                "Date", self.config.tags.date
            )
            self._plugin_widgets["tags_date"] = row
            expander.add_row(row)

            row = self._create_entry_row(
                "Comment", self.config.tags.comment
            )
            self._plugin_widgets["tags_comment"] = row
            expander.add_row(row)

            row = self._create_entry_row(
                "Label", self.config.tags.label
            )
            self._plugin_widgets["tags_label"] = row
            expander.add_row(row)

            row = self._create_spin_row(
                "Tracks to Add", "",
                self.config.tags.track_to_add, 1, 50,
            )
            self._plugin_widgets["tags_track_to_add"] = row
            expander.add_row(row)

            row = self._create_switch_row(
                "Prevent Same Album", "",
                self.config.tags.single_album,
            )
            self._plugin_widgets["tags_single_album"] = row
            expander.add_row(row)

    def _on_plugin_toggled(self, switch, pspec, plugin_name):
        """Handle plugin enable/disable toggle."""
        pass  # State is read when saving

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
        # Swap positions
        order[from_idx], order[to_idx] = order[to_idx], order[from_idx]

        # Save current switch states
        old_switches = {name: data["switch"].get_active() for name, data in self._plugin_rows.items()}

        # Remove all rows
        for name in list(self._plugin_rows.keys()):
            self._plugins_group.remove(self._plugin_rows[name]["expander"])

        # Clear stored references
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

        # Show toast
        toast = Adw.Toast(title="Settings applied")
        self.close()

    def _save_all_settings(self):
        """Save all settings from UI to config object."""
        # MPD
        self.config.mpd.host = self.mpd_host.get_text()
        self.config.mpd.port = int(self.mpd_port.get_value())
        self.config.mpd.password = self.mpd_password.get_text()

        # Sima general
        self.config.sima.queue_length = int(self.queue_length.get_value())
        self.config.sima.history_duration = int(self.history_duration.get_value())
        self.config.sima.musicbrainzid = self.musicbrainzid.get_active()
        self.config.sima.repeat_disable_queue = self.repeat_disable.get_active()
        self.config.sima.single_disable_queue = self.single_disable.get_active()

        # Log
        verbosity_model = self.verbosity.get_model()
        verbosity_index = self.verbosity.get_selected()
        self.config.log.verbosity = verbosity_model.get_string(verbosity_index)

        # Build plugin list from order and enabled state
        enabled_plugins = []
        order = self._get_plugin_order()
        base_priority = 10

        for i, plugin_name in enumerate(order):
            switch = self._plugin_rows[plugin_name]["switch"]
            if switch.get_active():
                enabled_plugins.append(plugin_name)

            # Set priority based on position
            priority = base_priority + (i * 10)
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

        # Crop settings
        if "consume" in self._plugin_widgets:
            self.config.crop.consume = int(self._plugin_widgets["consume"].get_value())

        # Random settings
        if "random_track_to_add" in self._plugin_widgets:
            self.config.random.track_to_add = int(self._plugin_widgets["random_track_to_add"].get_value())
        if "random_flavour" in self._plugin_widgets:
            model = self._plugin_widgets["random_flavour"].get_model()
            idx = self._plugin_widgets["random_flavour"].get_selected()
            self.config.random.flavour = model.get_string(idx)

        # Lastfm settings
        if "lastfm_queue_mode" in self._plugin_widgets:
            model = self._plugin_widgets["lastfm_queue_mode"].get_model()
            idx = self._plugin_widgets["lastfm_queue_mode"].get_selected()
            self.config.lastfm.queue_mode = model.get_string(idx)
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

        # Genre settings
        if "genre_queue_mode" in self._plugin_widgets:
            model = self._plugin_widgets["genre_queue_mode"].get_model()
            idx = self._plugin_widgets["genre_queue_mode"].get_selected()
            self.config.genre.queue_mode = model.get_string(idx)
        if "genre_track_to_add" in self._plugin_widgets:
            self.config.genre.track_to_add = int(self._plugin_widgets["genre_track_to_add"].get_value())
        if "genre_album_to_add" in self._plugin_widgets:
            self.config.genre.album_to_add = int(self._plugin_widgets["genre_album_to_add"].get_value())
        if "genre_single_album" in self._plugin_widgets:
            self.config.genre.single_album = self._plugin_widgets["genre_single_album"].get_active()

        # Tags settings
        if "tags_queue_mode" in self._plugin_widgets:
            model = self._plugin_widgets["tags_queue_mode"].get_model()
            idx = self._plugin_widgets["tags_queue_mode"].get_selected()
            self.config.tags.queue_mode = model.get_string(idx)
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
