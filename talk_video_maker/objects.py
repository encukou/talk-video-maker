import hashlib
import os
import struct
import subprocess


def hash_bytes(*args):
    hasher = hashlib.sha256()
    for i, arg in enumerate(args):
        if i:
            hasher.update(b'\0')
        hasher.update(arg)
    return hasher.hexdigest()


def run(argv):
    print('Running', argv)
    return subprocess.check_output(argv)


class Object:
    is_big_file = False

    def get_filename(self):
        return os.path.join('./__filecache__/', self.hash + self.ext)

    def save(self):
        filename = self.get_filename()
        if os.path.exists(filename):
            return filename
        try:
            os.makedirs(os.path.dirname(filename))
        except FileExistsError:
            pass
        try:
            self.save_to(filename)
        except Exception:
            try:
                os.unlink(filename)
            except FileNotFoundError:
                pass
            raise
        if not os.path.exists(filename):
            raise RuntimeError('file not saved to {}'.format(filename))
        self._filename = filename
        return filename

    @property
    def filename(self):
        try:
            return self._filename
        except:
            self._filename = self.save()
            return self._filename
    @filename.setter
    def filename(self, new):
        self._filename = new


class InputObject(Object):
    def __init__(self, *, filename=None):
        self.filename = filename
        stat = os.stat(filename)
        self.file_size = stat.st_size
        if self.is_big_file:
            packed = struct.pack('!LL', self.file_size, int(stat.st_mtime))
            self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                                   bytes(filename, 'utf-8'), packed)
        else:
            with open(filename, 'rb') as f:
                self.bytes = f.read()
                self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                                       self.bytes)

    def __repr__(self):
        return '<{} from {!r}>'.format(type(self).__name__, self.filename)
