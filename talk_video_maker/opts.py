import argparse
import glob
import operator
import functools
import os

import yaml

from .templates import InputTemplate
from .videos import InputVideo


NOTHING = object()

def fileglob(pattern, default, base='.'):
    if pattern is None:
        pattern = default
    result = []
    for item in glob.glob(os.path.join(base, pattern)):
        if os.path.isdir(item):
            for subitem in glob.glob(os.path.join(base, item, default)):
                result.append(os.path.abspath(subitem))
        else:
            result.append(item)
    if not result:
        print('Base:', base)
        print('Pattern:', pattern)
        print('Default:', default)
        print('Warning: no files matching {}'.format(pattern))
    return sorted(result)


class Option:
    need_value = True

    def __init__(self, *, help=None, default=NOTHING):
        self.default = default
        self.help = help

    def add_arg(self, parser, name):
        arg_name = '--' + name.replace('_', '-')
        arg_params = dict(help=self.help, default=NOTHING)
        self.set_arg_params(arg_params)
        parser.add_argument(arg_name, **arg_params)

    def set_arg_params(self, params):
        if params['help'] and self.default is not NOTHING and self.default:
            params['help'] += ' [default: {}]'.format(self.default)


class TemplateOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'SVG_FILE')
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        if isinstance(value, str):
            value = InputTemplate(filename=value)
        return value


class VideoOption(Option):
    def set_arg_params(self, params):
        params['help'] += ' (globs accepted)'
        params.setdefault('metavar', 'FILE')
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        conf_path = all_opts.get('config') or './config.yaml'
        base = os.path.dirname(conf_path)
        if isinstance(value, str):
            filenames = fileglob(value, self.default, base)
            inputs = [InputVideo(filename=n) for n in filenames]
            value = functools.reduce(operator.add, inputs)
        return value


class TextOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'TEXT')
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        return str(value)


class FlagOption(Option):
    need_value = False

    def set_arg_params(self, params):
        params.setdefault('action', 'store_true')
        params['default'] = False
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        return bool(value)


class FloatOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'NUMBER')
        params['type'] = float
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        return float(value)


class DateOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'DATE')
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        if isinstance(value, str):
            value = datetime.date.strptime(value, '%Y-%m-%d')
        return value


def parse_options(signature, argv):
    parser = argparse.ArgumentParser(description='Create a video.',
                                     prog=argv[0])

    parser.add_argument('config', nargs='?', default=None,
                        help='Configuration file ' +
                             ' (YAML, provides defaults for other arguments)' +
                             ' (*.yaml if a directory is given)' +
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
        filenames = fileglob(namespace.config, '*.yaml')
        print('Config:', filenames)
        [filename] = filenames
        infile = open(filename)
    if infile:
        with infile:
            config = yaml.safe_load(infile)
    else:
        config = {}
    args = {'config': namespace.config}

    for param in signature.parameters.values():
        value = getattr(namespace, param.name)
        if value is NOTHING:
            value = config.get(param.name, param.annotation.default)
        if value is NOTHING and param.annotation.need_value:
            raise LookupError('Option {!r} not specified'.format(param.name))
        args[param.name] = value

    return args


def coerce_options(signature, options_in):
    options_out = {}
    for param in signature.parameters.values():
        value = param.annotation.coerce(options_in[param.name], options_in)
        options_out[param.name] = value
    return options_out
