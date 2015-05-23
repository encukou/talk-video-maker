import pprint

from talk_video_maker import mainfunc, opts, correlated

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
    export_template = export_template.without('vid-screen')
    export_template = export_template.without('vid-speaker')
    export_template = export_template.without('qr-code')

    template = template.with_text('txt-speaker', speaker + ':')
    template = template.with_text('txt-title', title)
    template = template.with_text('txt-event', event)
    template = template.with_text('txt-date', date.strftime('%Y-%m-%d'))
    template = template.with_text('txt-url', url)

    screen_vid = screen_vid.resized_by_template(template, 'vid-screen')
    screen_vid = screen_vid.with_fps(FPS)

    speaker_vid = speaker_vid.resized_by_template(template, 'vid-speaker')
    speaker_vid = speaker_vid.with_fps(FPS)

    sponsors = export_template.exported_slide('slide-sponsors', 6, fps=FPS)
    sponsors = sponsors.resized_by_template(template, 'vid-screen')

    last = export_template.exported_slide('slide-last', 6, fps=FPS)
    last = last.resized_by_template(template, 'vid-screen')

    #screen_vid = screen_vid + sponsors + last

    screen_vid, speaker_vid = correlated(screen_vid, speaker_vid)
    screen_vid = screen_vid.muted()

    page = export_template.exported_page(screen_vid.length)

    result = page | screen_vid | speaker_vid

    return result
