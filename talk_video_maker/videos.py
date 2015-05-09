from . import objects, templates
from .objects import hash_bytes


class Video(objects.Object):
    is_big_file = True
    ext = '.video'

    def __add__(self, other):
        return ConcatenatedVideo(self, other)

    def resize_by_template(self, template, id):
        sizes = templates.TemplateElementSizes(template)
        w = sizes.get(id, 'w')
        h = sizes.get(id, 'h')
        resized = ResizedVideo(self, w, h)
        x = sizes.get(id, 'x')
        y = sizes.get(id, 'y')
        return BoxedVideo(self, x, y, template.width, template.height)

    def fade_in(self, t):
        return FadedVideo(self, fade_in=t)

    def fade_out(self, t):
        return FadedVideo(self, fade_out=t)

    def set_fps(self, fps):
        return FPSVideo(self, fps)

    def mono_audio(self):
        return MonoAudio(self)

    def export(self, *, format=None, sample_rate=None):
        return ConvertedAudio(self, format=format, sample_rate=sample_rate)

    def save_to(self, filename):
        print(filename)
        raise NotImplementedError()


class InputVideo(Video, objects.InputObject):
    pass


class ConcatenatedVideo(Video):
    def __init__(self, first, second):
        self.first = first
        self.second = second
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               first.hash.encode('utf-8'),
                               second.hash.encode('utf-8'))

    def __repr__(self):
        return '({s.first}+{s.second})'.format(s=self)


class FadedVideo(Video):
    def __init__(self, parent, *, fade_in=0, fade_out=0):
        self.parent = parent
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               parent.hash.encode('utf-8'),
                               str(fade_in).encode('utf-8'),
                               str(fade_out).encode('utf-8'))


class FPSVideo(Video):
    def __init__(self, parent, fps):
        self.parent = parent
        self.fps = fps
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               parent.hash.encode('utf-8'),
                               str(fps).encode('utf-8'))


class ResizedVideo(Video):
    def __init__(self, parent, w, h):
        self.parent = parent
        self.w = w
        self.h = h
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               parent.hash.encode('utf-8'),
                               str(w).encode('utf-8'),
                               str(h).encode('utf-8'))

    def __repr__(self):
        return '{s.parent}{{->{s.w}x{s.h}}}'.format(s=self)


class BoxedVideo(Video):
    def __init__(self, parent, x, y, w, h):
        self.parent = parent
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               parent.hash.encode('utf-8'),
                               str(x).encode('utf-8'),
                               str(y).encode('utf-8'),
                               str(w).encode('utf-8'),
                               str(h).encode('utf-8'))


class ImageVideo(Video):
    def __init__(self, image, time, fps):
        self.image = image
        self.time = time
        self.fps = fps
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               image.hash.encode('utf-8'),
                               str(time).encode('utf-8'),
                               str(fps).encode('utf-8'))


class MonoAudio(Video):
    def __init__(self, parent):
        self.parent = parent
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               parent.hash.encode('utf-8'))


class ConvertedAudio(Video):
    def __init__(self, parent, format=None, sample_rate=None):
        self.parent = parent
        self.format = format
        self.sample_rate = sample_rate
        self.hash = hash_bytes(type(self).__name__.encode('utf-8'),
                               parent.hash.encode('utf-8'),
                               str(format).encode('utf-8'),
                               str(sample_rate).encode('utf-8'))
