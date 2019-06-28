"""Installation file for project faceSec
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='faceSec',  # Required
    version='1.0',  # Required
    description='A facial recognition second factor authentication for secure access, as a school project',  # Optional
    long_description=long_description,  # Optional
    long_description_content_type='text/markdown',  # Optional (see note above)
    url='https://github.com/jabatrox/faceSec',  # Optional
    author='Javier Soler Macías',  # Optional
    author_email='jsoler92@hotmail.com',  # Optional
    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Education',
        'Intended Audience :: Other Audience',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Topic :: Security',
        'Topic :: Multimedia :: Video :: Capture',
        'Topic :: Multimedia :: Video :: Display',
        'Topic :: Scientific/Engineering :: Visualization',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        # These classifiers are *not* checked by 'pip install'. See instead
        # 'python_requires' below.
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='facial recognition webserver webcam two-side authentication security',  # Optional
    packages=find_packages(exclude=['tests']),  # Required
    python_requires='>=3.6',
    install_requires=[
        'numpy',
        'pathlib2',
        'dlib',
        'opencv-contrib-python',
        'face_recognition',
        'imutils',
        'schedule',
        'flask',
        'Flask-SocketIO',
        'gooey'
    ],  # Optional
    entry_points={  # Optional
        'console_scripts': [
            'faceSec=faceSec:main',
        ],
    },
)
