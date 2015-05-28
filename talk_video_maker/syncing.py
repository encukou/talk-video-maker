from concurrent.futures import ThreadPoolExecutor

import librosa
import numpy
import scipy

from . import objects, templates, videos
from .objects import hash_bytes, run
from .cdtw import dtw

SAMPLE_RATE = 22050
DTW_HOP_RATIO = 3/4
DTW_CUTOFF = 1/8
STFT_HOP_LENGTH = 512
DTW_WINDOW_LENGTH = 120  # seconds

DTW_WINDOW_SIZE = DTW_WINDOW_LENGTH * SAMPLE_RATE // STFT_HOP_LENGTH

thread_executor = ThreadPoolExecutor(1)  # XXX: higher value


def synchronized(video_a, video_b, mode='pad'):
    sync = SynchronizedObject(video_a, video_b)

    slope, intercept, r, stderr = sync.stats
    frames = intercept * 1
    frames_s = intercept * STFT_HOP_LENGTH / SAMPLE_RATE
    print('A is {}× faster than B'.format(slope))
    print('A is shifted by {} frames = {} s relative to B'.format(
        frames, frames_s))
    print('Speedup coefficient: {}'.format(r))
    print('Standard error of estimate: {}'.format(stderr))

    return sync.get_results(mode=mode)

class SynchronizedObject(objects.Object):
    ext = '.npy'

    def __init__(self, video_a, video_b):
        self.hash = hash_bytes(
            type(self).__name__.encode('utf-8'),
            video_a.hash.encode('utf-8'),
            video_b.hash.encode('utf-8'),
        )
        self.video_a = video_a
        self.video_b = video_b

    def save_to(self, filename):
        data = get_data(self.video_a, self.video_b)
        paths = get_wdwt_path(*data)
        with open(filename, 'wb') as f:
            numpy.save(f, paths)
        self._paths = paths

    @property
    def stats(self):
        self.save()
        try:
            paths = self._paths
        except AttributeError:
            with open(self.filename, 'rb') as f:
                paths = numpy.load(f)
        return regress(paths)

    def get_results(self, *, mode='pad'):
        if mode == 'pad':
            result_a = self._pad_video(self.video_a, 1)
            result_b = self._pad_video(self.video_b, -1)
        else:
            raise ValueError('bad mode')
        return result_a, result_b

    def _pad_video(self, video, side):
        slope, intercept, r, stderr = self.stats
        if intercept * side <= 0:
            return video
        else:
            delay = side * intercept * STFT_HOP_LENGTH / SAMPLE_RATE
            blank = videos.BlankVideo(delay,
                                      width=video.width,
                                      height=video.height)
            return blank + video.fade_in(0.5)


def get_data(video_a, video_b):
    opts = dict()

    def prepare_audio(video):
        return video.mono_audio().exported_audio('s16',
                                                 sample_rate=SAMPLE_RATE)

    def load_data(audio):
        signal, _sample_rate = librosa.load(audio.filename, sr=SAMPLE_RATE)
        mfcc = librosa.feature.mfcc(signal, SAMPLE_RATE, n_mfcc=10,
                                    hop_length=STFT_HOP_LENGTH)
        return signal, mfcc.T

    data_a, data_b = thread_executor.map(
        load_data, [prepare_audio(video_a), prepare_audio(video_b)])

    return data_a, data_b


def get_wdwt_path(data1, data2):
    y1, f1 = data1
    y2, f2 = data2
    path1 = [0]
    path2 = [0]
    path_chunk_length = int(DTW_WINDOW_SIZE * DTW_HOP_RATIO)
    while path1[-1] < len(f1) - 1 and path2[-1] < len(f2) - 1:
        start1, start2 = path1[-1], path2[-1]
        print('Correlating... {}/{} {}/{} (~{}%), {} vs {}, sz {}'.format(
            len(path1), len(f1), len(path2), len(f2),
            int(min(len(path1)/len(f1), len(path2)/len(f2))*100),
            start1, start2, DTW_WINDOW_SIZE))
        dist, cost, path = dtw(f1[start1:start1+DTW_WINDOW_SIZE],
                            f2[start2:start2+DTW_WINDOW_SIZE])
        path1.extend(path[0][:path_chunk_length] + start1)
        path2.extend(path[1][:path_chunk_length] + start2)
    return numpy.array([path1, path2])


def regress(paths):
    length = paths.shape[1]
    cutoff = int(length * DTW_CUTOFF)
    slope, intercept, r, p, stderr = scipy.stats.linregress(
        paths[:,cutoff:-cutoff])
    return slope, intercept, r, stderr
