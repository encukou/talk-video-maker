from concurrent.futures import ThreadPoolExecutor

import librosa
from dtw import dtw
import numpy
import scipy

from . import objects, templates
from .objects import hash_bytes, run

SAMPLE_RATE = 22050
DTW_WINDOW_START_SIZE = 2000
DTW_WINDOW_DELTA = 5
DTW_WINDOW_MIN_SIZE = 50
DTW_HOP_RATIO = 3/4
DTW_CUTOFF = 5000
STFT_HOP_LENGTH = 512

thread_executor = ThreadPoolExecutor(1)  # XXX: higher value


def correlated(video_a, video_b):
    stats = CorrelatedObject(video_a, video_b).stats
    print(stats)

class CorrelatedObject(objects.Object):
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
        slope, intercept, r, stderr = regress(paths)
        return slope, intercept, r, stderr


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
    dtw_size = DTW_WINDOW_START_SIZE
    while path1[-1] < len(f1) - 1 and path2[-1] < len(f2) - 1:
        start1, start2 = path1[-1], path2[-1]
        print('Correlating... {}/{} {}/{} (~{}%), {} vs {}, sz {}'.format(
            len(path1), len(f1), len(path2), len(f2),
            int(min(len(path1)/len(f1), len(path2)/len(f2))*100),
            start1, start2, dtw_size))
        path_chunk_length = int(dtw_size * DTW_HOP_RATIO)
        dist, cost, path = dtw(f1[start1:start1+dtw_size],
                            f2[start2:start2+dtw_size])
        path1.extend(path[0][:path_chunk_length] + start1)
        path2.extend(path[1][:path_chunk_length] + start2)
        if dtw_size > DTW_WINDOW_MIN_SIZE:
            dtw_size -= DTW_WINDOW_DELTA
        else:
            dtw_size = DTW_WINDOW_MIN_SIZE
    return numpy.array([path1, path2])


def regress(paths):
    slope, intercept, r, p, stderr = scipy.stats.linregress(
        paths[:,DTW_CUTOFF:-DTW_CUTOFF])
    frames = intercept * 1  # TODO
    def print_(*a, **ka):
        print(*a, **ka)
    print_('Screngrab is {}× faster'.format(slope))
    #print_('Screngrab is shifted by {} frames'.format(frames))
    print_('Correlation coefficient: {}'.format(r))
    print_('Standard error of estimate: {}'.format(stderr))
    return slope, intercept, r, stderr
