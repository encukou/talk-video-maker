from concurrent.futures import ThreadPoolExecutor

import librosa
import dtw

SAMPLE_RATE = 22050

thread_executor = ThreadPoolExecutor(1)  # XXX: higher value


def correlated(video_a, video_b):
    opts = dict()

    def prepare_audio(video):
        return video.mono_audio().exported_audio('s16',
                                                 sample_rate=SAMPLE_RATE)

    def load_data(audio):
        data, _sample_rate = librosa.load(audio.filename, sr=SAMPLE_RATE)
        return data

    data_a, data_b = thread_executor.map(
        load_data, [prepare_audio(video_a), prepare_audio(video_b)])

    dist, cost, path = dtw.dtw(data_a, data_b)

    return data_a, data_b
