from setuptools import setup, Extension

from Cython.Build import cythonize

extensions = [
    Extension("talk_video_maker.cdtw", ["cdtw.pyx"]),
]


setup(
    name='talk_video_maker',
    version='0.1',
    description='A compiler for talk videos',
    url='https://github.com/encukou/talk_video_maker',
    author='Petr Viktorin',
    author_email='encukou@gmail.com',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    packages=['talk_video_maker'],
    install_requires=[
        'pyyaml',
        'numpy',
        'scipy',
        'librosa',
        'lxml',
        'qrcode',
        # /usr/bin/inkscape
        # /usr/bin/ffmpeg
    ],
    setup_requires = ['cython'],

    ext_modules = cythonize(extensions),
)
