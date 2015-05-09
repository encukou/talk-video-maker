import csv
import math

import lxml.etree

from . import objects
from .objects import hash_bytes, run

class Template(objects.Object):
    is_big_file = False
    ext = '.svg'

    def set_text(self, id, text):
        return RetextedTemplate(self, id, text)

    def remove(self, id):
        return ReducedTemplate(self, id)

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

    def export_slide(self, id, time, *, fps):
        from . import videos
        pic = self.export_picture(id)
        return videos.ImageVideo(pic, time, fps=fps)

    def export_picture(self, id):
        def write_image(filename):
            run(['inkscape',
                 '--export-png', filename,
                 '--export-id', id,
                 '--export-area-drawing',
                 self.filename])
        pic_hash = hash_bytes(self.hash.encode('utf-8'),
                              id.encode('utf-8'))
        return GeneratedImage(pic_hash.encode('utf-8'), write_image)

    @property
    def width(self):
        return int(self.dom.attrib['width'])

    @property
    def height(self):
        return int(self.dom.attrib['height'])


class InputTemplate(Template, objects.InputObject):
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
        for elem in dom.xpath(xpath):
            elem.find('..').remove(elem)
        return dom

    def __repr__(self):
        return '{s.parent}{{-{s.id}}}'.format(s=self)


class TemplateElementSizes(objects.Object):
    ext = '.sizes'

    def __init__(self, template):
        self.template = template
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               self.template.hash.encode('utf-8'),
                               b'sizes')

    def save_to(self, filename):
        data = run(['inkscape', '--query-all', self.template.filename])
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


class GeneratedImage(objects.Object):
    ext = '.png'

    def __init__(self, hash_part, write_func):
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               hash_part)
        self.write_func = write_func
        self.save()

    def save_to(self, filename):
        self.write_func(filename)
