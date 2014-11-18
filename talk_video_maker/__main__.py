import os
import sys
import pathlib
import asyncio
import subprocess
import contextlib
from concurrent.futures import ThreadPoolExecutor

import yaml
import numpy
import scipy.io.wavfile
import librosa
from dtw import dtw

SAMPLE_RATE = 22050
NUM_CORES = 4
DTW_SIZE = 200
DTW_MIN = 50
DTW_DUTY = 3/4
DTW_CUTOFF = 5000

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


@asyncio.coroutine
def immediate(data):
    return data


def get_config(directory):

    result = {
        'temp': {
            'videolist': str(directory / '_videolist'),
            'concat': str(directory / '_concat.mts'),
            'concat_audio': str(directory / '_concat.wav'),
            'screengrab_audio': str(directory / '_screengrab.wav'),
            'dtw_path': str(directory / '_dtw_path.npy'),
            'correlation_stats': str(directory / '_correlation_stats.npy'),
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
def get_audio_data(source_path_coro, temp_path):
    source_path = yield from source_path_coro
    yield from extract_audio(source_path, temp_path)

    def job():
        signal, _sample_rate = librosa.load(temp_path, sr=SAMPLE_RATE)
        mfcc = librosa.feature.mfcc(signal, SAMPLE_RATE, n_mfcc=10)
        return signal, mfcc.T

    print('Getting audio data for %s' % source_path)
    result = yield from run_in_thread(job)
    print('Got audio data for %s (%s samples = %ss)' % (
        source_path, len(result[0]), len(result[0]) / SAMPLE_RATE))
    return result


@asyncio.coroutine
def get_dwt(cache_name, data1_coro, data2_coro):
    try:
        f = open(cache_name, 'rb')
    except IOError:
        (y1, f1), (y2, f2) = yield from asyncio.gather(data1_coro, data2_coro)
        path1 = [0]
        path2 = [0]
        dtw_size = DTW_SIZE
        while path1[-1] < len(f1) - 1 and path2[-1] < len(f2) - 1:
            start1, start2 = path1[-1], path2[-1]
            if dtw_size > DTW_MIN:
                dtw_size -= 3
            print('Correlating...', len(path1), start1, start2)
            path_chunk_length = int(dtw_size * DTW_DUTY)
            dist, cost, path = dtw(f1[start1:start1+dtw_size],
                                f2[start2:start2+dtw_size])
            path1.extend(path[0][:path_chunk_length] + start1)
            path2.extend(path[1][:path_chunk_length] + start2)
        result = numpy.array([path1, path2])
        with open(cache_name, 'wb') as f:
            numpy.save(f, result)
        return result
    else:
        with f:
            return numpy.load(f)

@asyncio.coroutine
def regress(config):
    data = yield from get_dwt(
        config['temp']['dtw_path'],
        get_audio_data(
            concatenated(config),
            config['temp']['concat_audio']
        ),
        get_audio_data(
            immediate(config['screengrab']),
            config['temp']['screengrab_audio']
        ),
    )
    slope, intercept, r, p, stderr = scipy.stats.linregress(
        data[:,DTW_CUTOFF:-DTW_CUTOFF])
    frames = intercept * 1  # TODO
    stats_filename = config['temp']['correlation_stats']
    with open(stats_filename, 'wt', encoding='utf-8') as f:
        def print_(*a, **ka):
            print(*a, **ka)
            print(*a, file=f, **ka)
        print_('Screngrab is {}× faster'.format(slope))
        #print_('Screngrab is shifted by {} frames'.format(frames))
        print_('Correlation coefficient: {}'.format(r))
        print_('Standard error of estimate: {}'.format(stderr))
    return slope, intercept, r, stderr

def main_coro():
    try:
        directory = pathlib.Path(sys.argv[1])
    except IndexError:
        directory = pathlib.Path('.')

    config = get_config(directory)

    print(yaml.safe_dump(config, default_flow_style=False))

    results = yield from regress(config)
    print(results)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_coro())
