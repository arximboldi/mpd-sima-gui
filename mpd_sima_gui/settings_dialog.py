"""Settings dialog for mpd-sima-gui using GTK4/Adwaita."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

from .config import SimaConfig, load_config, save_config


PLUGINS = {
    "Crop": {"description": "Remove old tracks from the queue"},
    "Random": {"description": "Queue random tracks as fallback"},
    "Lastfm": {"description": "Recommendations based on Last.fm data"},
    "Genre": {"description": "Queue tracks with similar genre tags"},
    "Tags": {"description": "Queue tracks using custom tag filters"},
}


class SettingsWindow(Adw.ApplicationWindow):
    """Settings window with navigation subpages."""

    def __init__(self, app: Adw.Application, apply_callback=None):
        super().__init__(
            application=app,
            title="MPD Sima",
            default_width=550,
            default_height=600,
        )

        self.config = load_config()
        self._apply_callback = apply_callback
        self._plugin_rows = {}
        self._plugin_widgets = {}
        self._plugin_order = []
        self._initial_plugin_order = []
        self._initial_plugin_enabled = {}
        self._has_changes = False
        self._apply_button = None
        self._subpage_apply_buttons = []

        self._build_ui()
        self._connect_change_signals()
        self._store_initial_state()

    def set_apply_callback(self, callback):
        self._apply_callback = callback

    def _build_ui(self):
        """Build the navigation-based UI."""
        self.nav_view = Adw.NavigationView()
        self.set_content(self.nav_view)

        self._create_main_page()
        self._create_mpd_page()
        self._create_general_page()

        # Create plugin settings pages
        for plugin_name in PLUGINS:
            self._create_plugin_settings_page(plugin_name)

    def _create_main_page(self):
        """Create the main page with status and navigation."""
        page = Adw.NavigationPage(title="MPD Sima", tag="main")
        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        self._apply_button = Gtk.Button(label="Apply")
        self._apply_button.add_css_class("suggested-action")
        self._apply_button.set_sensitive(False)
        self._apply_button.connect("clicked", self._on_apply)
        header.pack_end(self._apply_button)

        reset_button = Gtk.Button(icon_name="edit-undo-symbolic")
        reset_button.set_tooltip_text("Reset to Defaults")
        reset_button.connect("clicked", self._on_reset_defaults)
        header.pack_start(reset_button)

        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        toolbar_view.set_content(scrolled)

        clamp = Adw.Clamp(maximum_size=500, margin_top=24, margin_bottom=24, margin_start=12, margin_end=12)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(box)
        self._main_box = box

        # Settings navigation
        settings_group = Adw.PreferencesGroup(title="Settings")
        box.append(settings_group)

        row = Adw.ActionRow(title="MPD Connection", subtitle="Server address and authentication", activatable=True)
        row.add_prefix(Gtk.Image(icon_name="network-server-symbolic"))
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda r: self.nav_view.push_by_tag("mpd"))
        settings_group.add(row)

        row = Adw.ActionRow(title="General", subtitle="Queue behavior and logging", activatable=True)
        row.add_prefix(Gtk.Image(icon_name="preferences-system-symbolic"))
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda r: self.nav_view.push_by_tag("general"))
        settings_group.add(row)

        # Plugins section
        self._create_plugins_section(box)

        self.nav_view.push(page)

    def _create_subpage(self, title: str, tag: str) -> tuple[Adw.NavigationPage, Gtk.Box]:
        page = Adw.NavigationPage(title=title, tag=tag)
        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Add apply button to subpage
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.set_sensitive(False)
        apply_btn.connect("clicked", self._on_apply)
        header.pack_end(apply_btn)
        self._subpage_apply_buttons.append(apply_btn)

        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        toolbar_view.set_content(scrolled)

        clamp = Adw.Clamp(maximum_size=500, margin_top=24, margin_bottom=24, margin_start=12, margin_end=12)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(box)

        self.nav_view.add(page)
        return page, box

    def _create_spin_row(self, title: str, subtitle: str, value: int, min_val: int, max_val: int) -> Adw.SpinRow:
        adj = Gtk.Adjustment(value=value, lower=min_val, upper=max_val, step_increment=1, page_increment=10)
        return Adw.SpinRow(title=title, subtitle=subtitle, adjustment=adj)

    def _create_entry_row(self, title: str, value: str, password: bool = False):
        row = Adw.PasswordEntryRow(title=title) if password else Adw.EntryRow(title=title)
        row.set_text(value)
        return row

    def _create_switch_row(self, title: str, subtitle: str, value: bool) -> Adw.SwitchRow:
        return Adw.SwitchRow(title=title, subtitle=subtitle, active=value)

    def _create_combo_row(self, title: str, subtitle: str, options: list[str], current: str) -> Adw.ComboRow:
        model = Gtk.StringList()
        selected = 0
        for i, opt in enumerate(options):
            model.append(opt)
            if opt == current:
                selected = i
        return Adw.ComboRow(title=title, subtitle=subtitle, model=model, selected=selected)

    def _create_mpd_page(self):
        page, box = self._create_subpage("MPD Connection", "mpd")
        group = Adw.PreferencesGroup()
        box.append(group)

        self.mpd_host = self._create_entry_row("Host", self.config.mpd.host)
        self.mpd_host.set_tooltip_text("MPD server hostname or IP address")
        group.add(self.mpd_host)

        self.mpd_port = self._create_spin_row("Port", "MPD server port (default: 6600)", self.config.mpd.port, 1, 65535)
        group.add(self.mpd_port)

        self.mpd_password = self._create_entry_row("Password", self.config.mpd.password, password=True)
        self.mpd_password.set_tooltip_text("Leave empty if no authentication required")
        group.add(self.mpd_password)

    def _create_general_page(self):
        page, box = self._create_subpage("General", "general")

        queue_group = Adw.PreferencesGroup(title="Queue")
        box.append(queue_group)

        self.queue_length = self._create_spin_row(
            "Queue Threshold", "Trigger autoqueue when this many tracks remain",
            self.config.sima.queue_length, 0, 100)
        queue_group.add(self.queue_length)

        self.history_duration = self._create_spin_row(
            "History Duration", "Hours to remember played tracks to avoid repeats",
            self.config.sima.history_duration, 0, 168)
        queue_group.add(self.history_duration)

        behavior_group = Adw.PreferencesGroup(title="Behavior")
        box.append(behavior_group)

        self.musicbrainzid = self._create_switch_row(
            "Use MusicBrainz IDs", "More accurate artist matching using unique identifiers",
            self.config.sima.musicbrainzid)
        behavior_group.add(self.musicbrainzid)

        self.repeat_disable = self._create_switch_row(
            "Pause in Repeat Mode", "Don't queue new tracks when repeat is enabled",
            self.config.sima.repeat_disable_queue)
        behavior_group.add(self.repeat_disable)

        self.single_disable = self._create_switch_row(
            "Pause in Single Mode", "Don't queue new tracks when single mode is enabled",
            self.config.sima.single_disable_queue)
        behavior_group.add(self.single_disable)

        log_group = Adw.PreferencesGroup(title="Logging")
        box.append(log_group)

        self.verbosity = self._create_combo_row(
            "Log Level", "Amount of detail in log output",
            ["debug", "info", "warning", "error"], self.config.log.verbosity)
        log_group.add(self.verbosity)

    def _create_plugins_section(self, box: Gtk.Box):
        current_plugins = [p.strip() for p in self.config.sima.internal.split(",") if p.strip()]
        all_plugins = list(PLUGINS.keys())
        enabled = [p for p in current_plugins if p in all_plugins]
        disabled = [p for p in all_plugins if p not in enabled]

        self._plugins_group = Adw.PreferencesGroup(
            title="Plugins",
            description="Enable and reorder (top = highest priority)")
        box.append(self._plugins_group)

        for name in enabled + disabled:
            self._add_plugin_row(name, name in enabled)

    def _add_plugin_row(self, plugin_name: str, enabled: bool):
        info = PLUGINS[plugin_name]

        row = Adw.ActionRow(title=plugin_name, subtitle=info["description"], activatable=True)

        switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        switch.set_active(enabled)
        row.add_prefix(switch)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2, valign=Gtk.Align.CENTER)

        up_btn = Gtk.Button(icon_name="go-up-symbolic")
        up_btn.add_css_class("flat")
        up_btn.connect("clicked", self._on_move_up, plugin_name)
        btn_box.append(up_btn)

        down_btn = Gtk.Button(icon_name="go-down-symbolic")
        down_btn.add_css_class("flat")
        down_btn.connect("clicked", self._on_move_down, plugin_name)
        btn_box.append(down_btn)

        row.add_suffix(btn_box)
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda r, n=plugin_name: self.nav_view.push_by_tag(f"plugin_{n}"))

        self._plugin_rows[plugin_name] = {"row": row, "switch": switch}
        self._plugins_group.add(row)
        self._plugin_order.append(plugin_name)

    def _create_plugin_settings_page(self, plugin_name: str):
        page, box = self._create_subpage(f"{plugin_name} Settings", f"plugin_{plugin_name}")

        if plugin_name == "Crop":
            group = Adw.PreferencesGroup()
            box.append(group)
            row = self._create_spin_row(
                "Tracks to Keep", "Number of played tracks to retain in queue (-1 = keep all)",
                self.config.crop.consume, -1, 1000)
            self._plugin_widgets["crop_consume"] = row
            group.add(row)

        elif plugin_name == "Random":
            group = Adw.PreferencesGroup()
            box.append(group)
            row = self._create_spin_row(
                "Tracks to Add", "Number of random tracks to queue",
                self.config.random.track_to_add, 1, 50)
            self._plugin_widgets["random_track_to_add"] = row
            group.add(row)

            row = self._create_combo_row(
                "Mode", "Selection strategy: sensible respects history, pure is fully random",
                ["sensible", "pure"], self.config.random.flavour)
            self._plugin_widgets["random_flavour"] = row
            group.add(row)

        elif plugin_name == "Lastfm":
            self._create_lastfm_settings(box)

        elif plugin_name == "Genre":
            self._create_genre_settings(box)

        elif plugin_name == "Tags":
            self._create_tags_settings(box)

    def _create_lastfm_settings(self, box: Gtk.Box):
        # Queue group
        queue_group = Adw.PreferencesGroup(title="Queue")
        box.append(queue_group)

        queue_mode = self._create_combo_row(
            "Queue Mode", "How to select tracks: individual tracks, top tracks, or full albums",
            ["track", "top", "album"], self.config.lastfm.queue_mode)
        self._plugin_widgets["lastfm_queue_mode"] = queue_mode
        queue_group.add(queue_mode)

        track_to_add = self._create_spin_row(
            "Tracks to Add", "Number of tracks to queue per cycle",
            self.config.lastfm.track_to_add, 1, 50)
        self._plugin_widgets["lastfm_track_to_add"] = track_to_add
        queue_group.add(track_to_add)

        album_to_add = self._create_spin_row(
            "Albums to Add", "Number of albums to queue per cycle",
            self.config.lastfm.album_to_add, 1, 10)
        self._plugin_widgets["lastfm_album_to_add"] = album_to_add
        queue_group.add(album_to_add)

        single_album = self._create_switch_row(
            "Prevent Same Album", "Avoid queueing multiple tracks from the same album",
            self.config.lastfm.single_album)
        self._plugin_widgets["lastfm_single_album"] = single_album
        queue_group.add(single_album)

        # Recommendations group
        rec_group = Adw.PreferencesGroup(title="Recommendations")
        box.append(rec_group)

        max_art = self._create_spin_row(
            "Similar Artists Limit", "Maximum number of similar artists to consider",
            self.config.lastfm.max_art, 1, 100)
        self._plugin_widgets["lastfm_max_art"] = max_art
        rec_group.add(max_art)

        depth = self._create_spin_row(
            "History Depth", "How many recent tracks to use for finding similar artists",
            self.config.lastfm.depth, 1, 10)
        self._plugin_widgets["lastfm_depth"] = depth
        rec_group.add(depth)

        cache = self._create_switch_row(
            "Cache Responses", "Store Last.fm API responses for better performance",
            self.config.lastfm.cache)
        self._plugin_widgets["lastfm_cache"] = cache
        rec_group.add(cache)

        # Set up visibility based on queue mode
        self._update_lastfm_visibility(queue_mode.get_selected())
        queue_mode.connect("notify::selected", self._on_lastfm_mode_changed)

    def _on_lastfm_mode_changed(self, combo, pspec):
        self._update_lastfm_visibility(combo.get_selected())

    def _update_lastfm_visibility(self, mode_index: int):
        # 0=track, 1=top, 2=album
        is_album = mode_index == 2
        self._plugin_widgets["lastfm_track_to_add"].set_visible(not is_album)
        self._plugin_widgets["lastfm_album_to_add"].set_visible(is_album)
        self._plugin_widgets["lastfm_single_album"].set_visible(not is_album)

    def _create_genre_settings(self, box: Gtk.Box):
        # Queue group
        queue_group = Adw.PreferencesGroup(title="Queue")
        box.append(queue_group)

        queue_mode = self._create_combo_row(
            "Queue Mode", "Queue individual tracks or full albums",
            ["track", "album"], self.config.genre.queue_mode)
        self._plugin_widgets["genre_queue_mode"] = queue_mode
        queue_group.add(queue_mode)

        track_to_add = self._create_spin_row(
            "Tracks to Add", "Number of tracks to queue per cycle",
            self.config.genre.track_to_add, 1, 50)
        self._plugin_widgets["genre_track_to_add"] = track_to_add
        queue_group.add(track_to_add)

        album_to_add = self._create_spin_row(
            "Albums to Add", "Number of albums to queue per cycle",
            self.config.genre.album_to_add, 1, 10)
        self._plugin_widgets["genre_album_to_add"] = album_to_add
        queue_group.add(album_to_add)

        single_album = self._create_switch_row(
            "Prevent Same Album", "Avoid queueing multiple tracks from the same album",
            self.config.genre.single_album)
        self._plugin_widgets["genre_single_album"] = single_album
        queue_group.add(single_album)

        self._update_genre_visibility(queue_mode.get_selected())
        queue_mode.connect("notify::selected", self._on_genre_mode_changed)

    def _on_genre_mode_changed(self, combo, pspec):
        self._update_genre_visibility(combo.get_selected())

    def _update_genre_visibility(self, mode_index: int):
        is_album = mode_index == 1
        self._plugin_widgets["genre_track_to_add"].set_visible(not is_album)
        self._plugin_widgets["genre_album_to_add"].set_visible(is_album)
        self._plugin_widgets["genre_single_album"].set_visible(not is_album)

    def _create_tags_settings(self, box: Gtk.Box):
        # Queue group
        queue_group = Adw.PreferencesGroup(title="Queue")
        box.append(queue_group)

        queue_mode = self._create_combo_row(
            "Queue Mode", "Queue individual tracks or full albums",
            ["track", "album"], self.config.tags.queue_mode)
        self._plugin_widgets["tags_queue_mode"] = queue_mode
        queue_group.add(queue_mode)

        track_to_add = self._create_spin_row(
            "Tracks to Add", "Number of tracks to queue per cycle",
            self.config.tags.track_to_add, 1, 50)
        self._plugin_widgets["tags_track_to_add"] = track_to_add
        queue_group.add(track_to_add)

        album_to_add = self._create_spin_row(
            "Albums to Add", "Number of albums to queue per cycle",
            self.config.tags.album_to_add, 1, 10)
        self._plugin_widgets["tags_album_to_add"] = album_to_add
        queue_group.add(album_to_add)

        single_album = self._create_switch_row(
            "Prevent Same Album", "Avoid queueing multiple tracks from the same album",
            self.config.tags.single_album)
        self._plugin_widgets["tags_single_album"] = single_album
        queue_group.add(single_album)

        # Filters group
        filter_group = Adw.PreferencesGroup(title="Filters")
        box.append(filter_group)

        filter_row = self._create_entry_row("Filter Expression", self.config.tags.filter)
        filter_row.set_tooltip_text("Raw MPD protocol filter expression")
        self._plugin_widgets["tags_filter"] = filter_row
        filter_group.add(filter_row)

        genre_row = self._create_entry_row("Genre", self.config.tags.genre)
        genre_row.set_tooltip_text("Comma-separated genre names to match (OR logic)")
        self._plugin_widgets["tags_genre"] = genre_row
        filter_group.add(genre_row)

        date_row = self._create_entry_row("Date", self.config.tags.date)
        date_row.set_tooltip_text("Year or year range (e.g., 1990 or 1990-1999)")
        self._plugin_widgets["tags_date"] = date_row
        filter_group.add(date_row)

        comment_row = self._create_entry_row("Comment", self.config.tags.comment)
        comment_row.set_tooltip_text("Comma-separated comment values to match")
        self._plugin_widgets["tags_comment"] = comment_row
        filter_group.add(comment_row)

        label_row = self._create_entry_row("Label", self.config.tags.label)
        label_row.set_tooltip_text("Record label to match")
        self._plugin_widgets["tags_label"] = label_row
        filter_group.add(label_row)

        self._update_tags_visibility(queue_mode.get_selected())
        queue_mode.connect("notify::selected", self._on_tags_mode_changed)

    def _on_tags_mode_changed(self, combo, pspec):
        self._update_tags_visibility(combo.get_selected())

    def _update_tags_visibility(self, mode_index: int):
        is_album = mode_index == 1
        self._plugin_widgets["tags_track_to_add"].set_visible(not is_album)
        self._plugin_widgets["tags_album_to_add"].set_visible(is_album)
        self._plugin_widgets["tags_single_album"].set_visible(not is_album)

    def _get_plugin_order(self) -> list[str]:
        return list(self._plugin_order)

    def _on_move_up(self, button, plugin_name):
        order = self._get_plugin_order()
        idx = order.index(plugin_name)
        if idx > 0:
            self._rebuild_plugin_list(order, idx, idx - 1)

    def _on_move_down(self, button, plugin_name):
        order = self._get_plugin_order()
        idx = order.index(plugin_name)
        if idx < len(order) - 1:
            self._rebuild_plugin_list(order, idx, idx + 1)

    def _rebuild_plugin_list(self, order: list[str], from_idx: int, to_idx: int):
        order[from_idx], order[to_idx] = order[to_idx], order[from_idx]
        old_switches = {n: d["switch"].get_active() for n, d in self._plugin_rows.items()}

        for name in list(self._plugin_rows.keys()):
            self._plugins_group.remove(self._plugin_rows[name]["row"])

        self._plugin_rows.clear()
        self._plugin_order.clear()

        for name in order:
            self._add_plugin_row(name, old_switches[name])

        # Reconnect switch signals and check for changes
        for name, data in self._plugin_rows.items():
            data["switch"].connect("notify::active", self._on_value_changed)
        self._check_for_changes()

    def _on_apply(self, button):
        self._save_all_settings()
        save_config(self.config)
        if self._apply_callback:
            self._apply_callback()
        self._store_initial_state()
        self._has_changes = False
        if self._apply_button:
            self._apply_button.set_sensitive(False)
        for btn in self._subpage_apply_buttons:
            btn.set_sensitive(False)

    def _on_reset_defaults(self, button):
        """Reset all settings to defaults."""
        self.config = SimaConfig()
        self._load_config_to_widgets()
        self._check_for_changes()

    def _load_config_to_widgets(self):
        """Load current config values into all widgets."""
        # MPD settings
        self.mpd_host.set_text(self.config.mpd.host)
        self.mpd_port.set_value(self.config.mpd.port)
        self.mpd_password.set_text(self.config.mpd.password)

        # General settings
        self.queue_length.set_value(self.config.sima.queue_length)
        self.history_duration.set_value(self.config.sima.history_duration)
        self.musicbrainzid.set_active(self.config.sima.musicbrainzid)
        self.repeat_disable.set_active(self.config.sima.repeat_disable_queue)
        self.single_disable.set_active(self.config.sima.single_disable_queue)

        # Find verbosity index
        verbosity_options = ["debug", "info", "warning", "error"]
        verbosity_idx = verbosity_options.index(self.config.log.verbosity) if self.config.log.verbosity in verbosity_options else 1
        self.verbosity.set_selected(verbosity_idx)

        # Plugin settings
        if "crop_consume" in self._plugin_widgets:
            self._plugin_widgets["crop_consume"].set_value(self.config.crop.consume)

        if "random_track_to_add" in self._plugin_widgets:
            self._plugin_widgets["random_track_to_add"].set_value(self.config.random.track_to_add)
        if "random_flavour" in self._plugin_widgets:
            flavour_options = ["sensible", "pure"]
            flavour_idx = flavour_options.index(self.config.random.flavour) if self.config.random.flavour in flavour_options else 0
            self._plugin_widgets["random_flavour"].set_selected(flavour_idx)

        # Lastfm settings
        if "lastfm_queue_mode" in self._plugin_widgets:
            mode_options = ["track", "top", "album"]
            mode_idx = mode_options.index(self.config.lastfm.queue_mode) if self.config.lastfm.queue_mode in mode_options else 0
            self._plugin_widgets["lastfm_queue_mode"].set_selected(mode_idx)
        if "lastfm_max_art" in self._plugin_widgets:
            self._plugin_widgets["lastfm_max_art"].set_value(self.config.lastfm.max_art)
        if "lastfm_depth" in self._plugin_widgets:
            self._plugin_widgets["lastfm_depth"].set_value(self.config.lastfm.depth)
        if "lastfm_track_to_add" in self._plugin_widgets:
            self._plugin_widgets["lastfm_track_to_add"].set_value(self.config.lastfm.track_to_add)
        if "lastfm_album_to_add" in self._plugin_widgets:
            self._plugin_widgets["lastfm_album_to_add"].set_value(self.config.lastfm.album_to_add)
        if "lastfm_single_album" in self._plugin_widgets:
            self._plugin_widgets["lastfm_single_album"].set_active(self.config.lastfm.single_album)
        if "lastfm_cache" in self._plugin_widgets:
            self._plugin_widgets["lastfm_cache"].set_active(self.config.lastfm.cache)

        # Genre settings
        if "genre_queue_mode" in self._plugin_widgets:
            mode_options = ["track", "album"]
            mode_idx = mode_options.index(self.config.genre.queue_mode) if self.config.genre.queue_mode in mode_options else 0
            self._plugin_widgets["genre_queue_mode"].set_selected(mode_idx)
        if "genre_track_to_add" in self._plugin_widgets:
            self._plugin_widgets["genre_track_to_add"].set_value(self.config.genre.track_to_add)
        if "genre_album_to_add" in self._plugin_widgets:
            self._plugin_widgets["genre_album_to_add"].set_value(self.config.genre.album_to_add)
        if "genre_single_album" in self._plugin_widgets:
            self._plugin_widgets["genre_single_album"].set_active(self.config.genre.single_album)

        # Tags settings
        if "tags_queue_mode" in self._plugin_widgets:
            mode_options = ["track", "album"]
            mode_idx = mode_options.index(self.config.tags.queue_mode) if self.config.tags.queue_mode in mode_options else 0
            self._plugin_widgets["tags_queue_mode"].set_selected(mode_idx)
        if "tags_filter" in self._plugin_widgets:
            self._plugin_widgets["tags_filter"].set_text(self.config.tags.filter)
        if "tags_genre" in self._plugin_widgets:
            self._plugin_widgets["tags_genre"].set_text(self.config.tags.genre)
        if "tags_date" in self._plugin_widgets:
            self._plugin_widgets["tags_date"].set_text(self.config.tags.date)
        if "tags_comment" in self._plugin_widgets:
            self._plugin_widgets["tags_comment"].set_text(self.config.tags.comment)
        if "tags_label" in self._plugin_widgets:
            self._plugin_widgets["tags_label"].set_text(self.config.tags.label)
        if "tags_track_to_add" in self._plugin_widgets:
            self._plugin_widgets["tags_track_to_add"].set_value(self.config.tags.track_to_add)
        if "tags_album_to_add" in self._plugin_widgets:
            self._plugin_widgets["tags_album_to_add"].set_value(self.config.tags.album_to_add)
        if "tags_single_album" in self._plugin_widgets:
            self._plugin_widgets["tags_single_album"].set_active(self.config.tags.single_album)

        # Reset plugin order and enabled states to defaults
        default_plugins = [p.strip() for p in SimaConfig().sima.internal.split(",") if p.strip()]
        all_plugins = list(PLUGINS.keys())
        enabled = [p for p in default_plugins if p in all_plugins]
        disabled = [p for p in all_plugins if p not in enabled]
        default_order = enabled + disabled

        # Rebuild plugin list with default order and enabled states
        old_switches = {name: name in enabled for name in all_plugins}
        for name in list(self._plugin_rows.keys()):
            self._plugins_group.remove(self._plugin_rows[name]["row"])
        self._plugin_rows.clear()
        self._plugin_order.clear()
        for name in default_order:
            self._add_plugin_row(name, old_switches[name])
        for name, data in self._plugin_rows.items():
            data["switch"].connect("notify::active", self._on_value_changed)

    def _save_all_settings(self):
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
        self.config.log.verbosity = self.verbosity.get_model().get_string(self.verbosity.get_selected())

        # Plugins (first in list = highest priority)
        enabled = []
        num_plugins = len(self._plugin_order)
        for i, name in enumerate(self._plugin_order):
            switch = self._plugin_rows[name]["switch"]
            priority = (num_plugins - i) * 10
            if switch.get_active():
                enabled.append(name)

            if name == "Crop":
                self.config.crop.priority = priority
            elif name == "Random":
                self.config.random.priority = priority
            elif name == "Lastfm":
                self.config.lastfm.priority = priority
            elif name == "Genre":
                self.config.genre.priority = priority
            elif name == "Tags":
                self.config.tags.priority = priority

        self.config.sima.internal = ", ".join(enabled)

        # Plugin settings
        if "crop_consume" in self._plugin_widgets:
            self.config.crop.consume = int(self._plugin_widgets["crop_consume"].get_value())

        if "random_track_to_add" in self._plugin_widgets:
            self.config.random.track_to_add = int(self._plugin_widgets["random_track_to_add"].get_value())
        if "random_flavour" in self._plugin_widgets:
            self.config.random.flavour = self._plugin_widgets["random_flavour"].get_model().get_string(
                self._plugin_widgets["random_flavour"].get_selected())

        if "lastfm_queue_mode" in self._plugin_widgets:
            self.config.lastfm.queue_mode = self._plugin_widgets["lastfm_queue_mode"].get_model().get_string(
                self._plugin_widgets["lastfm_queue_mode"].get_selected())
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
            self.config.genre.queue_mode = self._plugin_widgets["genre_queue_mode"].get_model().get_string(
                self._plugin_widgets["genre_queue_mode"].get_selected())
        if "genre_track_to_add" in self._plugin_widgets:
            self.config.genre.track_to_add = int(self._plugin_widgets["genre_track_to_add"].get_value())
        if "genre_album_to_add" in self._plugin_widgets:
            self.config.genre.album_to_add = int(self._plugin_widgets["genre_album_to_add"].get_value())
        if "genre_single_album" in self._plugin_widgets:
            self.config.genre.single_album = self._plugin_widgets["genre_single_album"].get_active()

        if "tags_queue_mode" in self._plugin_widgets:
            self.config.tags.queue_mode = self._plugin_widgets["tags_queue_mode"].get_model().get_string(
                self._plugin_widgets["tags_queue_mode"].get_selected())
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
        if "tags_album_to_add" in self._plugin_widgets:
            self.config.tags.album_to_add = int(self._plugin_widgets["tags_album_to_add"].get_value())
        if "tags_single_album" in self._plugin_widgets:
            self.config.tags.single_album = self._plugin_widgets["tags_single_album"].get_active()

    def _store_initial_state(self):
        """Store initial widget values for change detection."""
        self._initial_values = {
            "mpd_host": self.mpd_host.get_text(),
            "mpd_port": self.mpd_port.get_value(),
            "mpd_password": self.mpd_password.get_text(),
            "queue_length": self.queue_length.get_value(),
            "history_duration": self.history_duration.get_value(),
            "musicbrainzid": self.musicbrainzid.get_active(),
            "repeat_disable": self.repeat_disable.get_active(),
            "single_disable": self.single_disable.get_active(),
            "verbosity": self.verbosity.get_selected(),
        }
        # Store plugin widget values
        for key, widget in self._plugin_widgets.items():
            if isinstance(widget, Adw.SpinRow):
                self._initial_values[key] = widget.get_value()
            elif isinstance(widget, Adw.SwitchRow):
                self._initial_values[key] = widget.get_active()
            elif isinstance(widget, Adw.ComboRow):
                self._initial_values[key] = widget.get_selected()
            elif isinstance(widget, (Adw.EntryRow, Adw.PasswordEntryRow)):
                self._initial_values[key] = widget.get_text()

        # Store plugin order and enabled state
        self._initial_plugin_order = list(self._plugin_order)
        self._initial_plugin_enabled = {
            name: data["switch"].get_active()
            for name, data in self._plugin_rows.items()
        }

    def _connect_change_signals(self):
        """Connect signals to detect changes."""
        # MPD settings
        self.mpd_host.connect("changed", self._on_value_changed)
        self.mpd_port.connect("notify::value", self._on_value_changed)
        self.mpd_password.connect("changed", self._on_value_changed)

        # General settings
        self.queue_length.connect("notify::value", self._on_value_changed)
        self.history_duration.connect("notify::value", self._on_value_changed)
        self.musicbrainzid.connect("notify::active", self._on_value_changed)
        self.repeat_disable.connect("notify::active", self._on_value_changed)
        self.single_disable.connect("notify::active", self._on_value_changed)
        self.verbosity.connect("notify::selected", self._on_value_changed)

        # Plugin widgets
        for key, widget in self._plugin_widgets.items():
            if isinstance(widget, Adw.SpinRow):
                widget.connect("notify::value", self._on_value_changed)
            elif isinstance(widget, Adw.SwitchRow):
                widget.connect("notify::active", self._on_value_changed)
            elif isinstance(widget, Adw.ComboRow):
                widget.connect("notify::selected", self._on_value_changed)
            elif isinstance(widget, (Adw.EntryRow, Adw.PasswordEntryRow)):
                widget.connect("changed", self._on_value_changed)

        # Plugin switches
        for name, data in self._plugin_rows.items():
            data["switch"].connect("notify::active", self._on_value_changed)

    def _on_value_changed(self, *args):
        """Handle any value change."""
        self._check_for_changes()

    def _check_for_changes(self):
        """Check if any values have changed from initial state."""
        if not hasattr(self, "_initial_values"):
            return

        has_changes = False

        # Check basic settings
        checks = [
            ("mpd_host", self.mpd_host.get_text()),
            ("mpd_port", self.mpd_port.get_value()),
            ("mpd_password", self.mpd_password.get_text()),
            ("queue_length", self.queue_length.get_value()),
            ("history_duration", self.history_duration.get_value()),
            ("musicbrainzid", self.musicbrainzid.get_active()),
            ("repeat_disable", self.repeat_disable.get_active()),
            ("single_disable", self.single_disable.get_active()),
            ("verbosity", self.verbosity.get_selected()),
        ]

        for key, current in checks:
            if self._initial_values.get(key) != current:
                has_changes = True
                break

        # Check plugin widgets
        if not has_changes:
            for key, widget in self._plugin_widgets.items():
                if isinstance(widget, Adw.SpinRow):
                    current = widget.get_value()
                elif isinstance(widget, Adw.SwitchRow):
                    current = widget.get_active()
                elif isinstance(widget, Adw.ComboRow):
                    current = widget.get_selected()
                elif isinstance(widget, (Adw.EntryRow, Adw.PasswordEntryRow)):
                    current = widget.get_text()
                else:
                    continue

                if self._initial_values.get(key) != current:
                    has_changes = True
                    break

        # Check plugin order
        if not has_changes and self._plugin_order != self._initial_plugin_order:
            has_changes = True

        # Check plugin enabled states
        if not has_changes:
            for name, data in self._plugin_rows.items():
                if data["switch"].get_active() != self._initial_plugin_enabled.get(name):
                    has_changes = True
                    break

        self._has_changes = has_changes
        if self._apply_button:
            self._apply_button.set_sensitive(has_changes)
        for btn in self._subpage_apply_buttons:
            btn.set_sensitive(has_changes)
