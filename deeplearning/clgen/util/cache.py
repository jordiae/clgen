# Copyright (c) 2016-2020 Chris Cummins.
#
# clgen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# clgen is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with clgen.  If not, see <https://www.gnu.org/licenses/>.
"""This file contains the logic for managing CLgen filesystem caches."""
import os
import pathlib
import six
import atexit
import json
import pathlib
import re
import typing

from deeplearning.clgen.util import crypto
from deeplearning.clgen.util import fs

class Cache(object):
  """
  Cache for storing (key,value) relational data.

  A cache is a dictionary with a limited subset of a the
  functionality.
  """

  def get(self, key, default=None) -> typing.Optional[pathlib.Path]:
    """
    Retrieve an item from cache.

    Arguments:
        key: Item key.
        default (optional): Default value if item not found.
    """
    raise NotImplementedError

  def clear(self) -> None:
    """
    Remove all items from cache.
    """
    raise NotImplementedError

  def items(self) -> typing.Iterable[pathlib.Path]:
    """
    Returns a generator for iterating over (key, value) pairs.
    """
    raise NotImplementedError

  def __getitem__(self, key) -> pathlib.Path:
    """
    Retrieve an item from cache.

    Arguments:
       key: Item key.

    Raises:
       KeyError: If key is not in cache.
    """
    raise NotImplementedError

  def __setitem__(self, key, value) -> None:
    """
    Set (key, value) pair.
    """
    raise NotImplementedError

  def __contains__(self, key) -> bool:
    """
    Returns whether key is in cache.
    """
    raise NotImplementedError

  def __delitem__(self, key) -> None:
    """
    Remove (key, value) pair.
    """
    raise NotImplementedError

  def __iter__(self) -> typing.Iterator[pathlib.Path]:
    """
    Iterate over all cache entries.
    """
    raise NotImplementedError

  def __len__(self) -> int:
    """
    Get the number of entries in the cache.
    """
    raise NotImplementedError


class TransientCache(Cache):
  """
  An in-memory only cache.
  """

  def __init__(self, basecache=None):
    """
    Create a new transient cache.

    Optionally supports populating the cache with values of an
    existing cache.

    Arguments:
       basecache (TransientCache, optional): Cache to populate this new
         cache with.
    """
    self._data = {}

    if basecache is not None:
      for key, val in basecache.items():
        self._data[key] = val

  def get(self, key, default=None):
    if key in self._data:
      return self._data[key]
    else:
      return default

  def clear(self):
    self._data.clear()

  def items(self):
    return six.iteritems(self._data)

  def __getitem__(self, key):
    return self._data[key]

  def __setitem__(self, key, value):
    self._data[key] = value
    return value

  def __contains__(self, key):
    return key in self._data

  def __delitem__(self, key):
    del self._data[key]

  def __iter__(self):
    """
    Iterate over all cache entries.

    Returns:
        iterable: Entries in cache.
    """
    for value in self._data.values():
      yield value

  def __len__(self):
    """
    Get the number of cache entries.

    Returns:
        int: Number of entries in the cache.
    """
    return len(list(self._data.keys()))


class JsonCache(TransientCache):
  """
  A persistent, JSON-backed cache.

  Requires that (key, value) pairs are JSON serialisable.
  """

  def __init__(self, path, basecache=None):
    """
    Create a new JSON cache.

    Optionally supports populating the cache with values of an
    existing cache.

    Arguments:
       basecache (TransientCache, optional): Cache to populate this new
         cache with.
    """

    super(JsonCache, self).__init__()
    self.path = fs.abspath(path)

    if fs.exists(self.path) and fs.Read(self.path):
      with open(self.path) as file:
        self._data = json.load(file)

    if basecache is not None:
      for key, val in basecache.items():
        self._data[key] = val

    # Register exit handler
    atexit.register(self.write)

  def write(self):
    """
    Write contents of cache to disk.
    """
    with open(self.path, "w") as file:
      json.dump(
        self._data, file, sort_keys=True, indent=2, separators=(",", ": "),
      )


def hash_key(key):
  """
  Convert a key to a filename by hashing its value.
  """
  return crypto.sha1_str(json.dumps(key, sort_keys=True))


def escape_path(key):
  """
  Convert a key to a filename by escaping invalid characters.
  """
  return re.sub(r"[ \\/]+", "_", key)


class FSCache(Cache):
  """
  Persistent filesystem cache.

  Each key uniquely identifies a file.
  Each value is a file path.

  Adding a file to the cache moves it into the cahce directory.

  Members:
      path (str): Root cache.
      escape_key (fn): Function to convert keys to file names.
  """

  def __init__(self, root, escape_key=hash_key):
    """
    Create filesystem cache.

    Arguments:
        root (str): String.
        escape_key (fn, optional): Function to convert keys to file names.
    """
    self.path = pathlib.Path(root)
    self.escape_key = escape_key

    fs.mkdir(self.path)

  def clear(self):
    """
    Empty the filesystem cache.

    This deletes the entire cache directory.
    """
    fs.rm(self.path)

  def keypath(self, key):
    """
    Get the filesystem path for a key.

    Arguments:
        key: Key.

    Returns:
        str: Absolute path.
    """
    return fs.path(self.path, self.escape_key(key))

  def __getitem__(self, key):
    """
    Get path to file in cache.

    Arguments:
        key: Key.

    Returns:
        str: Path to cache value.

    Raises:
        KeyErorr: If key not in cache.
    """
    path = self.keypath(key)
    if fs.exists(path):
      return path
    else:
      raise KeyError(key)

  def __setitem__(self, key, value):
    """
    Emplace file in cache.

    Arguments:
        key: Key.
        value (str): Path of file to insert in cache.

    Raises:
        ValueError: If no "value" does nto exist.
    """
    if not fs.exists(value):
      raise ValueError(value)

    path = self.keypath(key)
    fs.mkdir(self.path)
    fs.mv(value, path)

  def __contains__(self, key):
    """
    Check cache contents.

    Arguments:
        key: Key.

    Returns:
        bool: True if key in cache, else false.
    """
    path = self.keypath(key)
    return fs.exists(path)

  def __delitem__(self, key):
    """
    Delete cached file.

    Arguments:
        key: Key.

    Raises:
        KeyError: If file not in cache.
    """
    path = self.keypath(key)
    if fs.exists(path):
      fs.rm(path)
    else:
      raise KeyError(key)

  def __iter__(self):
    """
    Iterate over all cached files.

    Returns:
        iterable: Paths in cache.
    """
    for path in fs.ls(self.path, abspaths=True):
      yield path

  def __len__(self):
    """
    Get the number of entries in the cache.

    Returns:
        int: Number of entries in the cache.
    """
    return len(list(fs.ls(self.path)))

  def get(self, key, default=None):
    """
    Fetch from cache.

    Arguments:
        key: Key.
        default (optional): Value returned if key not found.

    Returns:
        str: Path to cached file.
    """
    if key in self:
      return self[key]
    else:
      return default

  def ls(self, **kwargs):
    """
    List files in cache.

    Arguments:
        **kwargs: Keyword options to pass to fs.ls().

    Returns:
        iterable: List of files.
    """
    return fs.ls(self.path, **kwargs)

def cachepath(*relative_path_components: str) -> pathlib.Path:
  """Return path to file system cache.

  Args:
    *relative_path_components: Relative path of cache.

  Returns:
    Absolute path of file system cache.
  """
  cache_root = pathlib.Path(os.environ.get("CLGEN_CACHE", "~/.cache/clgen/"))
  cache_root.expanduser().mkdir(parents=True, exist_ok=True)
  return pathlib.Path(fs.path(cache_root, *relative_path_components))


def mkcache(*relative_path_components: str) -> FSCache:
  """Instantiate a file system cache.

  If the cache does not exist, one is created.

  Args:
    *relative_path_components: Relative path of cache.

  Returns:
    A filesystem cache instance.
  """
  return FSCache(
    cachepath(*relative_path_components), escape_key=escape_path
  )
