Takes a video recording of a presentation, and video grabbed from the screen
(for example via recordmydesktop), does serious time-warping magic to sync
them up, composes them with captions and titles and such,
and throws the video to Youtube for all to see.

Or, it will do that. Someday. So far it just creates the resulting video.


Installation
------------

You'll want Python 3, ffmpeg, Inkscape, Cython, and a version of librosa
with this fix: https://github.com/bmcfee/librosa/pull/127

Make sure you have requirements for various scientific-y libraries – some of
those are:

* Numpy - BLAS and a C compiler
* PyYAML - libyaml-devel
* Scipy - a Fortran compiler

After that, you just::

    python setup.py install


Usage
-----

Make a template SVG file with rectangles where the videos should be, and
assign nice IDs to those rectangles (Inkscape: right-click, Object Properties).
An example is at pyvo/pyvo-640x480.svg

Then you have to write a little script that puts the videos together.
An example is at pyvo/make_vid_simple.py.
(There's also ``make_vid.py`` which is pretty complex, handling most cases
needed for videos from our meetups. If you need something that's not in *that*
example, then it's probably not implemented yet; sorry.)

After that, just run the script, and it'll do the magic!

To return the result (or to quickly check some intermediate output -- video,
image, etc.), do::

    return result_object

and then run the script. It'll generate the file, and give you the filename.

All generated files are stored in a ``__filecache__`` directory under a hash,
so that they are not built again if needed in a subsequent run.
If you change the talk_video_maker internals, or if you start running out of
space, you might need to delete the cache directory.


Pyvec-videomaker
----------------

If you need a simpler script, try Martin Bílek's pyvec-videomaker, the
inspiration for this monstrosity:
https://bitbucket.org/fragariacz/pyvec-videomaker


Architecture and Ideas
----------------------

This project is an experiment. I didn't know much about video processing when I
started, and it shows. Things are held together with digital duct tape.

When I rewrite this one day, these pieces will remain:

- Intermediate files are saved under a hash of their inputs, so when they need
  to be recomputed, they can justr be read off disk.
  Each result that *could* be somehow saved to a file has a hash; but not
  everything that could be saved is -- intermediate video files are a great way
  to lose quality. But, you can save things manually when debugging/playing
  with the pipeline.
- Multimedia is composed of multiple *streams*, and each streams has several
  *channels*. An audio stream can have one (mono), two (stereo), or more
  channels. Video streams theoretically have a channel per color, but that's
  not too useful to know.
- There are *filters* that work on streams, for example "overlay" merges two
  video streams, and "amix" mixes some audio streams together.
  A filter can have zero or more inputs, zero or more outputs, and some
  configuration.
- Streams, filters, multimedia objects, templates (SVGs) -- all are immutable.
  Changes result in new objects (with new hashes) being created.
- The multimedia objects are little more than a collections of streams, with
  convenience operations defined. Filters work on individual streams;
  a simple collection of streams can be encoded into a file. It's all streams
  underneath; what usually happens that the audio and corresponding video have
  quite disjoint sets of filters applied to them: "resize" only applies to
  video, and "mute" to audio.
  But, the multimedia objects are easier to think about when writing the
  processing algorithm.
- In ffmpeg, a stream connects exactly two filters (except input & output
  streams); there are "split" filters to clone streams ans "nullsink" filters
  to not use a stream. In talk-video-maker, each stream has one source,
  but can be an input to 0 or more filters. The splits and nullsinks are
  inserted automatically.
- There is a routine to output the filtergraph, as a graph, on the terminal.
  Extremely useful when debugging (until the graph is 4 pages long).

Some of the worst parts of the code are opts.py (coded offline; I'm pretty sure
it reinvents some wheel) and hashing in __init__ (too WET). Also, streams store
much too little information about themselves; they should keep everything
ffprobe tells us, and filters should update the info accordingly.
SVG operations should probably rely on a different attribute than ID, so that
sets of objects can be targeted for removal/replacement.
If I had the time, you could do "vid[5:10]" to trim videos, "vid[:5]+vid[10:]"
to cut a piece out, "vid[:, 30:50, 30:50]" to crop. Defaulting to seconds for
time, but making frame-/sample-based indexing possible (video/audio, resp.).
And positioning overlays by padding is probably wasteful; it should be possible
to do "vid1 | vid2.at(30, 50)".
