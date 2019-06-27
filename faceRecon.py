'''
Live facial recognition over a videostream.

This module can also be called as an independent script.

Usage examples:
    python faceRecon.py
    python faceRecon.py --encodings myEncodings.pickle --display 0 --detection-method cnn
Default params are '--encodings encodings.pickle --display 1 --detection-method hog'

'''

# Import the necessary packages
from datetime import datetime
from argparse import RawTextHelpFormatter
from imutils.video import VideoStream
from gooey import Gooey, GooeyParser
import cv2
import face_recognition
import argparse
import threading
import os
import sys
import pickle
import time
import imutils

# This program includes some basic performance tweaks to make things run a lot faster:
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

# PLEASE NOTE: This program requires OpenCV (the `cv2` library) to be installed only to read from your webcam.
# OpenCV is *not* required to use the face_recognition library.

# Initialize some variables
# face_locations = []
# face_encodings = []
# face_names = []
# process_this_frame = True
pathToUnknown = "images/unknown_people/"
known_count = {}        # Dictionnary to count the number of times each known
                        # subject recognized is detected
unknown_count = 0       # Number of times an unknown subject is detected
unknown_count_max = 15  # Max number of pictures taken of an unknown subject
granted = []            # List of subject with granted access
now = datetime.now()    # For the unknown folder path name
maxElapsedTime = 15     # Max number of seconds with recognition mode on

def startup():
    global known_count, unknown_count, unknown_count_max, granted, now, maxElapsedTime
    known_count = {}
    unknown_count = 0
    granted = []
    now = datetime.now()

class VideoCamera(object):
    '''
    Creates a VideoCamera object
    
        :param encodings: input path to serialized db of facial encodings.\n
        :param recon_detection_method: face detection model to use for live recognition: either 'hog' or 'cnn'.\n
        :param doRecon: whether or not to the program is on recognition mode (and frames should be processed).\n
    '''

    def __init__(self, encodings, detection_method, doRecon):
        # If using pure OpenCV (instead of 'VideoStream' from imutils.video),
        # uncomment the following line and comment the next one, and do the
        # same in the 'def __del__(self):' function
        # self.video_stream = cv2.VideoCapture(0)
        self.encodings = encodings
        self.detection_method = detection_method
        self.doRecon = doRecon
        self.load_encodings()
        print("############### OPEN CAMERA ###############")
    
    def __del__(self):
        # self.video_stream.release()
        self.stream.stop()

    def start(self):
		# Start capturing the video stream from device 0
        print("[INFO] starting video stream...", end =" ")
        self.stream = VideoStream(src=0)
        print("[DONE]")
        return self.stream.start()
    
    def read(self):
		# Return the current frame
        return self.stream.read()

    def load_encodings(self):
        # Load encodings from the known faces
        print("############### ENCODING RELOADED ###############")
        try:
            with open(self.encodings) as file:
                pass
        except IOError as e:
            # Does not exist or no read permissions for the encodings file
            print("\n[ERROR] Unable to open file")
            sys.exit(1)
        self.known_encodings = pickle.loads(open(self.encodings, "rb").read())
    
    def get_frame(self):
        # Read the frame from the camera
        frame = self.read()

        # If program is on recognition mode (from the main module, 'faceSec'),
        # process the frame to detect and recognize faces
        if self.doRecon:
            frame = self.process_frame(frame)

        # The generator uses Motion JPEG, but OpenCV defaults to capture raw
        # images, so we must encode it into JPEG in order to correctly display
        # the video stream.
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def process_frame(self, frame):
        # Process each received frame from the video stream (on recognition
        # mode)

        # Not sure why needed, but programs fails without it
        global unknown_count

        # Convert the input frame from BGR color (which OpenCV uses) to
        # RGB (which face_recognition uses), and then resize it to 1/4 size 
        # for faster face recognition processing. The resizing is by default
        # 1/4 of the original image, but it can be set to any size.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = imutils.resize(rgb, width=int(rgb.shape[1]/4)) # width=400
        r = frame.shape[1] / float(rgb.shape[1])

        # Detect the (x, y)-coordinates of the bounding face locations
        # corresponding to each face in the input frame, and then compute the
        # facial embeddings for each face
        face_locations = face_recognition.face_locations(rgb,
            model=self.detection_method)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)
        names = []
        
        # Loop over the facial embeddings
        for encoding in face_encodings:
            # Try to match each face in the input image to our known encodings
            matches = face_recognition.compare_faces(self.known_encodings["encodings"],
                encoding, tolerance=0.55)
            index_match = [k for k,v in matches.items() if v == True]
            name = "Unknown"

            # Check to see if we have found a match
            if True in matches:
                # Find the indexes of all matched faces, and then initialize a
                # dictionary to count the total number of times each face
                # was matched
                matched_indexes = [i for (i, b) in enumerate(matches) if b]
                matched_counts = {}

                # Loop over the matched indexes and count them for each
                # recognized face
                for i in matched_indexes:
                    name = self.known_encodings["names"][i]
                    matched_counts[name] = matched_counts.get(name, 0) + 1

                # Determine the recognized face with the largest number
                # of votes. Note that, in the event of an unlikely tie, Python
                # will select first entry in the dictionary)
                name = max(matched_counts, key=matched_counts.get)
                
                # For each new known face recognized, add a key with its name
                # to the dictionary that counts the number of times it has
                # appeared. If the key already exist, increment the number of
                # times that subject has been recognized
                if name in known_count:
                    known_count[name] += 1
                else:
                    known_count[name] = 1

            # If there is any unknow subject, start taking pictures of it, by
            # saving each frame in which he/she is in, within a folder with
            # the following path:
            # '%pathToUnknown%/[currentDate]/[currentTimestamp]'
            # Ex: 'images\unknown_people\2019-06-25\105122.890024
            elif name == "Unknown" and unknown_count < unknown_count_max:
                todayFolder = pathToUnknown + now.strftime("%Y-%m-%d")
                # If folder for current date (today) doesn't exit, create
                # it
                if not os.path.exists(todayFolder):
                    os.makedirs(todayFolder)
                    print(f"[INFO] folder for day {todayFolder[-10:]} created. "
                        +"Unknown subjects detected will be added there")
                timestampUnknownSubject = now.strftime("%H%M%S.%f")
                currentCaptureFolder = todayFolder +"/" + timestampUnknownSubject
                if not os.path.exists(currentCaptureFolder):
                    os.makedirs(currentCaptureFolder)
                    print("[WARNING] unknown subject detected! Folder %s created"
                        % timestampUnknownSubject)
                unknown_count += 1
                print("\__ capturing image %s/%s (%s.jpg)" % (unknown_count,
                    unknown_count_max, unknown_count))
                cv2.imwrite(currentCaptureFolder+"/%s.jpg"
                    % unknown_count, frame)
            
            # Update the list of names
            names.append(name)

        # Loop over the recognized faces
        for ((top, right, bottom, left), name) in zip(face_locations, names):
            # Rescale the face coordinates to the orginal ones
            top = int(top * r)
            right = int(right * r)
            bottom = int(bottom * r)
            left = int(left * r)

            # Draw the recognized face name on the image. The name displayed
            # is the name of the folder without the last 10 characters (the
            # CWID)
            cv2.rectangle(frame, (left, top), (right, bottom),
                (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            if name != "Unknown":
                name = name[:-10].replace("_", " ")
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, (0, 255, 0), 2)
        return frame

def accessControl():
    global known_count, unknown_count, unknown_count_max
    global granted, now, maxElapsedTime
    # known_count = {}
    # unknown_count = 0
    # unknown_count_max = 30
    # granted = []
    # now = datetime.now()
    # maxElapsedTime = 15

    # Start the time counter
    startTime = datetime.now()
    elapsedTime = (datetime.now() - startTime).total_seconds()

    # Loop over frames from the video stream for up to `maxElapsedTime`
    # seconds
    while elapsedTime < maxElapsedTime:
        if unknown_count == unknown_count_max:
            print("[INFO] %s pictures taken from an unknow subject. Exiting."
                % unknown_count_max)
            break
        
        # If the dictionary of known face recognized is has keys (names), and
        # any of them has reached a count of 5, grant access to that subject
        if bool(known_count):
            # print("known_count =", end = " ")
            granted = [k for k,v in known_count.items() if float(v) == 5]
            if granted:
                for subject in granted:
                    subject_name = subject[:-10].replace("_", " ")
                    subject_CWID = subject[-9:]
                    print("Face recognized! Access granted to %s (CWID: %s)"
                        % (subject_name, subject_CWID))
                break
        
        # Update the elapsed time it has been running
        elapsedTime = (datetime.now() - startTime).total_seconds()
    
    # Return the list of granted subjects
    if not granted:
        print("[TIMEOUT] No known subjects recognized. Please, swipe your "+
            "card again")
    return granted

############################################################################
############################################################################
############################### MAIN PROGRAM ###############################
################## ONLY FOR RUNNING AS INDEPENDANT SCRIPT ##################
############################################################################
############################################################################

def main(encodings, display, detection_method):
    '''
    Performs live facial recognition on a videostream from the default camera.

    :param encodings: input path to serialized db of facial encodings (default: 'encodings.pickle').\n
    :param display: whether or not to display output frame to screen during live recognition (default: 1 (yes)).\n
    :param recon_detection_method: face detection model to use for live recognition: either 'hog' or 'cnn' (default: 'hog').\n
    :return The list of granted subject received from the live recognition module
    '''

    # Initialize some variables
    # face_locations = []
    # face_encodings = []
    # face_names = []
    # process_this_frame = True
    pathToUnknown = "images/unknown_people/"
    known_count = {}
    unknown_count = 0
    unknown_count_max = 30
    granted = []
    now = datetime.now()
    maxElapsedTime = 15

    # Load encodings from the known faces, and warm up the camera sensor
    print("[INFO] loading encodings...", end =" ")
    try:
        with open(encodings) as file:
            pass
    except IOError as e:
        # Does not exist OR no read permissions
        print("\n[ERROR] Unable to open file")
        sys.exit(1)
    known_encodings = pickle.loads(open(encodings, "rb").read())
    print("[DONE]")
    print("[INFO] starting video stream...", end =" ")
    video_stream = VideoStream(src=0).start()
    # video_stream = VideoCamera().start()
    time.sleep(1.0)
    print("[DONE]")

    # Start the time counter
    startTime = datetime.now()
    elapsedTime = (datetime.now() - startTime).total_seconds()

    # Loop over frames from the video stream for up to `maxElapsedTime`
    # seconds
    while elapsedTime < maxElapsedTime:
        # Grab a frame from the threaded video stream
        frame = video_stream.read()
        
        # Convert the input frame from BGR color (which OpenCV uses) to
        # RGB (which face_recognition uses), and then resize it to 1/4 size 
        # for faster face recognition processing. The resizing is by default
        # 1/4 of the original image, but it can be set to any size.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = imutils.resize(rgb, width=int(rgb.shape[1]/4)) # width=400
        r = frame.shape[1] / float(rgb.shape[1])

        # Detect the (x, y)-coordinates of the bounding face locations
        # corresponding to each face in the input frame, and then compute the
        # facial embeddings for each face
        face_locations = face_recognition.face_locations(rgb,
            model=detection_method)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)
        names = []
        
        # Loop over the facial embeddings
        for encoding in face_encodings:
            # Try to match each face in the input image to our known encodings
            matches = face_recognition.compare_faces(known_encodings["encodings"],
                encoding, tolerance=0.55)
            # matches_06 = face_recognition.compare_faces(known_encodings["encodings"],
            #     encoding)
            # distances = face_recognition.face_distance(known_encodings["encodings"],
            #     encoding)
            # index_match = [k for k,v in enumerate(matches) if v == True]
            # index_match_06 = [k for k,v in enumerate(matches) if v == True]
            # distances_match_06 = [k for k,v in enumerate(distances) if v <= 0.60]
            # distances_match_055 = [k for k,v in enumerate(distances) if v <= 0.55]
            # print("-"*20)
            # print("index_match = ", end='')
            # print(index_match)
            # print("index_match_06 = ", end='')
            # print(index_match_06)
            # print("distances = ", end='')
            # print(distances)
            # print("distances_match_06 = ", end='')
            # print(distances_match_06)
            # print("distances_match_055 = ", end='')
            # print(distances_match_055)
            # print("matches = ", end='')
            # print(matches)
            # print("matches_06 = ", end='')
            # print(matches_06)
            # print("-"*20)
            name = "Unknown"

            # Check to see if we have found a match
            if True in matches:
                # Find the indexes of all matched faces, and then initialize a
                # dictionary to count the total number of times each face
                # was matched
                matched_indexes = [i for (i, b) in enumerate(matches) if b]
                matched_counts = {}

                # Loop over the matched indexes and count them for each
                # recognized face
                for i in matched_indexes:
                    name = known_encodings["names"][i]
                    matched_counts[name] = matched_counts.get(name, 0) + 1

                # Determine the recognized face with the largest number
                # of votes. Note that, in the event of an unlikely tie, Python
                # will select first entry in the dictionary)
                name = max(matched_counts, key=matched_counts.get)
                
                # If a new known face is recognized, add a key with its name
                # to the dictionary that counts the number of times it appeared.
                # If the key already exist, increment the number of times that
                # subject has been recognizd
                if name in known_count:
                    known_count[name] += 1
                else:
                    known_count[name] = 1
            elif name == "Unknown" and unknown_count < unknown_count_max:
                    todayFolder = pathToUnknown + now.strftime("%Y-%m-%d")
                    if not os.path.exists(todayFolder):
                        os.makedirs(todayFolder)
                        print(f"[INFO] folder for day {todayFolder[-10:]} created. "
                            +"Unknown subjects detected will be added there")
                    timestampUnknownSubject = now.strftime("%H%M%S.%f")
                    currentCaptureFolder = todayFolder +"/" + timestampUnknownSubject
                    if not os.path.exists(currentCaptureFolder):
                        os.makedirs(currentCaptureFolder)
                        print("[WARNING] unknown subject detected! Folder %s created"
                            % timestampUnknownSubject)
                    unknown_count += 1
                    print("\__ capturing image %s/%s (%s.jpg)" % (unknown_count,
                        unknown_count_max, unknown_count))
                    cv2.imwrite(currentCaptureFolder+"/%s.jpg"
                        % unknown_count, frame)
            
            # Update the list of names
            names.append(name)

        # Loop over the recognized faces
        for ((top, right, bottom, left), name) in zip(face_locations, names):
            # Rescale the face coordinates to the orginal ones
            top = int(top * r)
            right = int(right * r)
            bottom = int(bottom * r)
            left = int(left * r)

            # Draw the recognized face name on the image. The name displayed
            # is the name of the folder without the last 10 characters (the
            # CWID)
            cv2.rectangle(frame, (left, top), (right, bottom),
                (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            if name != "Unknown":
                name = name[:-10].replace("_", " ")
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, (0, 255, 0), 2)

        # Check to see if the output frame must be displayed to the screen
        if display > 0:
            cv2.imshow("Frame", frame)
            
            # If the `q` key is pressed, break from the loop and end the program
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

        if unknown_count == unknown_count_max:
            print("[INFO] %s pictures taken from an unknow subject. Exiting."
                % unknown_count_max)
            break
        
        # If the dictionary of known face recognized is has keys (names), and
        # any of them has reached a count of 5, grant access to that subject
        if bool(known_count):
            # print("known_count =", end = " ")
            granted = [k for k,v in known_count.items() if float(v) == 5]
            if granted:
                for subject in granted:
                    subject_name = subject[:-10].replace("_", " ")
                    subject_CWID = subject[-9:]
                    print("Face recognized! Access granted to %s (CWID: %s)"
                        % (subject_name, subject_CWID))
                break
        
        # Update the elapsed time it has been running
        elapsedTime = (datetime.now() - startTime).total_seconds()

    # Release handle to the webcam
    video_stream.stop()
    cv2.destroyAllWindows()

    # Return the list of granted subjects
    if not granted:
        print("[TIMEOUT] No known subjects recognized. Please, swipe your "+
            "card again")
    return granted


@Gooey(program_name="Face Recognition", image_dir='.')
def argParser():
    # Construct the argument parser and parse the arguments
    # ap = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    ap = GooeyParser(formatter_class=RawTextHelpFormatter)
    ap.add_argument("-e", "--encodings", widget="FileChooser", type=str,
        default="encodings.pickle",
        help="input path to serialized db of facial encodings "+
        "\ndefault: 'encodings.pickle'")
    ap.add_argument("-y", "--display", type=int, default=1,
        help="whether or not to display output frame to screen during live "+
        "recognition\ndefault: `1` (yes)")
    ap.add_argument("-d", "--detection-method", type=str, default="hog",
        help="face detection model to use: either `hog` or `cnn`"+
        "\ndefault: 'hog'")
    global args
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    # Call the argument parser function
    argParser()
    
    # Call the 'main' function with the parsed arguments
    main(args["encodings"], args["display"], args["detection_method"])