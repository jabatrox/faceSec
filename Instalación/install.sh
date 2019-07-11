#!/bin/bash
#if [ "$UID" -ne 0 ]; then
#    echo "This script runs with root priviledges."
#    exec sudo "$0" "$@"
#fi
echo -e "Installing all necessary packages...\n"
sudo apt-get update
sudo apt-get install git
sudo apt-get install build-essential gcc cmake
sudo apt-get install libopenblas-dev libblas-dev liblapack-dev libatlas-base-dev
sudo apt-get install libx11-dev libgtk-3-dev
sudo apt-get install python3 python3-dev python3-pip
echo -e "===== SYSTEM DEPENDENCIES INSTALLATION FINISHED ====="
printf "===== PRESS 'ENTER' TO PROCEED WITH INSTALLATION OF PYTHON LIBRARIES ===== "
read -r keypressed
sudo pip3 install numpy pathlib2
sudo pip3 install opencv-contrib-python
git clone https://github.com/davisking/dlib.git
cd dlib
mkdir build
cd build
cmake .. -DDLIB_USE_CUDA=1 -DUSE_AVX_INSTRUCTIONS=1
cmake --build .
cd ..
sudo python3 setup.py install --yes USE_AVX_INSTRUCTIONS --yes DLIB_USE_CUDA --compiler-flags "-DCUDA_HOST_COMPILER=/usr/bin/gcc-7"
sudo pip3 install face_recognition
sudo pip3 install imutils
sudo pip3 install schedule
sudo pip3 install flask
sudo pip3 install Flask-SocketIO
sudo pip3 install gooey
sudo pip3 install authlib google-api-python-client google-auth
cd ~/
git clone https://github.com/jabatrox/faceSec
echo -e "\nInstallation finished!"
