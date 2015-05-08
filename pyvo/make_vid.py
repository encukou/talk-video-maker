from talk_video_creator import run, opts, correlate

@run(__name__)
def make_pyvo(
        template: opts.Svg(default='../pyvo.svg'),
        screen_vid: opts.Video(default='*.ogv'),
        speaker_vid: opts.Video(default='*.MTS'),
        speaker = opts.Text()
        title = opts.Text()
        event = opts.Text()
        date = opts.Date()
        ):
    template = template.set_text('txt-speaker', speaker + ':')
    template = template.set_text('txt-title', title)
    template = template.set_text('txt-event', event)
    template = template.set_text('txt-date', date.strftime('%Y-%m-%d'))
    template = template.set_text('txt-url', url)

    screen_vid = screen_vid.resize_by_template(template, 'vid-screen')
    template = template.disable_export('vid-screen')

    speaker_vid = speaker_vid.resize_by_template(template, 'vid-speaker')
    template = template.disable_export('vid-speaker')

    speaker_vid = speaker_vid.fade_in(1)
    speaker_vid = speaker_vid.fade_out(1)

    screen_vid, speaker_vid = correlate(screen, speaker_vid)

    max_length = max(screen_vid.length, speaker_vid.length)

    sponsors = template.export_slide('slide-sponsors', 6)
    sponsors = sponsors.resize_by_template(template, 'vid-screen')

    last = template.export_slide('slide-last', 6)
    last = last.resize_by_template(template, 'vid-screen')

    main = screen_vid + sponsors + last

    page = template.export_page(main.length)

    return page | main | speaker_vid
