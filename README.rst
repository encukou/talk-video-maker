Takes a video recording of a presentation, and video grabbed from the screen
(for example via recordmydesktop), does serious time-warping magic to sync
them up, composes them with captions and titles and such,
and throws the video to Youtube for all to see.

Or, it will do that. Someday. So far it just creates the resulting video.

Installation
------------

You'll want Python 3, ffmpeg, Inkscape, and a version of librosa with this fix:
https://github.com/bmcfee/librosa/pull/127

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

Then you have to write a little script that puts the videos together.
An example is at pyvo/make_video.py.
(If you need something that's not in the example, then it's probably not
implemented yet; sorry.)

After that, just run the script, and it'll do the magic!

If you need to look at any intermediate output (video, image, etc.), do::

    exit(some_object.filename)

and then run the script. It'll generate the file, and give you the filename.

All generated files are stored in a ``__filecache__`` directory under a hash,
so that they are not built again if needed in a subsequent run.
If you change the talk_video_maker internals, you might need to delete the
cache directory.

Pyvec-videomaker
----------------

If you need a simpler script, try Martin Bílek's pyvec-videomaker:
https://bitbucket.org/fragariacz/pyvec-videomaker
