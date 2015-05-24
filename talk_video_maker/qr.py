import io
import lxml.etree

import qrcode
from qrcode.image.svg import SvgPathImage

from . import templates
from .objects import hash_bytes, run

class TextQR(templates.Template):
    def __init__(self, text):
        self.text = text
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               text.encode('utf-8'))

    @property
    def dom(self):
        qr = qrcode.QRCode(box_size=10,
                           image_factory=SvgPathImage)
        qr.add_data(self.text)
        qr.print_ascii()
        img = qr.make_image()
        with io.BytesIO() as f:
            img.save(f)
            return lxml.etree.XML(f.getvalue())
