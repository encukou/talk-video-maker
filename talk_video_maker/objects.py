import hashlib
import os
import struct
import subprocess
import csv
import math

import lxml.etree


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


class InputObject:
    def __init__(self, *, filename=None):
        self.filename = filename
        stat = os.stat(filename)
        self.file_size = stat.st_size
        if self.is_big_file:
            print('input (small):', filename)
            packed = struct.pack('!LL', self.file_size, int(stat.st_mtime))
            self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                                   bytes(filename, 'utf-8'), packed)
        else:
            print('input (big):', filename)
            with open(filename, 'rb') as f:
                self.bytes = f.read()
                self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                                       self.bytes)

    def __repr__(self):
        return '<{} from {!r}>'.format(type(self).__name__, self.filename)


class Template(Object):
    is_big_file = False
    ext = '.svg'

    def set_text(self, id, text):
        return RetextedTemplate(self, id, text)

    def _dom_copy(self):
        return lxml.etree.XML(lxml.etree.tostring(self.dom))

    @property
    def dom(self):
        try:
            return self._dom
        except AttributeError:
            self._dom = self.get_dom()
            return self._dom

    def save_to(self, filename):
        str = lxml.etree.tostring(self.dom, pretty_print=True)
        with open(filename, 'wb') as f:
            f.write(str)


class InputTemplate(Template, InputObject):
    def get_dom(self):
        return lxml.etree.XML(self.bytes)


class ModifiedTemplate(Template):
    def get_dom(self):
        return self._dom_copy()


class RetextedTemplate(ModifiedTemplate):
    def __init__(self, parent, id, text):
        self.parent = parent
        self.id = id
        self.text = text
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               self.parent.hash.encode('utf-8'),
                               id.encode('utf-8'),
                               text.encode('utf-8'))

    def _dom_copy(self):
        dom = self.parent._dom_copy()
        xpath = './/*[@id="{}"]'.format(self.id)
        elems = dom.xpath(xpath)
        if not elems:
            raise LookupError('element {} not found in SVG'.format(self.id))
        for elem in dom.xpath(xpath):
            regions = elem.findall('./{*}flowPara')
            [elem] = regions
            elem.text = self.text
        return dom

    def __repr__(self):
        return '{s.parent}{{{s.id}->{s.text!r}}}'.format(s=self)


class ReducedTemplate(ModifiedTemplate):
    def __init__(self, parent, id):
        self.parent = parent
        self.id = id
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               self.parent.hash.encode('utf-8'),
                               id.encode('utf-8'))

    def _dom_copy(self):
        dom = self.parent._dom_copy()
        xpath = './/*[@id="{}"]'.format(self.id)
        elems = dom.xpath(xpath)
        if not elems:
            raise LookupError('element {} not found in SVG'.format(self.id))
        for elem in dom.xpath(xpath):
            regions = elem.findall('./{*}flowPara')
            [elem] = regions
            elem.text = self.text
        return dom

    def __repr__(self):
        return '{s.parent}{{{s.id}->{s.text!r}}}'.format(s=self)


class TemplateElementSizes(Object):
    ext = '.sizes'

    def __init__(self, template):
        self.template = template
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               self.template.hash.encode('utf-8'), b'sizes')

    def save_to(self, filename):
        data = run(['inkscape', '-S',self.template.filename])
        self._csv = data.decode('utf-8')
        with open(filename, 'wb') as f:
            f.write(data)

    @property
    def data(self):
        try:
            return self._data
        except AttributeError:
            self.save()
            try:
                csv_text = self._csv
            except AttributeError:
                with open(self.filename) as f:
                    csv_lines = list(f)
            else:
                csv_lines = csv_text.splitlines()
            data = {}
            for name, x, y, w, h in csv.reader(csv_lines):
                data[name] = {'x': x, 'y': y, 'w': w, 'h': h}
            self._data = data
            return self._data

    def get(self, id, size):
        value = float(self.data[id][size])
        if size in 'wh':
            value = math.ceil(value)
        return int(value)


class Video:
    is_big_file = True
    ext = '.video'
    pos = 0, 0

    def __add__(self, other):
        return ConcatenatedVideo(self, other)

    def resize_by_template(self, template, id):
        sizes = TemplateElementSizes(template)
        w = sizes.get(id, 'w')
        h = sizes.get(id, 'h')
        return ResizedVideo(self, w, h)


class InputVideo(Video, InputObject):
    pass


class ConcatenatedVideo(Video):
    def __init__(self, first, second):
        self.first = first
        self.second = second

    def __repr__(self):
        return '({s.first}+{s.second})'.format(s=self)


class ResizedVideo(Video):
    def __init__(self, parent, w, h):
        self.parent = parent
        self.w = w
        self.h = h

    def __repr__(self):
        return '{s.parent}{{->{s.w}x{s.h}}}'.format(s=self)
