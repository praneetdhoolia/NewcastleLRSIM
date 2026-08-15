#!/usr/bin/env python
"""Deterministic gzip and zip output.

`gzip.open(path, 'w')` stamps the current wall-clock time into the gzip header,
so two builds of identical content produce different bytes and therefore
different sha256 digests in `data/MANIFEST.csv`. That breaks the project's
determinism rule and makes every rebuild look like a data change.

`gzip_writer` pins the header mtime to 0 and suppresses the embedded original
filename, so the compressed bytes depend only on the content.
"""
import io
import gzip


def gzip_writer(path, text=True, compresslevel=6, encoding='utf-8'):
    """Open `path` for writing gzip with a fixed, content-independent header."""
    raw = open(path, 'wb')
    gz = gzip.GzipFile(filename='', mode='wb', compresslevel=compresslevel,
                       fileobj=raw, mtime=0)
    if not text:
        return _Closing(gz, raw)
    return _Closing(io.TextIOWrapper(gz, encoding=encoding, newline='\n'), raw, gz)


class _Closing:
    """Wrap a stream so closing it also closes everything underneath."""

    def __init__(self, stream, *others):
        self._stream = stream
        self._others = others

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        try:
            self._stream.close()
        finally:
            for o in reversed(self._others):
                try:
                    o.close()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Deterministic zip
# ---------------------------------------------------------------------------
# A zip entry carries the file's modification time in its local header, so
# `ZipFile.writestr(name, data)` stamps the wall clock and two builds of
# identical content produce different bytes - and therefore different sha256
# digests in data/MANIFEST.csv. Exactly the gzip problem one container up.
#
# `zip_entry` pins every entry to a fixed date, so the archive bytes depend only
# on the content and the order it is written in.

ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)   # the earliest a zip timestamp can express


def zip_entry(name, compress_type=None):
    """A ZipInfo with a fixed timestamp, for reproducible archives."""
    import zipfile
    info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
    info.compress_type = (zipfile.ZIP_DEFLATED if compress_type is None
                          else compress_type)
    info.external_attr = 0o644 << 16
    return info
