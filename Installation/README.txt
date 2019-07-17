This is the way to install all dependencies needed for the program to work on Windows 10 using Conda (which installed Python 3.6.7).

1) Install miniconda with "Miniconda3-latest-Windows-x86_64.exe".
==> IMPORTANT: be sure to check the option "Add Anaconda to my PATH environment variable"!

2) Download the lastest dlib wheel (.whl) file. Currently, the latest dlib version is 19.17.0.
==> IMPORTANT: the ".whl" file is not available by default on the official repository for the latest versions. For the current latest version, 19.17.0, the wheel file "dlib-19.17.0-cp36-cp36m-win_amd64.whl" is available here: https://github.com/pzx521521/dlib-Python_whl_19.17.0_win_amd64/releases

3) Run the following commands on a CMD shell with administrator permission:
conda install -c conda-forge dlib
conda install pip
pip install opencv-contrib-python
pip install dlib-19.17.0-cp36-cp36m-win_amd64.whl
pip install -r requirements.txt
Modules in requirements file:
face_recognition, imutils, schedule, flask, Flask-SocketIO, gooey, authlib, google-api-python-client, google-auth

4) Open Visual Studio Code, and select the "Python 3.6.7 64-bit ('base': conda)" run environment

5) Run the file in terminal (right-click on the file, and "Run Python File in Terminal)