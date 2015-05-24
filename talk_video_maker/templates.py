import csv
import math

import lxml.etree

from . import objects
from .objects import hash_bytes, run

class Template(objects.Object):
    is_big_file = False
    ext = '.svg'

    def with_text(self, id, text):
        return RetextedTemplate(self, id, text)

    def with_image(self, id, image):
        return ImageReplacedTemplate(self, id, image)

    def without(self, id):
        return ReducedTemplate(self, id)

    def resized(self, width, height):
        return ResizedTemplate(self, width, height)

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

    def exported_slide(self, id=None, *, duration):
        from . import videos
        pic = self.exported_picture(id)
        return videos.make_image_video(pic, duration)

    def exported_page(self):
        return self.exported_picture()

    def exported_picture(self, id=None, width=None, height=None):
        def write_image(filename):
            args = ['inkscape',
                    self.filename,
                    '--export-png', filename,
                    '--export-background-opacity', '0']
            if id is not None:
                args.extend(['--export-area-snap',
                             '--export-id', id])
            else:
                args.extend(['--export-area-page'])
            if width is not None:
                args.extend(['--export-width', str(width)])
            if height is not None:
                args.extend(['--export-height', str(height)])
            run(args)
        pic_hash = hash_bytes(self.hash.encode('utf-8'),
                              id.encode('utf-8') if id else b'',
                              str(width).encode('utf-8'),
                              str(height).encode('utf-8'))
        return GeneratedImage(pic_hash.encode('utf-8'), write_image)

    @property
    def width(self):
        return int(self.dom.attrib['width'])

    @property
    def height(self):
        return int(self.dom.attrib['height'])

    @property
    def element_sizes(self):
        return TemplateElementSizes(self)


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


class ImageReplacedTemplate(ModifiedTemplate):
    def __init__(self, parent, id, image):
        self.parent = parent
        self.id = id
        self.image = image
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               self.parent.hash.encode('utf-8'),
                               id.encode('utf-8'),
                               image.hash.encode('utf-8'))

    def _dom_copy(self):
        dom = self.parent._dom_copy()
        xpath = './/*[@id="{}"]'.format(self.id)
        for elem in dom.xpath(xpath):
            width = elem.attrib['width']
            height = elem.attrib['height']
            x = elem.attrib['x']
            y = elem.attrib['y']
            elem.tag = 'image'
            elem.attrib.clear()
            elem.attrib.update({
                '{http://www.w3.org/1999/xlink}href': self.image.filename,
                'width': str(width),
                'height': str(height),
                'x': str(x),
                'y': str(y),
                'preserveAspectRatio': 'none',
            })
        return dom

    def __repr__(self):
        return '{s.parent}{{-{s.id}}}'.format(s=self)


class ResizedTemplate(ModifiedTemplate):
    def __init__(self, parent, width, height):
        self.parent = parent
        self.new_width = width
        self.new_height = height
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               self.parent.hash.encode('utf-8'),
                               str(width).encode('utf-8'),
                               str(height).encode('utf-8'))

    def _dom_copy(self):
        dom = self.parent._dom_copy()
        dom.attrib['width'] = str(self.new_width)
        dom.attrib['height'] = str(self.new_height)
        return dom


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

    def __getitem__(self, id):
        return {k: self.get(id, k) for k in self.data[id]}

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
