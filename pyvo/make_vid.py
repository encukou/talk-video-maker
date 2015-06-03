import pprint

from talk_video_maker import mainfunc, opts, qr
from talk_video_maker.syncing import synchronized

FPS = 25

@mainfunc(__name__)
def make_pyvo(
        template: opts.TemplateOption(
            default='../pyvo.svg', help='Main template'),
        screen_vid: opts.VideoOption(
            default='*.ogv',
            help='Video file with the screen grab'),
        speaker_vid: opts.VideoOption(
            default='*.MTS',
            help='Video file with recording of the speaker'),
        speaker: opts.TextOption(help='Name of the speaker'),
        title: opts.TextOption(help='Name of the talk'),
        url: opts.TextOption(help='URL of the talk'),
        event: opts.TextOption(help='Name of the event'),
        date: opts.DateOption(help='Date of the event'),
        ):
    template = template.with_text('txt-speaker', speaker + ':')
    template = template.with_text('txt-title', title)
    template = template.with_text('txt-event', event)
    template = template.with_text('txt-date', date.strftime('%Y-%m-%d'))
    template = template.with_text('txt-url', url)

    export_template = template
    export_template = export_template.without('vid-screen')
    export_template = export_template.without('vid-speaker')
    export_template = export_template.without('qrcode')

    screen_vid = screen_vid.resized_by_template(template, 'vid-screen')
    screen_vid = screen_vid.with_fps(FPS)

    speaker_vid = speaker_vid.resized_by_template(template, 'vid-speaker')
    speaker_vid = speaker_vid.with_fps(FPS)

    # Uncomment to manually sync audio:
    #speaker_vid = speaker_vid.with_video_offset(0.5)

    # Uncomment to get a 30-second preview:
    #speaker_vid = speaker_vid.trimmed(end=30)

    sponsors = export_template.exported_slide('slide-sponsors', duration=6)
    sponsors = sponsors.faded_in(0.5)
    sponsors = sponsors.faded_out(0.5)

    last = export_template.exported_slide('slide-last', duration=7)

    qr_sizes = template.element_sizes['qrcode']
    last_sizes = template.element_sizes['slide-last']
    qrcode = qr.TextQR(url).resized(qr_sizes['w'], qr_sizes['h'])
    qrcode = qrcode.exported_slide(duration=last.duration)
    qrcode = qrcode.resized_by_template(template, 'qrcode', 'slide-last')

    last = last | qrcode
    last = last.faded_in(0.5)

    screen_vid, speaker_vid = synchronized(screen_vid, speaker_vid, mode='b')
    screen_vid = screen_vid.muted()

    duration = max(screen_vid.duration, speaker_vid.duration)

    page = export_template.exported_slide(duration=duration)

    main = page | screen_vid | speaker_vid
    main = main.faded_out(0.5)
    main = main + sponsors + last

    blank = export_template.exported_slide('slide-blank', duration=main.duration)
    result = blank | main

    print(result.graph)
    exit(result.filename)

    return result
