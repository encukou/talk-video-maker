Takes a video recording of a presentation, and video grabbed from the screen
(for example via recordmydesktop), does serious time-warping magic to sync
them up, composes them with captions and titles and such,
and throws the video to Youtube for all to see.

Or, it will do that. Someday. So far I'm just messing with asyncio and
time warping algorithms – turns out different videos can be recorded
at different speeds.

Installation
------------

You'll want Python 3, ffmpeg, and a version of librosa with this fix:
https://github.com/bmcfee/librosa/pull/127

Make sure you have requirements for various scientific-y libraries – some of
those are:

* Numpy - BLAS and a C compiler
* PyYAML - libyaml-devel
* Scipy - a Fortran compiler

After that, you just::

    pip install -r requirements.txt

Usage
-----

Use::

    python -m talk_video_maker /path/to/the/sources

The directory should contain:

* One or more .mts files with the video from the camera
* One .ogv file with the screen grab
* One .yaml file with information for titles

The program creates a bunch of cache files named with a leading underscore.
These allow the script to pick up where it left off if interrupted.


Pyvec-videomaker
----------------

If you need a working script, try Martin Bílek's pyvec-videomaker:
https://bitbucket.org/fragariacz/pyvec-videomaker
