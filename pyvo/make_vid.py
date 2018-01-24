#!/usr/bin/env python3

import os.path
import unicodedata
import re

from talk_video_maker import mainfunc, opts, qr
from talk_video_maker.syncing import offset_video, get_audio_offset

FPS = 25

DEFAULT_TEMPLATE = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                'pyvo.svg')


def apply_logo(template, logo_name, duration, logo_elem, page_elem=None):
    sizes = template.element_sizes[logo_elem]
    logo_overlay = template.exported_slide(
        'logo-' + logo_name, duration=duration,
        width=sizes['w'], height=sizes['h'])
    logo_overlay = logo_overlay.resized_by_template(
        template, logo_elem, page_elem)
    return logo_overlay


def make_info_overlay(template, duration, logo=None):
    info_overlay = template.exported_slide('vid-only', duration=min(duration, 10))
    if logo:
        info_overlay |= apply_logo(template, logo, info_overlay.duration, 'logo2', 'vid-only')
    return info_overlay.faded_out(1)


def slugify(text):
    slug = unicodedata.normalize('NFKD', text)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^-a-zA-Z0-9]+', '_', slug).strip('_')
    slug = re.sub(r'[_]+', '_', slug)
    return slug


@mainfunc(__name__)
def make_pyvo(
        template: opts.TemplateOption(
            default=DEFAULT_TEMPLATE, help='Main template'),
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
        trim: opts.TextOption(
            default='b',
            help='Video trimming mode '
                 '(a=whole screencast, b=whole speaker video, '
                 'pad=include both videos, intersect=include only common part)'),
        preview: opts.FlagOption(
            help='Only process a small preview of the video'),
        av_offset: opts.FloatOption(
            default=0,
            help='Audio/Video offset correction for the speaker video'),
        screen_offset: opts.FloatOption(
            default=None,
            help='Manual time offset of the screencast'),
        speaker_only: opts.FlagOption(
            help='Only use the speaker video'),
        logo: opts.TextOption(
            default='',
            help='Pyvo logo variant (can be "tuplak", "ruby")'),
        praha: opts.FlagOption(
            help='Skip sponsors slide & include Pyvec overlay'),
        widescreen: opts.FlagOption(
            help='Make the screencast span the whole screen, not just a 4:3 area'),
        has_pillarbox: opts.FlagOption(
            help='The screencast is pure 4:3 but recorded as 16:9'),
        screen_on_top: opts.FlagOption(
            default=True,
            help='Put screencast on top of speaker video'),
        no_end: opts.FlagOption(
            help='Do not include the end slides'),
        outpath: opts.PathOption(
            default='.',
            help='Path where to put the output file'),
        ):
    for n in '', '2', '3':
        template = template.with_text('txt-speaker' + n, speaker + ':' if speaker else '')
        template = template.with_text('txt-title' + n, title)
        template = template.with_text('txt-event' + n, event)
        template = template.with_text('txt-date' + n, date.strftime('%Y-%m-%d'))
    template = template.with_text('txt-url', url)

    if not screen_vid and not speaker_only:
        raise ValueError('No screen video')
    if not speaker_vid:
        raise ValueError('No speaker video')

    if praha:
        # no overlay for PiP videos yet
        assert speaker_only

    export_template = template
    export_template = export_template.without('vid-screen')
    export_template = export_template.without('vid-speaker')
    export_template = export_template.without('vid-wscreen')
    export_template = export_template.without('vid-wspeaker')
    export_template = export_template.without('qrcode')
    export_template = export_template.without('vid-only')
    export_template = export_template.without('slide-overlay')

    if logo:
        export_template = export_template.without('logo')
        export_template = export_template.without('logo2')
        export_template = export_template.without('logo3')

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

    if av_offset:
        speaker_vid = speaker_vid.with_video_offset(av_offset)

    if speaker_only:
        speaker_vid = speaker_vid.resized_by_template(template, 'vid-only', 'vid-only')
        speaker_vid = speaker_vid.with_fps(FPS)

        if preview:
            speaker_vid = speaker_vid.trimmed(end=30)

        duration = speaker_vid.duration

        # Don't know why but without the following, FFMPEG fails with a
        # cryptic error: more samples than frame size
        speaker_vid = speaker_vid.with_audio_offset(0.0001)

        main = speaker_vid | make_info_overlay(export_template, duration, logo)
    else:
        speaker_vid = speaker_vid.with_fps(FPS)
        screen_vid = screen_vid.with_fps(FPS)
        if screen_offset is None:
            if not any(s.type == 'audio' for s in screen_vid.streams):
                raise ValueError('screencast has no audio, specify screen_offset manually')
            screen_offset = get_audio_offset(screen_vid, speaker_vid, max_stderr=5e-4)

        if has_pillarbox:
            assert not widescreen
            screen_vid = screen_vid.cropped(screen_vid.width*3//4, screen_vid.height)
        if widescreen:
            speaker_vid = speaker_vid.resized_by_template(template, 'vid-wspeaker', 'slide-ws')
            screen_vid = screen_vid.resized_by_template(template, 'vid-wscreen', 'slide-ws')
        else:
            speaker_vid = speaker_vid.resized_by_template(template, 'vid-speaker')
            screen_vid = screen_vid.resized_by_template(template, 'vid-screen')

        screen_vid, speaker_vid = offset_video(screen_vid, speaker_vid,
                                               screen_offset, mode=trim)

        if preview:
            speaker_vid = speaker_vid.trimmed(end=30)
            screen_vid = screen_vid.trimmed(end=30)

        screen_vid = screen_vid.muted()

        duration = max(screen_vid.duration, speaker_vid.duration)

        if widescreen:
            page = export_template.exported_slide('slide-ws', duration=duration)
        else:
            page = export_template.exported_slide(duration=duration)
        if logo:
            page |= apply_logo(export_template, logo, page.duration, 'logo')
        if screen_on_top:
            main = page | speaker_vid | screen_vid
        else:
            main = page | screen_vid | speaker_vid


    if praha:
        overlay = export_template.exported_slide('slide-overlay', duration=main.duration)
        main |= overlay
    main = main.faded_out(0.5).faded_in(0.5)
    if not no_end:
        if not praha:
            main += sponsors
        main += last

    blank = export_template.exported_slide('slide-blank', duration=main.duration)
    result = blank | main

    print(result.graph)

    outname = [date.strftime('%Y-%m-%d'), event, speaker, title,
               'preview' if preview else None]
    outname = [slugify(x) for x in outname if x]
    outname = os.path.join(outpath, '-'.join(outname) + ".mkv")
    num = 0
    while os.path.exists(outname):
        num += 1
        outname = "{}-{}.mkv".format(outname[:-4].rstrip("-0123456789"), num)

    result.save()
    os.link(result.filename, outname)
    print("Saved as {}".format(outname))

    return result
