import json
import collections
import itertools
import functools
import re

from . import objects, templates
from .objects import hash_bytes, run
from .draw_graph import draw_graph


# A AVObject has multiple Streams
# A Stream has a type: Video, Audio, Subtitle, Attachment, Data
# A video stream has a width, height, duration, frame rate
# An audio stream has sample rate, 

class AVObject(objects.Object):
    def __init__(self, streams, format='mp4', acodec='aac'):
        streams = tuple(streams)
        for stream in streams:
            assert stream.type
        self.streams = streams
        self.format = format
        self.ext = '.' + format
        self.acodec = acodec
        self.hash = hash_bytes(
            type(self).__name__.encode('utf-8'),
            acodec.encode('utf-8'),
            *(s.hash.encode('utf-8') for s in streams))

    def __add__(self, other):
        return ConcatenatedAV(self, other)

    def resized_by_template(self, template, id):
        sizes = templates.TemplateElementSizes(template)
        streams = self.streams
        streams = filter_streams(
            streams, {'video'}, 'scale', dict(
                w=sizes.get(id, 'w'),
                h=sizes.get(id, 'h'),
        ))
        streams = filter_streams(streams, {'video'}, 'setsar', dict(sar='1'))
        streams = filter_streams(streams, {'video'}, 'pad', dict(
            x=sizes.get(id, 'x'),
            y=sizes.get(id, 'y'),
            w=template.width,
            h=template.height,
        ))
        return AVObject(streams)

    def with_fps(self, fps):
        streams = self.streams
        streams = filter_streams(
            streams, {'video'}, 'fps', dict(
                fps=fps,
        ))
        return AVObject(streams)

    def mono_audio(self):
        streams = [s for s in self.streams if s.type == 'audio']
        streams = filter_amix(streams).outputs
        streams = filter_aformat(streams, channel_layouts=['mono']).outputs
        return AVObject(streams)

    def with_audio_rate(self, sample_rate):
        streams = self.streams
        streams = filter_streams(
            streams, {'audio'}, 'aformat', dict(
                sample_rates=sample_rate,
        ))
        return AVObject(streams)

    def exported_audio(self, format, sample_rate=None):
        args = {'sample_fmts': format}
        if sample_rate:
            args['sample_rates'] = sample_rate
        streams = self.streams
        streams = filter_streams(streams, {'audio'}, 'aformat', args)
        return AVObject(streams, acodec='pcm_s16le', format='wav')

    def save_to(self, filename):
        print('\n'.join(draw_graph(self.streams)))
        print(filename)
        specs = ' ; '.join(generate_filter_specifications(self.streams))
        print(specs)
        run(['ffmpeg',
             '-filter_complex', specs,
             '-f', self.format,
             '-c:v', 'libx264',
             '-c:a', self.acodec,
             '-crf', '30',
             '-maxrate', '5000k',
             '-strict', '-2',
             filename])
        return


class InputVideo(AVObject):
    def __init__(self, filename):
        streams = filter_movie(filename).outputs
        super().__init__(streams)


class ConcatenatedAV(AVObject):
    def __init__(self, *parts):
        flattened = []
        for part in parts:
            if isinstance(part, ConcatenatedAV):
                flattened.extend(part.parts)
            else:
                flattened.append(part)
        self.parts = parts = flattened

        has_audio = any(s.type == 'audio'
                        for p in parts
                        for s in p.streams)
        inputs = []
        for part in parts:
            [video] = [s for s in part.streams if s.type == 'video']
            if has_audio:
                audios = [s for s in part.streams if s.type == 'audio']
                if audios:
                    [audio] = audios
                else:
                    [audio] = generate_silence().outputs
                inputs.append([video, audio])
            else:
                inputs.append([video])
        streams = filter_concat(inputs).outputs
        super().__init__(streams)


class ImageVideo(AVObject):
    def __init__(self, image, time, fps):
        streams = filter_movie(image.filename, ['dv']).outputs
        super().__init__(streams)


class Stream:
    def __repr__(self):
        try:
            source = self.source
        except AttributeError:
            source = '<unset>'
        return '<{} from {}>'.format(type(self).__name__, source)

    @property
    def symbol(self):
        return self.type[0]

    @property
    def incomplete_hash(self):
        return hash_bytes(type(self).__name__.encode('utf-8'),
                          self.type.encode('utf-8'))

    @property
    def hash(self):
        return hash_bytes(self.incomplete_hash.encode('utf-8'),
                          self.source.hash.encode('utf-8'))


class VideoStream(Stream):
    type = 'video'


class AudioStream(Stream):
    type = 'audio'


def gen_names():
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    n = 1
    while True:
        for c in itertools.combinations_with_replacement(alphabet, n):
            yield ''.join(c)
        n += 1


def generate_filter_specifications(streams):
    names_iter = gen_names()
    get_name = lambda: next(names_iter)

    end = Filter('output', {}, streams, ())
    stream_names = {}

    def quote(s):
        d = {
            ':': r'\:',
            '\\': r'\\\\',
            "'": r"\\\'",
            "[": r"\[",
            "]'": r"\]",
            ",'": r"\,",
            ";'": r"\;",
        }
        pattern = re.compile('|'.join(re.escape(k) for k in d.keys()))
        return pattern.sub(lambda x: d[x.group()], s)

    split_names = {
        'video': 'split',
        'audio': 'asplit',
    }
    null_names = {
        'video': 'null',
        'audio': 'anull',
    }
    null_sink_names = {
        'video': 'nullsink',
        'audio': 'anullsink',
    }

    unprocessed = [end]
    seen_filters = set()
    processed = []
    while unprocessed:
        filter = unprocessed.pop()
        filterspec = filter.name
        if filter.arg_tuples:
            # XXX: Quoting
            filterspec += '=' + ':'.join(
                '{}={}'.format(n, quote(v)) for n, v in filter.arg_tuples)
        f = [], filterspec, [], filter
        for inp in filter.inputs:
            if inp in stream_names:
                # Split a stream
                old_name = stream_names[inp]
                new_name_1 = get_name()
                new_name_2 = get_name()
                processed.append(([new_name_1],
                                  split_names[inp.type],
                                  [old_name, new_name_2],
                                  None))
                stream_names[inp] = new_name_1
                stream_names[old_name] = old_name
                stream_names[new_name_2] = new_name_2
                used_name = new_name_2
            else:
                used_name = stream_names[inp] = get_name()
            f[0].append(used_name)
            if inp.source not in seen_filters:
                unprocessed.append(inp.source)
                seen_filters.add(inp.source)
        for outp in filter.outputs:
            f[2].append(outp)
        processed.append(f)
    for filter in seen_filters:
        for outp in filter.outputs:
            if outp not in stream_names:
                name = stream_names[outp] = get_name()
                processed.append((
                    [name],
                    null_sink_names[outp.type],
                    [],
                    None))
    for inputs, filterspec, outputs, filter in reversed(processed):
        if filter is end:
            yield ';'.join('[{}] {}'.format(n, null_names[s.type]) for n, s in zip(
                inputs, end.inputs))
        else:
            yield '{} {} {}'.format(
                ''.join('[{}]'.format(p) for p in inputs),
                filterspec,
                ''.join('[{}]'.format(stream_names[p]) for p in outputs),
            )


class Filter(collections.namedtuple('Filter', 'name arg_tuples inputs outputs hash')):
    def __new__(cls, name, args, inputs, outputs):
        hash_components = [cls.__name__.encode('utf-8'), name.encode('utf-8')]
        arg_tuples = tuple(sorted((str(k), str(v)) for k, v in args.items()))
        for k, v in arg_tuples:
            hash_components.extend([k.encode('utf-8'), v.encode('utf-8')])
        hash_components.append(b'\0')
        for inp in inputs:
            hash_components.append(inp.hash.encode('utf-8'))
        for outp in outputs:
            hash_components.append(outp.incomplete_hash.encode('utf-8'))
        filter = super().__new__(
            cls, name, arg_tuples,
            tuple(inputs), tuple(outputs),
            hash_bytes(*hash_components))
        for input in inputs:
            assert input.type
        for output in outputs:
            assert output.type
            output.source = filter
        return filter

    def __str__(self):
        return "{}({})".format(self.name, ', '.join('{}={}'.format(k, v) for k, v in self.arg_tuples))


def filter_streams(streams, types, name, args):
    for stream in streams:
        if stream.type in types:
            filter = Filter(name, args, [stream], [type(stream)()])
            [stream] = filter.outputs
            yield stream
        else:
            yield stream


def filter_movie(filename, stream_specs=('dv', 'da')):
    outputs = []
    for stream_spec in stream_specs:
        if stream_spec == 'dv':
            outputs.append(VideoStream())
        elif stream_spec == 'da':
            outputs.append(AudioStream())
        else:
            raise ValueError(
                'stream specification {!r} not implemented'.format(stream_spec))
    return Filter(
        name='movie',
        args={'filename': filename, 'streams': '+'.join(stream_specs)},
        inputs=(),
        outputs=tuple(outputs),
    )


def filter_concat(groups):
    outputs = []
    in_audio = False
    num_video = 0
    num_audio = 0
    length = len(groups[0])
    if any(len(g) != length for g in groups):
        raise ValueError('Uneven stream group length')
    for group in zip(*groups):
        tp = group[0].type
        if any(s.type != tp for s in group):
            raise ValueError('Incompatible stream types: {}'.format(
                [s.type for s in group]))
        if tp == 'video':
            outputs.append(VideoStream())
            if in_audio:
                raise ValueError('Video streams must come before audio streams')
            num_video += 1
        elif tp == 'audio':
            outputs.append(AudioStream())
            num_audio += 1
            in_audio = True
        else:
            raise ValueError('Unknown stream type for concat: {}'.format(tp))
    return Filter(
        name='concat',
        args={'n': len(groups), 'v': num_video, 'a': num_audio},
        inputs=tuple(s for g in groups for s in g),
        outputs=tuple(outputs),
    )


def filter_amix(audios):
    if not all(s.type == 'audio' for s in audios):
        raise ValueError('Attempting to amix non-audio streams')
    return Filter(
        name='amix',
        args={'inputs': len(audios)},
        inputs=audios,
        outputs=[AudioStream()])


def filter_aformat(audios, channel_layouts=None):
    if not all(s.type == 'audio' for s in audios):
        raise ValueError('Attempting to aformat non-audio streams')
    args = {}
    if channel_layouts:
        args['channel_layouts'] = '|'.join(channel_layouts)
    return Filter(
        name='aformat',
        args=args,
        inputs=audios,
        outputs=[AudioStream()])


@functools.lru_cache()
def generate_silence():
    return Filter(
        name='aevalsrc',
        args={'exprs': 0},
        inputs=(),
        outputs=[AudioStream()],
    )
