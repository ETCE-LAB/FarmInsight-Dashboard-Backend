import logging
import os
import threading
import time
from collections import deque
from typing import Optional

from .matrix_notifier import matrix_client

# Farbzuordnung für verschiedene Log-Level
LOG_LEVEL_COLORS = {
    'INFO': '#36a64f',      # Grün
    'WARNING': '#ffc107',   # Gelb
    'ERROR': '#dc3545',     # Rot
    'CRITICAL': '#dc3545',  # Rot
    'DEBUG': '#ff00ff',     # Magenta
}

# Liste von Logger-Namen, deren Logs ignoriert werden sollten um Endlosschleifen zu vermeiden
# WICHTIG: Alle Logger die während Matrix-Nachrichten-Versand aktiv sein könnten müssen hier sein!
IGNORED_LOGGER_NAMES = frozenset([
    # Matrix-bezogen
    'nio',
    'matrix',
    'matrix_notifier',
    'matrix_notifier_internal',  # Our internal matrix client logger
    'django_server.matrix_notifier',
    'django_server.custom_logger',
    'custom_logger',
    # Async/Threading
    'asyncio',
    'concurrent',
    'threading',
    # Datenbank-bezogen (kritisch für SQLite locking!)
    'django.db',
    'django.db.backends',
    'django.db.backends.schema',
    'django.db.backends.base',
    'django.db.backends.sqlite3',
    'aiosqlite',
    'sqlite3',
    # HTTP/Network
    'httpx',
    'httpcore',
    'urllib3',
    'requests',
    'h11',
    'h2',
    'hpack',
    # Django internals
    'django.request',
    'django.security',
    'django.template',
    'django.utils',
    # Andere Bibliotheken die Logs erzeugen könnten
    'PIL',
    'parso',
    'charset_normalizer',
    'certifi',
])


class MatrixLogHandler(logging.Handler):
    """
    Handler zum Senden von Log-Einträgen an Matrix-Räume.

    Verwendet einen Cache für die Raum-IDs um Datenbank-Abfragen zu minimieren
    und verhindert Endlosschleifen durch Filterung von Matrix-bezogenen Logs.

    Features:
    - Rate limiting per handler to avoid spamming
    - Deduplication of repeated messages
    - Async-safe caching of room IDs
    - Thread-local recursion prevention
    """

    # Klassen-Variablen für Caching und Thread-Safety
    _room_ids_cache: Optional[list] = None
    _cache_timestamp: float = 0
    _cache_lock = threading.Lock()
    _cache_ttl = 300  # Cache für 5 Minuten (erhöht von 60s)
    _is_emitting = threading.local()  # Thread-local Flag um Rekursion zu verhindern

    # Rate limiting für Log-Handler (Klassenattribute für Sharing zwischen Instanzen)
    _rate_limit_lock = threading.Lock()
    _message_timestamps: deque = deque(maxlen=100)  # Track last 100 message timestamps
    _rate_limit_window = 10.0  # Time window in seconds
    _rate_limit_max_messages = 20  # Max messages per window
    _rate_limited_until: float = 0  # Timestamp until which we're rate limited

    # Deduplication (Klassenattribute)
    _recent_messages: dict = {}  # message_hash -> (count, first_timestamp)
    _dedup_window = 30.0  # Deduplicate same messages within 30 seconds
    _dedup_lock = threading.Lock()

    # Flag to prevent concurrent DB fetches
    _is_fetching: bool = False

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def _should_ignore_record(self, record: logging.LogRecord) -> bool:
        """Prüft ob dieser Log-Eintrag ignoriert werden sollte."""
        # Prüfe ob wir bereits innerhalb eines emit() Aufrufs sind (Rekursionsschutz)
        if getattr(MatrixLogHandler._is_emitting, 'value', False):
            return True

        # Prüfe explizit ignorierte Logger
        record_name = record.name.lower()
        for ignored in IGNORED_LOGGER_NAMES:
            if ignored.lower() in record_name:
                return True

        return False

    def _get_cached_room_ids(self):
        """
        Holt die Raum-IDs aus dem Cache oder aus der Datenbank.
        Verwendet einen TTL-Cache um Datenbank-Zugriffe zu minimieren.

        This method is designed to be non-blocking:
        - Returns cached data if available
        - Only one thread at a time will fetch from DB
        - Returns empty list while fetch is in progress to avoid blocking

        CRITICAL: This method must NEVER block or cause DB locks that could affect
        the main application. All DB access is done outside the cache lock.
        """
        current_time = time.time()

        with MatrixLogHandler._cache_lock:
            # Prüfe ob Cache noch gültig ist
            if MatrixLogHandler._room_ids_cache is not None and (current_time - MatrixLogHandler._cache_timestamp) < MatrixLogHandler._cache_ttl:
                return list(MatrixLogHandler._room_ids_cache)  # Return a copy to prevent modification

            # If another thread is already fetching, return cached data or empty list
            if MatrixLogHandler._is_fetching:
                return list(MatrixLogHandler._room_ids_cache) if MatrixLogHandler._room_ids_cache is not None else []

            # Mark that we're fetching
            MatrixLogHandler._is_fetching = True

        # Cache ist abgelaufen, lade neue Daten (outside the lock!)
        room_ids = []
        try:
            from farminsight_dashboard_backend.models import Notification

            # Use a timeout for the DB query to prevent blocking
            # Note: SQLite doesn't support query timeouts, but we minimize risk by:
            # 1. Using a simple, indexed query
            # 2. Converting to list immediately
            # 3. Having the is_fetching flag prevent concurrent queries
            room_ids = list(Notification.objects.values_list('room_id', flat=True))

        except Exception:
            # Silently handle any errors - we'll return cached or empty data
            # Do NOT log here to prevent recursion!
            room_ids = list(MatrixLogHandler._room_ids_cache) if MatrixLogHandler._room_ids_cache is not None else []
        finally:
            # CRITICAL: Always reset _is_fetching to prevent permanent lockout
            with MatrixLogHandler._cache_lock:
                if room_ids:  # Only update cache if we got valid data
                    MatrixLogHandler._room_ids_cache = room_ids
                    MatrixLogHandler._cache_timestamp = current_time
                MatrixLogHandler._is_fetching = False

        return room_ids

    @classmethod
    def invalidate_cache(cls):
        """Invalidiert den Raum-ID-Cache. Sollte aufgerufen werden wenn Notifications geändert werden."""
        with cls._cache_lock:
            cls._room_ids_cache = None
            cls._cache_timestamp = 0

    def _is_rate_limited(self) -> bool:
        """Prüft ob wir gerade rate-limited sind."""
        current_time = time.time()

        with MatrixLogHandler._rate_limit_lock:
            # Check if we're still in a rate-limited period
            if current_time < MatrixLogHandler._rate_limited_until:
                return True

            # Clean up old timestamps
            while MatrixLogHandler._message_timestamps and MatrixLogHandler._message_timestamps[0] < current_time - MatrixLogHandler._rate_limit_window:
                MatrixLogHandler._message_timestamps.popleft()

            # Check if we've exceeded the rate limit
            if len(MatrixLogHandler._message_timestamps) >= MatrixLogHandler._rate_limit_max_messages:
                # Rate limit for 30 seconds
                MatrixLogHandler._rate_limited_until = current_time + 30.0
                return True

            # Record this message timestamp
            MatrixLogHandler._message_timestamps.append(current_time)
            return False

    def _check_dedup(self, message: str) -> tuple[bool, int]:
        """
        Prüft ob diese Nachricht ein Duplikat ist.
        Returns: (is_duplicate, count)
        """
        current_time = time.time()
        message_hash = hash(message)

        with MatrixLogHandler._dedup_lock:
            # Clean up old entries
            expired_keys = [
                k for k, (_, ts) in MatrixLogHandler._recent_messages.items()
                if current_time - ts > MatrixLogHandler._dedup_window
            ]
            for k in expired_keys:
                del MatrixLogHandler._recent_messages[k]

            if message_hash in MatrixLogHandler._recent_messages:
                count, first_ts = MatrixLogHandler._recent_messages[message_hash]
                MatrixLogHandler._recent_messages[message_hash] = (count + 1, first_ts)
                # Only let through every 5th duplicate
                if count % 5 != 0:
                    return True, count + 1
                return False, count + 1
            else:
                MatrixLogHandler._recent_messages[message_hash] = (1, current_time)
                return False, 1

    def emit(self, record: logging.LogRecord):
        """Sucht den korrekten Raum und sendet den Log-Eintrag an Matrix."""
        # Verhindert eine Endlosschleife durch verschiedene Checks
        if self._should_ignore_record(record):
            return

        # Quick check if matrix client is available (send_message_sync will do proper checks)
        if not matrix_client.loop:
            return

        # Rate limiting check
        if self._is_rate_limited():
            return

        # Setze Rekursions-Flag (verhindert rekursive Aufrufe während emit läuft)
        MatrixLogHandler._is_emitting.value = True

        try:
            # Hole gecachte Raum-IDs (synchron, kein DB-Zugriff bei Cache-Hit)
            room_ids = self._get_cached_room_ids()
            if not room_ids:
                return

            # Formatiere die Nachricht einmal
            try:
                message_text = record.getMessage()
            except Exception:
                # Falls die Nachricht nicht formatiert werden kann, ignorieren
                return

            # Deduplication check
            is_duplicate, dup_count = self._check_dedup(message_text)
            if is_duplicate:
                return

            plain_text = message_text
            if dup_count > 1:
                plain_text = f"[Repeated {dup_count}x] {message_text}"

            color = LOG_LEVEL_COLORS.get(record.levelname, '#6c757d')

            dup_indicator = f" <em>(repeated {dup_count}x)</em>" if dup_count > 1 else ""
            html_body = (
                f'<p><font color="{color}"><strong>{record.levelname}</strong></font>{dup_indicator}</p>'
                f'<font color="#ffffff">{message_text}</font>'
                f'<p><font color="#aaaaaa"><em>Function: {record.funcName} File: {os.path.splitext(record.filename)[0]}:{record.lineno}</em></font></p>'
            )

            # Sende Nachrichten asynchron
            for room_id in room_ids:
                if room_id:
                    matrix_client.send_message_sync(room_id, plain_text, html_body)
        except Exception:
            # Silently ignore any errors to prevent recursion
            pass
        finally:
            MatrixLogHandler._is_emitting.value = False



class DatabaseLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        # This is a placeholder for the actual database logging implementation
        pass
