import argparse
import glob
import operator
import functools
import os

import yaml

from .templates import InputTemplate
from .videos import InputVideo


NOTHING = object()

def fileglob(pattern, default):
    result = []
    for item in glob.glob(pattern):
        if os.path.isdir(item):
            print(item, default)
            for subitem in glob.glob(os.path.join(item, default)):
                result.append(subitem)
        else:
            result.append(item)
    if not result:
        raise LookupError('no files matching {}'.format(pattern))
    return sorted(result)


class Option:
    def __init__(self, *, help=None, default=NOTHING):
        self.default = default
        self.help = help

    def add_arg(self, parser, name):
        arg_name = '--' + name.replace('_', '-')
        arg_params = dict(help=self.help, default=NOTHING)
        self.set_arg_params(arg_params)
        parser.add_argument(arg_name, **arg_params)

    def set_arg_params(self, params):
        if params['help'] and self.default is not NOTHING:
            params['help'] += ' [default: {}]'.format(self.default)


class TemplateOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'SVG_FILE')
        super().set_arg_params(params)

    def coerce(self, value):
        if isinstance(value, str):
            value = InputTemplate(filename=value)
        return value


class VideoOption(Option):
    def set_arg_params(self, params):
        params['help'] += ' (globs accepted)'
        params.setdefault('metavar', 'FILE')
        super().set_arg_params(params)

    def coerce(self, value):
        if isinstance(value, str):
            filenames = fileglob(value, self.default)
            inputs = [InputVideo(filename=n) for n in filenames]
            value = functools.reduce(operator.add, inputs)
        return value


class TextOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'TEXT')
        super().set_arg_params(params)

    def coerce(self, value):
        return str(value)


class DateOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'DATE')
        super().set_arg_params(params)

    def coerce(self, value):
        if isinstance(value, str):
            value = datetime.date.strptime(value, '%Y-%m-%d')
        return value


def parse_options(signature, argv):
    parser = argparse.ArgumentParser(description='Create a video.',
                                     prog=argv[0])

    parser.add_argument('--config', '-c', nargs='?', default=None,
                        help='Configuration file ' +
                             ' (YAML, provides defaults for other arguments)' +
                             ' [default: config.yaml (if exists)]')

    for param in signature.parameters.values():
        param.annotation.add_arg(parser, param.name)

    namespace = parser.parse_args(argv[1:])
    if namespace.config is None:
        try:
            infile = open('config.yaml')
        except OSError:
            infile = None
    else:
        infile = open(namespace.config)
    if infile:
        with infile:
            config = yaml.safe_load(infile)
    else:
        config = {}
    args = {}

    for param in signature.parameters.values():
        value = getattr(namespace, param.name)
        if value is NOTHING:
            value = config.get(param.name, param.annotation.default)
        if value is NOTHING:
            raise LookupError('Option {!r} not specified'.format(param.name))
        args[param.name] = value

    return args


def coerce_options(signature, options_in):
    options_out = {}
    for param in signature.parameters.values():
        value = param.annotation.coerce(options_in[param.name])
        options_out[param.name] = value
    return options_out
