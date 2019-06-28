#!/bin/bash
echo -e "Installing all necessary packages...\n"
sudo apt-get update
sudo apt-get install git openssh-server
sudo apt-get install build-essential cmake
sudo apt-get install libopenblas-dev liblapack-dev
sudo apt-get install libx11-dev libgtk-3-dev
sudo apt-get install python3 python3-dev python3-pip
pip3 install numpy pathlib2
pip3 install opencv-contrib-python
git clone https://github.com/davisking/dlib.git
cd dlib
mkdir build
cd build
cmake .. -DDLIB_USE_CUDA=1 -DUSE_AVX_INSTRUCTIONS=1
cmake --build .
cd ..
python setup.py install --yes USE_AVX_INSTRUCTIONS --yes DLIB_USE_CUDA
pip3 install face_recognition
pip3 install imutils
pip3 install schedule
pip3 install flask
pip3 install Flask-SocketIO
pip3 install gooey
echo -e "\nInstallation finished!"
