"""Settings dialog for sima-gui using GTK4/Adwaita with GNOME Control Center style."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

from .config import SimaConfig, load_config, save_config


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

        # Create subpages for each section
        self._create_mpd_page()
        self._create_general_page()
        self._create_plugins_page()
        self._create_lastfm_page()
        self._create_advanced_page()

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
            "Crop, Random, and active plugins",
            "application-x-addon-symbolic",
            "plugins",
        )
        nav_group.add(row)

        # Last.fm
        row = self._create_nav_row(
            "Last.fm",
            "Similar artist recommendations",
            "audio-x-generic-symbolic",
            "lastfm",
        )
        nav_group.add(row)

        # Advanced
        row = self._create_nav_row(
            "Advanced",
            "Genre and Tags plugins",
            "preferences-other-symbolic",
            "advanced",
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
        """Create plugins configuration page."""
        page, box = self._create_subpage("Plugins", "plugins")

        # Active plugins
        plugins_group = Adw.PreferencesGroup(
            title="Active Plugins",
            description="Comma-separated list (e.g., Lastfm, Random, Crop)",
        )
        box.append(plugins_group)

        self.internal_plugins = self._create_entry_row(
            "Plugins", self.config.sima.internal
        )
        plugins_group.add(self.internal_plugins)

        # Crop expander
        crop_expander = Adw.ExpanderRow(
            title="Crop",
            subtitle="Remove old tracks from playlist",
        )
        plugins_group.add(crop_expander)

        self.crop_consume = self._create_spin_row(
            "Tracks to Keep",
            "Number of played tracks to retain (-1 = all)",
            self.config.crop.consume, -1, 1000,
        )
        crop_expander.add_row(self.crop_consume)

        self.crop_priority = self._create_spin_row(
            "Priority", "Lower runs earlier",
            self.config.crop.priority, 0, 200,
        )
        crop_expander.add_row(self.crop_priority)

        # Random expander
        random_expander = Adw.ExpanderRow(
            title="Random",
            subtitle="Fallback random track selection",
        )
        plugins_group.add(random_expander)

        self.random_tracks = self._create_spin_row(
            "Tracks to Add", "",
            self.config.random.track_to_add, 1, 50,
        )
        random_expander.add_row(self.random_tracks)

        self.random_flavour = self._create_combo_row(
            "Mode", "",
            ["sensible", "pure"],
            self.config.random.flavour,
        )
        random_expander.add_row(self.random_flavour)

        self.random_priority = self._create_spin_row(
            "Priority", "",
            self.config.random.priority, 0, 200,
        )
        random_expander.add_row(self.random_priority)

    def _create_lastfm_page(self):
        """Create Last.fm plugin settings page."""
        page, box = self._create_subpage("Last.fm", "lastfm")

        # Recommendations group
        rec_group = Adw.PreferencesGroup(
            title="Recommendations",
            description="How to find similar tracks",
        )
        box.append(rec_group)

        self.lastfm_queue_mode = self._create_combo_row(
            "Queue Mode",
            "Track selection strategy",
            ["track", "top", "album"],
            self.config.lastfm.queue_mode,
        )
        rec_group.add(self.lastfm_queue_mode)

        self.lastfm_max_art = self._create_spin_row(
            "Similar Artists Limit",
            "Maximum artists to consider",
            self.config.lastfm.max_art, 1, 100,
        )
        rec_group.add(self.lastfm_max_art)

        self.lastfm_depth = self._create_spin_row(
            "History Depth",
            "Recent tracks to base suggestions on",
            self.config.lastfm.depth, 1, 10,
        )
        rec_group.add(self.lastfm_depth)

        # Track selection group
        track_group = Adw.PreferencesGroup(
            title="Selection",
        )
        box.append(track_group)

        self.lastfm_track_to_add = self._create_spin_row(
            "Tracks to Add",
            "Per selection (track/top modes)",
            self.config.lastfm.track_to_add, 1, 50,
        )
        track_group.add(self.lastfm_track_to_add)

        self.lastfm_album_to_add = self._create_spin_row(
            "Albums to Add",
            "Per selection (album mode)",
            self.config.lastfm.album_to_add, 1, 10,
        )
        track_group.add(self.lastfm_album_to_add)

        self.lastfm_tracks_from_album = self._create_spin_row(
            "Tracks from Album",
            "0 = entire album",
            self.config.lastfm.track_to_add_from_album, 0, 50,
        )
        track_group.add(self.lastfm_tracks_from_album)

        self.lastfm_single_album = self._create_switch_row(
            "Prevent Same Album",
            "Avoid multiple tracks from one album",
            self.config.lastfm.single_album,
        )
        track_group.add(self.lastfm_single_album)

        # Advanced group
        adv_group = Adw.PreferencesGroup(
            title="Advanced",
        )
        box.append(adv_group)

        self.lastfm_cache = self._create_switch_row(
            "Cache Responses",
            "Store API responses for better performance",
            self.config.lastfm.cache,
        )
        adv_group.add(self.lastfm_cache)

        self.lastfm_priority = self._create_spin_row(
            "Priority", "",
            self.config.lastfm.priority, 0, 200,
        )
        adv_group.add(self.lastfm_priority)

    def _create_advanced_page(self):
        """Create advanced settings page."""
        page, box = self._create_subpage("Advanced", "advanced")

        # Genre plugin
        genre_group = Adw.PreferencesGroup(
            title="Genre Plugin",
            description="Offline recommendations using genre tags",
        )
        box.append(genre_group)

        self.genre_queue_mode = self._create_combo_row(
            "Queue Mode", "",
            ["track", "album"],
            self.config.genre.queue_mode,
        )
        genre_group.add(self.genre_queue_mode)

        self.genre_track_to_add = self._create_spin_row(
            "Tracks to Add", "",
            self.config.genre.track_to_add, 1, 50,
        )
        genre_group.add(self.genre_track_to_add)

        self.genre_album_to_add = self._create_spin_row(
            "Albums to Add", "",
            self.config.genre.album_to_add, 1, 10,
        )
        genre_group.add(self.genre_album_to_add)

        self.genre_single_album = self._create_switch_row(
            "Prevent Same Album", "",
            self.config.genre.single_album,
        )
        genre_group.add(self.genre_single_album)

        self.genre_priority = self._create_spin_row(
            "Priority", "",
            self.config.genre.priority, 0, 200,
        )
        genre_group.add(self.genre_priority)

        # Tags plugin
        tags_group = Adw.PreferencesGroup(
            title="Tags Plugin",
            description="Custom MPD filter-based queuing",
        )
        box.append(tags_group)

        self.tags_queue_mode = self._create_combo_row(
            "Queue Mode", "",
            ["track", "album"],
            self.config.tags.queue_mode,
        )
        tags_group.add(self.tags_queue_mode)

        self.tags_filter = self._create_entry_row(
            "Filter Expression", self.config.tags.filter
        )
        tags_group.add(self.tags_filter)

        self.tags_genre = self._create_entry_row(
            "Genre", self.config.tags.genre
        )
        tags_group.add(self.tags_genre)

        self.tags_date = self._create_entry_row(
            "Date", self.config.tags.date
        )
        tags_group.add(self.tags_date)

        self.tags_comment = self._create_entry_row(
            "Comment", self.config.tags.comment
        )
        tags_group.add(self.tags_comment)

        self.tags_label = self._create_entry_row(
            "Label", self.config.tags.label
        )
        tags_group.add(self.tags_label)

        self.tags_track_to_add = self._create_spin_row(
            "Tracks to Add", "",
            self.config.tags.track_to_add, 1, 50,
        )
        tags_group.add(self.tags_track_to_add)

        self.tags_single_album = self._create_switch_row(
            "Prevent Same Album", "",
            self.config.tags.single_album,
        )
        tags_group.add(self.tags_single_album)

        self.tags_priority = self._create_spin_row(
            "Priority", "",
            self.config.tags.priority, 0, 200,
        )
        tags_group.add(self.tags_priority)

    def _on_apply(self, button):
        """Handle apply button click."""
        self._save_all_settings()
        save_config(self.config)

        if self._apply_callback:
            self._apply_callback()

        # Show toast
        toast = Adw.Toast(title="Settings applied")
        # Find toast overlay if we have one, or just close
        self.close()

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
        verbosity_model = self.verbosity.get_model()
        verbosity_index = self.verbosity.get_selected()
        self.config.log.verbosity = verbosity_model.get_string(verbosity_index)

        # Crop
        self.config.crop.consume = int(self.crop_consume.get_value())
        self.config.crop.priority = int(self.crop_priority.get_value())

        # Random
        self.config.random.track_to_add = int(self.random_tracks.get_value())
        flavour_model = self.random_flavour.get_model()
        flavour_index = self.random_flavour.get_selected()
        self.config.random.flavour = flavour_model.get_string(flavour_index)
        self.config.random.priority = int(self.random_priority.get_value())

        # Lastfm
        queue_mode_model = self.lastfm_queue_mode.get_model()
        queue_mode_index = self.lastfm_queue_mode.get_selected()
        self.config.lastfm.queue_mode = queue_mode_model.get_string(queue_mode_index)
        self.config.lastfm.max_art = int(self.lastfm_max_art.get_value())
        self.config.lastfm.depth = int(self.lastfm_depth.get_value())
        self.config.lastfm.track_to_add = int(self.lastfm_track_to_add.get_value())
        self.config.lastfm.album_to_add = int(self.lastfm_album_to_add.get_value())
        self.config.lastfm.track_to_add_from_album = int(self.lastfm_tracks_from_album.get_value())
        self.config.lastfm.single_album = self.lastfm_single_album.get_active()
        self.config.lastfm.cache = self.lastfm_cache.get_active()
        self.config.lastfm.priority = int(self.lastfm_priority.get_value())

        # Genre
        genre_mode_model = self.genre_queue_mode.get_model()
        genre_mode_index = self.genre_queue_mode.get_selected()
        self.config.genre.queue_mode = genre_mode_model.get_string(genre_mode_index)
        self.config.genre.track_to_add = int(self.genre_track_to_add.get_value())
        self.config.genre.album_to_add = int(self.genre_album_to_add.get_value())
        self.config.genre.single_album = self.genre_single_album.get_active()
        self.config.genre.priority = int(self.genre_priority.get_value())

        # Tags
        tags_mode_model = self.tags_queue_mode.get_model()
        tags_mode_index = self.tags_queue_mode.get_selected()
        self.config.tags.queue_mode = tags_mode_model.get_string(tags_mode_index)
        self.config.tags.filter = self.tags_filter.get_text()
        self.config.tags.genre = self.tags_genre.get_text()
        self.config.tags.date = self.tags_date.get_text()
        self.config.tags.comment = self.tags_comment.get_text()
        self.config.tags.label = self.tags_label.get_text()
        self.config.tags.track_to_add = int(self.tags_track_to_add.get_value())
        self.config.tags.single_album = self.tags_single_album.get_active()
        self.config.tags.priority = int(self.tags_priority.get_value())
