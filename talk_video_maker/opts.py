import argparse
import glob
import operator
import functools
import os

import yaml

from .templates import InputTemplate
from .videos import InputVideo

class Nothing:
    def __bool__(self):
        return False

NOTHING = Nothing()

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
        params.setdefault('metavar', 'FILE')
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        conf_path = all_opts.get('config') or './config.yaml'
        base = os.path.dirname(conf_path)
        if isinstance(value, str):
            filenames = fileglob(value, self.default, base)
            inputs = [InputVideo(filename=n) for n in filenames]
            if not inputs:
                return None
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
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        return bool(value)


class FloatOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'NUMBER')
        params['type'] = float
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        if value is not None:
            return float(value)


class DateOption(Option):
    def set_arg_params(self, params):
        params.setdefault('metavar', 'DATE')
        super().set_arg_params(params)

    def coerce(self, value, all_opts):
        if isinstance(value, str):
            value = datetime.date.strptime(value, '%Y-%m-%d')
        return value


help_description = """
Create a video.

All options can also be specified in the configuration file, in YAML format.
For example,

    speaker: A. Knowitall
    title: On the Meaning of Life
    event: The Summit of Importance
    date: 2058-04-26
    url: http://summit.site.example/2058/talk527
    speaker_vid: "*.AVI"

Whenever filenamess are specified, they are taken relative to the config file's
directory (or $PWD, in the case of the config file). There are two shortcuts:
* glob: "*.MTS" means all files ending in ".MTS".
* directories: "/somedir/" means: apply the default glob pattern for the given
  option to that directory.

"""


def parse_options(signature, argv):
    parser = argparse.ArgumentParser(description=help_description,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog=argv[0])

    parser.add_argument('config', nargs='?', default=None,
                        help='Configuration file ' +
                             ' (YAML, provides defaults for other arguments)' +
                             ' [default: *.yaml]',
                        )

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
