"""System tray support using DBus StatusNotifierItem for GTK4 compatibility."""

import os
import struct
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import GLib, Gio, GdkPixbuf

# DBus interface for StatusNotifierItem
SNI_INTERFACE = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <signal name="NewIcon"/>
    <signal name="NewTitle"/>
    <signal name="NewStatus">
      <arg type="s" name="status"/>
    </signal>
    <method name="Activate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
  </interface>
</node>
"""

# DBus interface for StatusNotifierWatcher
SNW_INTERFACE = "org.kde.StatusNotifierWatcher"

# DBusMenu interface
DBUSMENU_INTERFACE = """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg type="a(isvu)" name="events" direction="in"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="ai" name="updatesNeeded" direction="out"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)" name="removedProps"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
    <signal name="ItemActivationRequested">
      <arg type="i" name="id"/>
      <arg type="u" name="timestamp"/>
    </signal>
  </interface>
</node>
"""


class StatusIcon:
    """System tray icon using DBus StatusNotifierItem protocol."""

    ICON_ACTIVE = "sima-gui-enabled"
    ICON_INACTIVE = "sima-gui-disabled"
    ICON_SIZE = 22  # Standard tray icon size

    # Menu item IDs
    MENU_ROOT = 0
    MENU_ENABLED = 1
    MENU_SEP1 = 2
    MENU_LOGS = 3
    MENU_CONFIG = 4
    MENU_SETTINGS = 5
    MENU_SEP2 = 6
    MENU_QUIT = 7

    def __init__(self, app):
        self._app = app
        self._bus = None
        self._sni_registration_id = 0
        self._menu_registration_id = 0
        self._bus_name_id = 0
        self._enabled = True
        self._running = False
        self._available = False
        self._revision = 1
        self._bus_name = None
        self._icon_cache = {}

        self._load_icons()
        self._try_register()

    def _find_icon_path(self, icon_name: str) -> Path | None:
        """Find icon in XDG data directories."""
        xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/share").split(":")
        xdg_data_dirs.insert(0, str(Path.home() / ".local" / "share"))

        for data_dir in xdg_data_dirs:
            icon_path = Path(data_dir) / "icons" / "hicolor" / "scalable" / "apps" / f"{icon_name}.svg"
            if icon_path.exists():
                return icon_path

        # Also check package directory for development
        package_dir = Path(__file__).parent.parent / "logos"
        icon_path = package_dir / f"{icon_name}.svg"
        if icon_path.exists():
            return icon_path

        return None

    def _load_icons(self):
        """Load and cache icon pixmaps."""
        for icon_name in [self.ICON_ACTIVE, self.ICON_INACTIVE]:
            icon_path = self._find_icon_path(icon_name)
            if icon_path:
                print(f"Found icon {icon_name} at {icon_path}")
                try:
                    pixmap = self._svg_to_pixmap(icon_path)
                    if pixmap:
                        width, height, data = pixmap
                        print(f"Loaded icon {icon_name}: {width}x{height}, {len(data)} bytes")
                        self._icon_cache[icon_name] = pixmap
                    else:
                        print(f"Failed to convert icon {icon_name} to pixmap")
                except Exception as e:
                    print(f"Failed to load icon {icon_name}: {e}")
            else:
                print(f"Icon not found: {icon_name}")

    def _svg_to_pixmap(self, svg_path: Path) -> tuple | None:
        """Convert SVG to ARGB32 pixmap data for StatusNotifierItem."""
        try:
            size = self.ICON_SIZE

            # Load SVG using GdkPixbuf
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(svg_path), size, size)

            # Ensure we have alpha channel
            if not pixbuf.get_has_alpha():
                pixbuf = pixbuf.add_alpha(False, 0, 0, 0)

            width = pixbuf.get_width()
            height = pixbuf.get_height()
            rowstride = pixbuf.get_rowstride()
            pixels_raw = pixbuf.get_pixels()

            # GdkPixbuf gives us RGBA, SNI wants ARGB as 32-bit integers in network byte order
            # Use struct.pack to ensure correct byte order
            pixel_data = []
            for y in range(height):
                for x in range(width):
                    src_offset = y * rowstride + x * 4
                    r = pixels_raw[src_offset]
                    g = pixels_raw[src_offset + 1]
                    b = pixels_raw[src_offset + 2]
                    a = pixels_raw[src_offset + 3]
                    # Pack as big-endian 32-bit ARGB
                    argb = (a << 24) | (r << 16) | (g << 8) | b
                    pixel_data.append(struct.pack('>I', argb))

            return (width, height, b''.join(pixel_data))
        except Exception as e:
            print(f"Error converting SVG {svg_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @property
    def available(self) -> bool:
        """Check if status icon is available."""
        return self._available

    def _try_register(self):
        """Try to register with the StatusNotifierWatcher."""
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

            # Check if StatusNotifierWatcher is available
            try:
                proxy = Gio.DBusProxy.new_sync(
                    self._bus,
                    Gio.DBusProxyFlags.DO_NOT_AUTO_START,
                    None,
                    SNW_INTERFACE,
                    "/StatusNotifierWatcher",
                    SNW_INTERFACE,
                    None,
                )

                if proxy.get_name_owner() is None:
                    print("No StatusNotifierWatcher available - tray icon disabled")
                    return
            except Exception:
                print("StatusNotifierWatcher not found - tray icon disabled")
                return

            # Own a unique bus name for our item
            pid = os.getpid()
            self._bus_name = f"org.kde.StatusNotifierItem-{pid}-1"

            self._bus_name_id = Gio.bus_own_name(
                Gio.BusType.SESSION,
                self._bus_name,
                Gio.BusNameOwnerFlags.NONE,
                self._on_bus_acquired,
                self._on_name_acquired,
                self._on_name_lost,
            )

        except Exception as e:
            print(f"StatusNotifierItem not available: {e}")

    def _on_bus_acquired(self, connection, name):
        """Handle bus acquisition."""
        try:
            # Register StatusNotifierItem interface
            node_info = Gio.DBusNodeInfo.new_for_xml(SNI_INTERFACE)
            self._sni_registration_id = connection.register_object(
                "/StatusNotifierItem",
                node_info.interfaces[0],
                self._handle_sni_method_call,
                self._handle_sni_get_property,
                None,
            )

            # Register DBusMenu interface
            menu_node_info = Gio.DBusNodeInfo.new_for_xml(DBUSMENU_INTERFACE)
            self._menu_registration_id = connection.register_object(
                "/StatusNotifierItem/Menu",
                menu_node_info.interfaces[0],
                self._handle_menu_method_call,
                self._handle_menu_get_property,
                None,
            )
        except Exception as e:
            print(f"Failed to register DBus objects: {e}")

    def _on_name_acquired(self, connection, name):
        """Handle name acquisition - register with watcher."""
        try:
            proxy = Gio.DBusProxy.new_sync(
                connection,
                Gio.DBusProxyFlags.DO_NOT_AUTO_START,
                None,
                SNW_INTERFACE,
                "/StatusNotifierWatcher",
                SNW_INTERFACE,
                None,
            )

            proxy.call_sync(
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (name,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )

            self._available = True
            print(f"Tray icon registered: {name}")

        except Exception as e:
            print(f"Failed to register with StatusNotifierWatcher: {e}")

    def _on_name_lost(self, connection, name):
        """Handle name loss."""
        self._available = False

    def _handle_sni_method_call(self, connection, sender, path, interface, method, params, invocation):
        """Handle StatusNotifierItem method calls."""
        if method == "Activate":
            # Primary click - show settings
            self._app.show_settings()
            invocation.return_value(None)

        elif method == "SecondaryActivate":
            # Middle click - toggle enable/disable
            self._enabled = not self._enabled
            self._app.toggle_service(self._enabled)
            invocation.return_value(None)

        elif method == "ContextMenu":
            # Right click - menu is shown via DBusMenu
            invocation.return_value(None)

        else:
            invocation.return_dbus_error(
                "org.freedesktop.DBus.Error.UnknownMethod",
                f"Unknown method: {method}"
            )

    def _handle_sni_get_property(self, connection, sender, path, interface, property_name):
        """Handle StatusNotifierItem property access."""
        if property_name == "Category":
            return GLib.Variant("s", "ApplicationStatus")
        elif property_name == "Id":
            return GLib.Variant("s", "sima-gui")
        elif property_name == "Title":
            return GLib.Variant("s", "mpd-sima")
        elif property_name == "Status":
            return GLib.Variant("s", "Active")
        elif property_name == "IconName":
            # Return empty string to force use of IconPixmap if available
            icon_name = self.ICON_ACTIVE if self._running else self.ICON_INACTIVE
            if icon_name in self._icon_cache:
                return GLib.Variant("s", "")
            return GLib.Variant("s", icon_name)
        elif property_name == "IconPixmap":
            icon_name = self.ICON_ACTIVE if self._running else self.ICON_INACTIVE
            if icon_name in self._icon_cache:
                width, height, data = self._icon_cache[icon_name]
                print(f"IconPixmap requested: {icon_name}, {width}x{height}, {len(data)} bytes")
                # Convert bytes to list of integers for GLib.Variant
                pixel_list = list(data)
                return GLib.Variant("a(iiay)", [(width, height, pixel_list)])
            print(f"IconPixmap requested but no cache for: {icon_name}")
            return GLib.Variant("a(iiay)", [])
        elif property_name == "Menu":
            return GLib.Variant("o", "/StatusNotifierItem/Menu")
        return None

    def _handle_menu_method_call(self, connection, sender, path, interface, method, params, invocation):
        """Handle DBusMenu method calls."""
        try:
            if method == "GetLayout":
                parent_id, depth, props = params.unpack()
                layout = self._build_layout(parent_id, depth)
                result = GLib.Variant("(u(ia{sv}av))", (self._revision, layout))
                invocation.return_value(result)

            elif method == "GetGroupProperties":
                ids, prop_names = params.unpack()
                result = []
                for item_id in ids:
                    props = self._get_item_properties(item_id)
                    result.append((item_id, props))
                invocation.return_value(GLib.Variant("(a(ia{sv}))", (result,)))

            elif method == "GetProperty":
                item_id, prop_name = params.unpack()
                props = self._get_item_properties(item_id)
                if prop_name in props:
                    invocation.return_value(GLib.Variant("(v)", (props[prop_name],)))
                else:
                    invocation.return_dbus_error(
                        "com.canonical.dbusmenu.UnknownProperty",
                        f"Unknown property: {prop_name}"
                    )

            elif method == "Event":
                item_id, event_id, data, timestamp = params.unpack()
                self._handle_menu_event(item_id, event_id)
                invocation.return_value(None)

            elif method == "EventGroup":
                events = params.unpack()[0]
                errors = []
                for item_id, event_id, data, timestamp in events:
                    self._handle_menu_event(item_id, event_id)
                invocation.return_value(GLib.Variant("(ai)", (errors,)))

            elif method == "AboutToShow":
                item_id = params.unpack()[0]
                invocation.return_value(GLib.Variant("(b)", (False,)))

            elif method == "AboutToShowGroup":
                ids = params.unpack()[0]
                invocation.return_value(GLib.Variant("(aiai)", ([], [])))

            else:
                invocation.return_dbus_error(
                    "org.freedesktop.DBus.Error.UnknownMethod",
                    f"Unknown method: {method}"
                )
        except Exception as e:
            print(f"Error handling menu method {method}: {e}")
            import traceback
            traceback.print_exc()
            invocation.return_dbus_error(
                "org.freedesktop.DBus.Error.Failed",
                str(e)
            )

    def _handle_menu_get_property(self, connection, sender, path, interface, property_name):
        """Handle DBusMenu property access."""
        if property_name == "Version":
            return GLib.Variant("u", 3)
        elif property_name == "TextDirection":
            return GLib.Variant("s", "ltr")
        elif property_name == "Status":
            return GLib.Variant("s", "normal")
        elif property_name == "IconThemePath":
            return GLib.Variant("as", [])
        return None

    def _get_item_properties(self, item_id: int) -> dict:
        """Get properties for a menu item as a dict of GLib.Variant."""
        if item_id == self.MENU_ROOT:
            return {
                "children-display": GLib.Variant("s", "submenu"),
            }
        elif item_id == self.MENU_ENABLED:
            return {
                "label": GLib.Variant("s", "Enabled"),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
                "toggle-type": GLib.Variant("s", "checkmark"),
                "toggle-state": GLib.Variant("i", 1 if self._enabled else 0),
            }
        elif item_id == self.MENU_SEP1 or item_id == self.MENU_SEP2:
            return {
                "type": GLib.Variant("s", "separator"),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
            }
        elif item_id == self.MENU_LOGS:
            return {
                "label": GLib.Variant("s", "Show Logs"),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
            }
        elif item_id == self.MENU_CONFIG:
            return {
                "label": GLib.Variant("s", "Show Config"),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
            }
        elif item_id == self.MENU_SETTINGS:
            return {
                "label": GLib.Variant("s", "Settings"),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
            }
        elif item_id == self.MENU_QUIT:
            return {
                "label": GLib.Variant("s", "Quit"),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
            }
        return {}

    def _build_layout(self, parent_id: int, depth: int) -> tuple:
        """Build menu layout starting from parent_id."""
        props = self._get_item_properties(parent_id)

        if parent_id != self.MENU_ROOT or depth == 0:
            return (parent_id, props, [])

        # Build children for root
        children = []
        child_ids = [
            self.MENU_ENABLED,
            self.MENU_SEP1,
            self.MENU_LOGS,
            self.MENU_CONFIG,
            self.MENU_SETTINGS,
            self.MENU_SEP2,
            self.MENU_QUIT,
        ]

        for child_id in child_ids:
            child_props = self._get_item_properties(child_id)
            # Build the child struct directly - the av array expects variants
            # containing (ia{sv}av) structs
            child_struct = GLib.Variant("(ia{sv}av)", (child_id, child_props, []))
            children.append(child_struct)

        return (parent_id, props, children)

    def _handle_menu_event(self, item_id: int, event_id: str):
        """Handle menu item activation."""
        if event_id != "clicked":
            return

        if item_id == self.MENU_ENABLED:
            self._enabled = not self._enabled
            self._app.toggle_service(self._enabled)
            self._emit_properties_updated()
        elif item_id == self.MENU_LOGS:
            self._app.show_logs()
        elif item_id == self.MENU_CONFIG:
            self._app.show_config()
        elif item_id == self.MENU_SETTINGS:
            self._app.show_settings()
        elif item_id == self.MENU_QUIT:
            self._app.quit()

    def _emit_properties_updated(self):
        """Emit ItemsPropertiesUpdated signal for the enabled item."""
        if self._bus and self._available:
            try:
                props = self._get_item_properties(self.MENU_ENABLED)
                updated = [(self.MENU_ENABLED, props)]
                removed = []
                self._bus.emit_signal(
                    None,
                    "/StatusNotifierItem/Menu",
                    "com.canonical.dbusmenu",
                    "ItemsPropertiesUpdated",
                    GLib.Variant("(a(ia{sv})a(ias))", (updated, removed)),
                )
            except Exception as e:
                print(f"Failed to emit ItemsPropertiesUpdated: {e}")

    def _emit_layout_updated(self):
        """Emit LayoutUpdated signal."""
        if self._bus and self._available:
            self._revision += 1
            try:
                self._bus.emit_signal(
                    None,
                    "/StatusNotifierItem/Menu",
                    "com.canonical.dbusmenu",
                    "LayoutUpdated",
                    GLib.Variant("(ui)", (self._revision, 0)),
                )
            except Exception as e:
                print(f"Failed to emit LayoutUpdated: {e}")

    def _emit_new_icon(self):
        """Emit NewIcon signal."""
        if self._bus and self._available:
            try:
                self._bus.emit_signal(
                    None,
                    "/StatusNotifierItem",
                    "org.kde.StatusNotifierItem",
                    "NewIcon",
                    None,
                )
            except Exception as e:
                print(f"Failed to emit NewIcon: {e}")

    def update_icon(self, running: bool):
        """Update the icon based on running state."""
        self._running = running
        self._emit_new_icon()

    def set_enabled(self, enabled: bool):
        """Set the enabled state."""
        if self._enabled != enabled:
            self._enabled = enabled
            self._emit_properties_updated()

    def cleanup(self):
        """Clean up DBus registrations."""
        try:
            if self._bus:
                if self._sni_registration_id:
                    self._bus.unregister_object(self._sni_registration_id)
                    self._sni_registration_id = 0
                if self._menu_registration_id:
                    self._bus.unregister_object(self._menu_registration_id)
                    self._menu_registration_id = 0

            if self._bus_name_id:
                Gio.bus_unown_name(self._bus_name_id)
                self._bus_name_id = 0

            self._available = False
        except Exception as e:
            print(f"Error during cleanup: {e}")
