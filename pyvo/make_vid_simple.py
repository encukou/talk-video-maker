import os.path

from talk_video_maker import mainfunc, opts, qr
from talk_video_maker.syncing import offset_video, get_audio_offset

FPS = 25

DEFAULT_TEMPLATE = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                'pyvo-640x480.svg')

@mainfunc(__name__)
def make_pyvo(
        template: opts.TemplateOption(
            default=DEFAULT_TEMPLATE, help='Main template'),
        speaker_vid: opts.VideoOption(
            default='*.MTS',
            help='Video file with recording of the speaker'),
        speaker: opts.TextOption(help='Name of the speaker'),
        title: opts.TextOption(help='Name of the talk'),
        url: opts.TextOption(help='URL of the talk'),
        event: opts.TextOption(help='Name of the event'),
        date: opts.DateOption(help='Date of the event'),
        preview: opts.FlagOption(
            help='Only process a small preview of the video'),
        av_offset: opts.FloatOption(
            default=0,
            help='Audio/Video offset correction for the speaker video'),
        ):
    if speaker:
        speaker += ':'
    template = template.with_text('txt-speaker', speaker)
    template = template.with_text('txt-title', title)
    template = template.with_text('txt-event', event)
    template = template.with_text('txt-date', date.strftime('%Y-%m-%d'))
    template = template.with_text('txt-url', url)

    template = template.without('qrcode')
    template = template.without('slide-overlay')

    last = template.exported_slide('slide-last', duration=7)

    qr_sizes = template.element_sizes['qrcode']
    last_sizes = template.element_sizes['slide-last']
    qrcode = qr.TextQR(url).resized(qr_sizes['w'], qr_sizes['h'])
    qrcode = qrcode.exported_slide(duration=last.duration)
    qrcode = qrcode.resized_by_template(template, 'qrcode', 'slide-last')

    last = last | qrcode
    last = last.faded_in(0.5)

    if preview:
        speaker_vid = speaker_vid.trimmed(end=20)

    logo = template.exported_slide(None, duration=speaker_vid.duration)

    overlay = template.exported_slide('slide-overlay', duration=7)
    overlay = overlay.faded_out(0.5)

    main = (speaker_vid | logo | overlay).faded_out(0.5)

    result = main + last
    blank = template.exported_slide('slide-blank', duration=result.duration)
    result = blank | result

    return result
