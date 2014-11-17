import os
import sys
import pathlib
import asyncio
import subprocess
import contextlib
from concurrent.futures import ThreadPoolExecutor

import yaml
import scipy.io.wavfile
import librosa
from dtw import dtw

SAMPLE_RATE = 22050
NUM_CORES = 4

subprocess_lock = asyncio.Lock()
_thread_executor = ThreadPoolExecutor(NUM_CORES)


def core_lock():
    stack = contextlib.ExitStack()
    stack.enter_context((yield from subprocess_lock))
    return contextlib.closing(stack)


@asyncio.coroutine
def run_in_thread(func):
    loop = asyncio.get_event_loop()
    #with (yield from core_lock()):
    result = yield from loop.run_in_executor(_thread_executor, func)
    return result


def get_config(directory):

    result = {
        'temp': {
            'videolist': str(directory / '_videolist'),
            'concat': str(directory / '_concat.mts'),
            'concat_audio': str(directory / '_concat.wav'),
            'screengrab_audio': str(directory / '_screengrab.wav'),
        },
        'sources': [],
    }
    for filepath in directory.iterdir():
        if filepath.name.startswith('_'):
            continue
        if filepath.suffix.lower() == '.mts':
            result['sources'].append(str(filepath))
        elif filepath.suffix.lower() == '.ogv':
            result['screengrab'] = str(filepath)
        elif filepath.suffix.lower() == '.yaml':
            with filepath.open('rt', encoding='utf-8') as f:
                result['info'] = yaml.safe_load(f)

    return result


def try_unlink(filename):
    try:
        os.unlink(filename)
    except OSError:
        pass


@asyncio.coroutine
def concatenated(config):
    result = config['temp']['concat']
    if os.path.exists(result):
        return result

    try:
        with open(config['temp']['videolist'], 'wt') as f:
            for filename in config['sources']:
                f.write('file ')
                f.write(filename)
                f.write('\n')
        argv = ['ffmpeg',
                '-f', 'concat',
                '-i', config['temp']['videolist'],
                '-c', 'copy',
                result,
        ]
        with (yield from subprocess_lock):
            print('Concatenating source video')
            process = yield from asyncio.create_subprocess_exec(
                *argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
            yield from process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd=argv)
        return result
    except:
        try_unlink(result)
        raise
    finally:
        try_unlink(config['temp']['videolist'])


@asyncio.coroutine
def extract_audio(source_path, result_path):
    result = result_path
    if os.path.exists(result):
        return

    argv = [
        'ffmpeg',
        '-i', source_path,
        '-acodec', 'pcm_s16le',
        '-ac', '1',
        '-ar', str(SAMPLE_RATE),
        result,
    ]
    try:
        with (yield from subprocess_lock):
            print('Extracting audio from %s' % source_path)
            process = yield from asyncio.create_subprocess_exec(
                *argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
            yield from process.communicate()
            return result
    except:
        try_unlink(result)
        raise

@asyncio.coroutine
def get_audio_data(source_path, temp_path):
    yield from extract_audio(source_path, temp_path)

    def job():
        result = librosa.load(temp_path, sr=SAMPLE_RATE)
        return result

    print('Getting audio data for %s' % source_path)
    result, _sample_rate = yield from run_in_thread(job)
    print('Got audio data for %s (%s samples = %ss)' % (
        source_path, len(result), len(result) / SAMPLE_RATE))
    return result


@asyncio.coroutine
def correlate(data1_coro, data2_coro):
    y1, y2 = yield from asyncio.gather(data1_coro, data2_coro)
    return len(y1), len(y2)


def main_coro():
    try:
        directory = pathlib.Path(sys.argv[1])
    except IndexError:
        directory = pathlib.Path('.')

    config = get_config(directory)

    print(yaml.safe_dump(config, default_flow_style=False))

    results = yield from asyncio.gather(
        correlate(
            get_audio_data(
                (yield from concatenated(config)),
                config['temp']['concat_audio']
            ),
            get_audio_data(
                config['screengrab'],
                config['temp']['screengrab_audio']
            ),
        )
    )
    print(results)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_coro())
