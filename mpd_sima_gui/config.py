"""Configuration management for mpd-sima-gui."""

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "mpd-sima-gui"
CACHE_DIR = Path.home() / ".cache" / "mpd-sima-gui"
CONFIG_FILE = CONFIG_DIR / "mpd_sima.cfg"
LOG_FILE = CACHE_DIR / "mpd-sima.log"


@dataclass
class MPDSection:
    """MPD server connection settings."""

    host: str = "localhost"
    port: int = 6600
    password: str = ""


@dataclass
class LogSection:
    """Logging configuration."""

    logfile: str = ""
    verbosity: str = "info"


@dataclass
class DaemonSection:
    """Daemon settings."""

    daemon: bool = False
    pidfile: str = ""


@dataclass
class SimaSection:
    """Core sima settings."""

    internal: str = "Lastfm, Random, Crop"
    history_duration: int = 8
    queue_length: int = 2
    musicbrainzid: bool = True
    repeat_disable_queue: bool = True
    single_disable_queue: bool = True


@dataclass
class CropSection:
    """Crop plugin settings."""

    consume: int = 10
    priority: int = 10


@dataclass
class RandomSection:
    """Random plugin settings."""

    track_to_add: int = 1
    flavour: str = "sensible"
    priority: int = 50


@dataclass
class LastfmSection:
    """Last.fm plugin settings."""

    queue_mode: str = "track"
    max_art: int = 20
    depth: int = 1
    single_album: bool = False
    track_to_add: int = 1
    album_to_add: int = 1
    track_to_add_from_album: int = 0
    cache: bool = True
    priority: int = 100


@dataclass
class GenreSection:
    """Genre plugin settings."""

    queue_mode: str = "track"
    single_album: bool = False
    track_to_add: int = 1
    album_to_add: int = 1
    priority: int = 80


@dataclass
class TagsSection:
    """Tags plugin settings."""

    queue_mode: str = "track"
    single_album: bool = False
    filter: str = ""
    comment: str = ""
    date: str = ""
    genre: str = ""
    label: str = ""
    originaldate: str = ""
    priority: int = 80
    track_to_add: int = 1
    album_to_add: int = 1


@dataclass
class SimaConfig:
    """Complete mpd-sima configuration."""

    mpd: MPDSection = field(default_factory=MPDSection)
    log: LogSection = field(default_factory=LogSection)
    daemon: DaemonSection = field(default_factory=DaemonSection)
    sima: SimaSection = field(default_factory=SimaSection)
    crop: CropSection = field(default_factory=CropSection)
    random: RandomSection = field(default_factory=RandomSection)
    lastfm: LastfmSection = field(default_factory=LastfmSection)
    genre: GenreSection = field(default_factory=GenreSection)
    tags: TagsSection = field(default_factory=TagsSection)


def ensure_dirs() -> None:
    """Ensure configuration and cache directories exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_bool(parser: configparser.ConfigParser, section: str, option: str, default: bool) -> bool:
    """Get boolean value from config parser."""
    try:
        return parser.getboolean(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        return default


def _get_int(parser: configparser.ConfigParser, section: str, option: str, default: int) -> int:
    """Get integer value from config parser."""
    try:
        return parser.getint(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        return default


def _get_str(parser: configparser.ConfigParser, section: str, option: str, default: str) -> str:
    """Get string value from config parser."""
    try:
        return parser.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


def load_config() -> SimaConfig:
    """Load configuration from file."""
    ensure_dirs()
    config = SimaConfig()

    if not CONFIG_FILE.exists():
        return config

    parser = configparser.ConfigParser()
    parser.read(CONFIG_FILE)

    # MPD section
    config.mpd.host = _get_str(parser, "MPD", "host", config.mpd.host)
    config.mpd.port = _get_int(parser, "MPD", "port", config.mpd.port)
    config.mpd.password = _get_str(parser, "MPD", "password", config.mpd.password)

    # Log section
    config.log.logfile = _get_str(parser, "log", "logfile", config.log.logfile)
    config.log.verbosity = _get_str(parser, "log", "verbosity", config.log.verbosity)

    # Daemon section
    config.daemon.daemon = _get_bool(parser, "daemon", "daemon", config.daemon.daemon)
    config.daemon.pidfile = _get_str(parser, "daemon", "pidfile", config.daemon.pidfile)

    # Sima section
    config.sima.internal = _get_str(parser, "sima", "internal", config.sima.internal)
    config.sima.history_duration = _get_int(parser, "sima", "history_duration", config.sima.history_duration)
    config.sima.queue_length = _get_int(parser, "sima", "queue_length", config.sima.queue_length)
    config.sima.musicbrainzid = _get_bool(parser, "sima", "musicbrainzid", config.sima.musicbrainzid)
    config.sima.repeat_disable_queue = _get_bool(parser, "sima", "repeat_disable_queue", config.sima.repeat_disable_queue)
    config.sima.single_disable_queue = _get_bool(parser, "sima", "single_disable_queue", config.sima.single_disable_queue)

    # Crop section
    config.crop.consume = _get_int(parser, "crop", "consume", config.crop.consume)
    config.crop.priority = _get_int(parser, "crop", "priority", config.crop.priority)

    # Random section
    config.random.track_to_add = _get_int(parser, "random", "track_to_add", config.random.track_to_add)
    config.random.flavour = _get_str(parser, "random", "flavour", config.random.flavour)
    config.random.priority = _get_int(parser, "random", "priority", config.random.priority)

    # Lastfm section
    config.lastfm.queue_mode = _get_str(parser, "lastfm", "queue_mode", config.lastfm.queue_mode)
    config.lastfm.max_art = _get_int(parser, "lastfm", "max_art", config.lastfm.max_art)
    config.lastfm.depth = _get_int(parser, "lastfm", "depth", config.lastfm.depth)
    config.lastfm.single_album = _get_bool(parser, "lastfm", "single_album", config.lastfm.single_album)
    config.lastfm.track_to_add = _get_int(parser, "lastfm", "track_to_add", config.lastfm.track_to_add)
    config.lastfm.album_to_add = _get_int(parser, "lastfm", "album_to_add", config.lastfm.album_to_add)
    config.lastfm.track_to_add_from_album = _get_int(parser, "lastfm", "track_to_add_from_album", config.lastfm.track_to_add_from_album)
    config.lastfm.cache = _get_bool(parser, "lastfm", "cache", config.lastfm.cache)
    config.lastfm.priority = _get_int(parser, "lastfm", "priority", config.lastfm.priority)

    # Genre section
    config.genre.queue_mode = _get_str(parser, "genre", "queue_mode", config.genre.queue_mode)
    config.genre.single_album = _get_bool(parser, "genre", "single_album", config.genre.single_album)
    config.genre.track_to_add = _get_int(parser, "genre", "track_to_add", config.genre.track_to_add)
    config.genre.album_to_add = _get_int(parser, "genre", "album_to_add", config.genre.album_to_add)
    config.genre.priority = _get_int(parser, "genre", "priority", config.genre.priority)

    # Tags section
    config.tags.queue_mode = _get_str(parser, "tags", "queue_mode", config.tags.queue_mode)
    config.tags.single_album = _get_bool(parser, "tags", "single_album", config.tags.single_album)
    config.tags.filter = _get_str(parser, "tags", "filter", config.tags.filter)
    config.tags.comment = _get_str(parser, "tags", "comment", config.tags.comment)
    config.tags.date = _get_str(parser, "tags", "date", config.tags.date)
    config.tags.genre = _get_str(parser, "tags", "genre", config.tags.genre)
    config.tags.label = _get_str(parser, "tags", "label", config.tags.label)
    config.tags.originaldate = _get_str(parser, "tags", "originaldate", config.tags.originaldate)
    config.tags.priority = _get_int(parser, "tags", "priority", config.tags.priority)
    config.tags.track_to_add = _get_int(parser, "tags", "track_to_add", config.tags.track_to_add)
    config.tags.album_to_add = _get_int(parser, "tags", "album_to_add", config.tags.album_to_add)

    return config


def save_config(config: SimaConfig) -> None:
    """Save configuration to file."""
    ensure_dirs()

    parser = configparser.ConfigParser()

    # MPD section
    parser.add_section("MPD")
    parser.set("MPD", "host", config.mpd.host)
    parser.set("MPD", "port", str(config.mpd.port))
    if config.mpd.password:
        parser.set("MPD", "password", config.mpd.password)

    # Log section
    parser.add_section("log")
    if config.log.logfile:
        parser.set("log", "logfile", config.log.logfile)
    parser.set("log", "verbosity", config.log.verbosity)

    # Daemon section - we manage this ourselves, don't daemonize
    parser.add_section("daemon")
    parser.set("daemon", "daemon", "false")
    if config.daemon.pidfile:
        parser.set("daemon", "pidfile", config.daemon.pidfile)

    # Sima section
    parser.add_section("sima")
    parser.set("sima", "internal", config.sima.internal)
    parser.set("sima", "history_duration", str(config.sima.history_duration))
    parser.set("sima", "queue_length", str(config.sima.queue_length))
    parser.set("sima", "musicbrainzid", str(config.sima.musicbrainzid).lower())
    parser.set("sima", "repeat_disable_queue", str(config.sima.repeat_disable_queue).lower())
    parser.set("sima", "single_disable_queue", str(config.sima.single_disable_queue).lower())

    # Crop section
    parser.add_section("crop")
    parser.set("crop", "consume", str(config.crop.consume))
    parser.set("crop", "priority", str(config.crop.priority))

    # Random section
    parser.add_section("random")
    parser.set("random", "track_to_add", str(config.random.track_to_add))
    parser.set("random", "flavour", config.random.flavour)
    parser.set("random", "priority", str(config.random.priority))

    # Lastfm section
    parser.add_section("lastfm")
    parser.set("lastfm", "queue_mode", config.lastfm.queue_mode)
    parser.set("lastfm", "max_art", str(config.lastfm.max_art))
    parser.set("lastfm", "depth", str(config.lastfm.depth))
    parser.set("lastfm", "single_album", str(config.lastfm.single_album).lower())
    parser.set("lastfm", "track_to_add", str(config.lastfm.track_to_add))
    parser.set("lastfm", "album_to_add", str(config.lastfm.album_to_add))
    parser.set("lastfm", "track_to_add_from_album", str(config.lastfm.track_to_add_from_album))
    parser.set("lastfm", "cache", str(config.lastfm.cache).lower())
    parser.set("lastfm", "priority", str(config.lastfm.priority))

    # Genre section
    parser.add_section("genre")
    parser.set("genre", "queue_mode", config.genre.queue_mode)
    parser.set("genre", "single_album", str(config.genre.single_album).lower())
    parser.set("genre", "track_to_add", str(config.genre.track_to_add))
    parser.set("genre", "album_to_add", str(config.genre.album_to_add))
    parser.set("genre", "priority", str(config.genre.priority))

    # Tags section
    parser.add_section("tags")
    parser.set("tags", "queue_mode", config.tags.queue_mode)
    parser.set("tags", "single_album", str(config.tags.single_album).lower())
    if config.tags.filter:
        parser.set("tags", "filter", config.tags.filter)
    if config.tags.comment:
        parser.set("tags", "comment", config.tags.comment)
    if config.tags.date:
        parser.set("tags", "date", config.tags.date)
    if config.tags.genre:
        parser.set("tags", "genre", config.tags.genre)
    if config.tags.label:
        parser.set("tags", "label", config.tags.label)
    if config.tags.originaldate:
        parser.set("tags", "originaldate", config.tags.originaldate)
    parser.set("tags", "priority", str(config.tags.priority))
    parser.set("tags", "track_to_add", str(config.tags.track_to_add))
    parser.set("tags", "album_to_add", str(config.tags.album_to_add))

    with open(CONFIG_FILE, "w") as f:
        parser.write(f)
