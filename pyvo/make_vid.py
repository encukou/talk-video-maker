import pprint

from talk_video_maker import mainfunc, opts, correlate

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
    export_template = template
    export_template = export_template.remove('vid-screen')
    export_template = export_template.remove('vid-speaker')

    template = template.set_text('txt-speaker', speaker + ':')
    template = template.set_text('txt-title', title)
    template = template.set_text('txt-event', event)
    template = template.set_text('txt-date', date.strftime('%Y-%m-%d'))
    template = template.set_text('txt-url', url)

    screen_vid = screen_vid.resize_by_template(template, 'vid-screen')
    screen_vid = screen_vid.set_fps(FPS)

    speaker_vid = speaker_vid.resize_by_template(template, 'vid-speaker')
    speaker_vid = speaker_vid.set_fps(FPS)

    sponsors = export_template.export_slide('slide-sponsors', 6, fps=FPS)
    sponsors = sponsors.resize_by_template(template, 'vid-screen')

    last = export_template.export_slide('slide-last', 6, fps=FPS)
    last = last.resize_by_template(template, 'vid-screen')

    screen_vid = screen_vid + sponsors + last

    screen_vid, speaker_vid = correlate(screen_vid, speaker_vid)

    page = export_template.export_page(screen_vid.length)

    result = page | screen_vid | speaker_vid
    result = result.set_audio(main)

    return result