from concurrent.futures import ThreadPoolExecutor

import librosa

SAMPLE_RATE = 22050

thread_executor = ThreadPoolExecutor(1)  # XXX: higher value


def correlated(video_a, video_b):
    opts = dict()

    def load_data(video):
        audio = video.mono_audio().exported(format='pcm_s16le',
                                            sample_rate=SAMPLE_RATE)

        data = librosa.load(audio.filename, sr=SAMPLE_RATE)

    data_a, data_b = thread_executor.map(
        load_data, [video_a, video_b])

    return data_a, data_b
