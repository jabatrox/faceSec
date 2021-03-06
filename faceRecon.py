'''
Live facial recognition over a videostream.

This module can also be runned as an independent script.

Usage examples:
    python faceRecon.py
    python faceRecon.py --encodings myEncodings.pickle --display 0 \
--detection-method cnn
Default params are '--encodings encodings.pickle --display 1 \
--detection-method hog'
'''

# Import the necessary packages
from datetime import datetime
from argparse import RawTextHelpFormatter
from imutils.video import VideoStream
from gooey import Gooey, GooeyParser
import cv2
import face_recognition
import argparse
import os
import sys
import pickle
import time
import imutils


# Initialize some variables
# process_this_frame = True
# pathToUnknown = "images/unknown_people/"
known_count = {}        # Dictionnary to count the number of times each known
                        # subject recognized is detected
# known_count_max = 15    # Number of times a subject must be recogised
                        # before granting access
unknown_count = 0       # Number of times an unknown subject is detected
unknown_count_max = 15  # Max number of pictures taken of an unknown subject
unknown_max_reached = False # Boolean: 
granted = []            # List of subject with granted access
grantedCWIDs = []       # List of the CWIDs from subject with granted access
now = datetime.now()    # For the unknown folder path name
maxElapsedTime = 15     # Max number of seconds with recognition mode on

def startup():
    global known_count, unknown_count, unknown_max_reached
    global granted, grantedCWIDs, now
    known_count = {}
    unknown_count = 0
    unknown_max_reached = False
    granted = []
    grantedCWIDs = [] 
    now = datetime.now()

class VideoCamera(object):
    '''
    Creates a VideoCamera object.
    
    :param `encodings`: input path to serialized db of facial encodings.\n
    :param `recon_detection_method`: face detection model to use for live 
    recognition: either `'hog'` or `'cnn'`.\n
    :param `known_count_max`: number of times a subject must be recogised 
    before granting access while using `'hog'` detection method (the number is
    halved if `'cnn'` is used) (default: `15`).\n
    :param `doRecon`: whether or not to the program is on recognition mode 
    (and frames should be processed) (default: `False`).\n
    '''

    def __init__(self, pathToUnknown, encodings, detection_method,
        known_count_max=15, doRecon=False):
        print("############### OPEN CAMERA ###############")
        ## NOTE: If using pure OpenCV (instead of 'VideoStream' from
        ## imutils.video), uncomment the following line and comment the one
        ## from the 'start' function saying "self.stream = VideoStream(src=0)".
        ## Also, in the 'def __del__(self):' function, uncomment the first line
        ## and comment the second one
        # self.video_stream = cv2.VideoCapture(0)

        # Check if the input path for the dataset folder has "/" at the end, and
        # add it if doesn't
        if pathToUnknown[-1:] == "/":
            self.pathToUnknown = pathToUnknown
        else:
            self.pathToUnknown = pathToUnknown + "/"
        self.encodings = encodings
        self.detection_method = detection_method
        self.known_count_max = known_count_max
        self.doRecon = doRecon
        self.load_encodings()
    
    def __del__(self):
        # self.video_stream.release()
        self.stream.stop()

    def start(self):
		# Start capturing the video stream from device 0
        print("[INFO] starting video stream...", end =" ")
        self.stream = VideoStream(src=0)
        print("DONE")
        return self.stream.start()
    
    def read(self):
		# Return the current frame
        return self.stream.read()

    def load_encodings(self):
        # Load encodings from the known faces
        print("############### ENCODING RELOADED ###############")
        try:
            with open(self.encodings, "rb") as file:
                # self.known_encodings = pickle.loads(file.read())
                pass
        except IOError as e:
            # Does not exist or no read permissions for the encodings file
            print("\n[ERROR] Unable to open file")
            sys.exit(1)
            # import faceSec, faceEncode, multiprocessing
            # no_encodings_process = multiprocessing.Process(
            #     name='Encodings',
            #     target = faceEncode.main,
            #     args=(faceSec.args["dataset"], faceSec.args["encodings"],
            #         faceSec.args["encode_detection_method"]))
            # no_encodings_process.daemon = True
            # no_encodings_process.start()
            # no_encodings_process.join()
            # faceEncode.main(faceSec.args["dataset"],
            #     faceSec.args["encodings"], 
            #     faceSec.args["encode_detection_method"])
            # time.sleep(1)
            # faceSec.videoCamera.encodings = faceSec.args["encodings"]
        self.known_encodings = pickle.loads(open(self.encodings, "rb").read())
    
    def get_frame(self):
        # Read a frame from the camera
        frame = self.read()
        if frame is None:
            raise ValueError("[ERROR] camera could not be read. Please check "
                +"if it's accesible")

        # If program is on recognition mode (self.doRecon is set to True),
        # process the frame to detect and recognize faces
        if self.doRecon:
            frame = self.process_frame(frame)

        # The generator uses Motion JPEG, but OpenCV defaults to capture raw
        # images, so we must encode it into JPEG in order to correctly display
        # the video stream.
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def get_frame_local(self):
        # Read a frame from the camera
        frame = self.read()

        # If program is on recognition mode (self.doRecon is set to True),
        # process the frame to detect and recognize faces
        if self.doRecon:
            frame = self.process_frame(frame)
        return frame

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

            # If there is any unknown subject, start taking pictures of it, by
            # saving each frame in which he/she is in, within a folder with
            # the following path:
            # '%pathToUnknown%/[currentDate]/[currentTimestamp]'
            # Ex: 'images\unknown_people\2019-06-25\105122.890024
            elif name == "Unknown" and unknown_count < unknown_count_max:
                todayFolder = self.pathToUnknown + now.strftime("%Y-%m-%d")
                # If folder for current date (today) doesn't exit, create it
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
            # is the name of the folder without the first 10 characters (the
            # CWID and the underscore)
            cv2.rectangle(frame, (left, top), (right, bottom),
                (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            if name != "Unknown":
                name = name[10:].replace("_", " ")
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, (0, 255, 0), 2)
        return frame


# def accessControl(detection_method, known_count_max):
def accessControl(videoCamera):
    # :param `detection_method`: face detection model that is being used during  
    # the live recognition process: either `'hog'` or `'cnn'`. If it's `cnn`, 
    # the `known_count_max` will be divided by 2 to speed up the process.\n
    # :param `known_count_max`: number of times a subject must be recogised 
    # before granting access while using `'hog'` detection method (half of if is 
    # used for `'cnn'`).\n
    '''
    Keep count of the known and unknown subject in the frames, and returns the
    list of the ones having access once the desired `known_count_max` is
    reached. If the face detection model is `cnn`, the `known_count_max` 
    paramenter is divided by 2 to speed up the process.

    :param `videoCamera`: the VideoCamera type object.\n
    :return The list of `granted CWIDs` of the subjects that have been
    recognized `known_count_max` or more times during the live recognition
    phase.
    '''
    # Pickup global variables
    global known_count, unknown_count, unknown_count_max, unknown_max_reached
    global granted, grantedCWIDs, maxElapsedTime

    # Lower value since CNN is slower
    if videoCamera.detection_method == "cnn":
        videoCamera.known_count_max = int(known_count_max/2)

    # Start the facial recognition (the processing of the frames)
    videoCamera.doRecon = True

    # Start the time counter
    startTime = datetime.now()
    elapsedTime = (datetime.now() - startTime).total_seconds()

    # Loop over frames from the video stream for up to `maxElapsedTime`
    # seconds
    while elapsedTime < maxElapsedTime:
        if unknown_count == unknown_count_max and not unknown_max_reached:
            print("[WARNING] %s pictures taken from an unknow subject."
                % unknown_count_max)
            unknown_max_reached = True
        
        # If the dictionary of known face recognized is has keys (names), and
        # any of them has reached a count of 5, grant access to that subject
        if bool(known_count):
            granted = [k for k,v in known_count.items()
                if float(v) == videoCamera.known_count_max]
            if granted:
                for subject in granted:
                    subject_name = subject[10:].replace("_", " ")
                    subject_CWID = subject[:9]
                    grantedCWIDs.append(subject_CWID)
                    print("Face recognized! Access granted to %s (CWID: %s)"
                        % (subject_name, subject_CWID))
                break
        
        # Update the elapsed time it has been running
        elapsedTime = (datetime.now() - startTime).total_seconds()
    
    # Stop the facial recognition (the processing of the frames)
    videoCamera.doRecon = False
    
    # Return the list of granted subjects
    if not granted:
        print("[TIMEOUT] No known subjects recognized. Please, swipe your "+
            "card again")
    return grantedCWIDs


############################################################################
############################################################################
############################### MAIN PROGRAM ###############################
################## ONLY FOR RUNNING AS INDEPENDANT SCRIPT ##################
############################################################################
############################################################################

def main(encodings, display, detection_method, known_count_max):
    '''
    Performs live facial recognition on a videostream from the default camera.

    :param `encodings`: input path to serialized db of facial encodings 
    (default: `'encodings.pickle'`).\n
    :param `display`: whether or not to display output frame to screen during 
    live recognition (default: `1` (yes)).\n
    :param `recon_detection_method`: face detection model to use for live 
    recognition: either `'hog'` or `'cnn'` (default: `'hog'`).\n
    :param `known_count_max`: number of times a subject must be recogised 
    before granting access while using `'hog'` detection method (the number is
    halved if `'cnn'` is used) (default: `15`).\n
    :return The list of `granted CWIDs` of the subjects that have been
    recognized `known_count_max` or more times during the live recognition
    phase.
    '''

    # Pickup global variables and reset them
    global known_count, unknown_count, unknown_count_max, unknown_max_reached
    global granted, grantedCWIDs, maxElapsedTime
    startup()

    # Lower value since CNN is slower
    if detection_method == "cnn":                   
        known_count_max = int(known_count_max/2)

    # Initialize some variables
    # process_this_frame = True
    videoCam_started = False
    videoCamera = VideoCamera("images/unknown_people/", encodings,
        detection_method, known_count_max, True)
    if not videoCam_started:
        videoCam_started = True
        videoCamera.start()

    # Start the time counter
    startTime = datetime.now()
    elapsedTime = (datetime.now() - startTime).total_seconds()

    # Loop over frames from the video stream for up to `maxElapsedTime`
    # seconds
    while elapsedTime < maxElapsedTime:
        # Grab a frame from the threaded video stream
        frame = videoCamera.get_frame_local()
        videoCamera.doRecon = True

        # Check to see if the output frame must be displayed to the screen
        if display > 0:
            cv2.imshow("Frame", frame)
            
            # If the `q` key is pressed, break from the loop and end the program
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

        global unknown_max_reached
        if unknown_count == unknown_count_max and not unknown_max_reached:
            print("[INFO] %s pictures taken from an unknow subject."
                % unknown_count_max)
            unknown_max_reached = True
        
        # If the dictionary of known face recognized is has keys (names), and
        # any of them has reached a count of 5, grant access to that subject
        if bool(known_count):
            # print("known_count =", end = " ")
            granted = [k for k,v in known_count.items()
                if float(v) == known_count_max]
            if granted:
                for subject in granted:
                    subject_name = subject[10:].replace("_", " ")
                    subject_CWID = subject[:9]
                    grantedCWIDs.append(subject_CWID)
                    print("Face recognized! Access granted to %s (CWID: %s)"
                        % (subject_name, subject_CWID))
                break
        
        # Update the elapsed time it has been running
        elapsedTime = (datetime.now() - startTime).total_seconds()

    # Release handle to the webcam
    videoCamera.doRecon = False
    videoCamera.__del__()
    cv2.destroyAllWindows()

    # Return the list of granted subjects
    if not granted:
        print("[TIMEOUT] No known subjects recognized. Please, swipe your "+
            "card again")
    return grantedCWIDs


@Gooey(program_name="Face Recognition", image_dir='.')
def argParser():
    # Construct the argument parser and parse the arguments
    # ap = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    ap = GooeyParser(formatter_class=RawTextHelpFormatter)
    ap.add_argument("-e", "--encodings", widget="FileChooser", type=str,
        default="encodings.pickle",
        help="input path to serialized db of facial encodings "+
        "\ndefault: 'encodings.pickle'")
    ap.add_argument("-u", "--unknown",  type=str, default="images/unknown_people",
        help="path to output directory of unknown face images.\ndefault: "+
        "'images/unknown_people'")
    ap.add_argument("-d", "--detection-method", type=str, default="hog",
        help="face detection model to use: either `hog` or `cnn`"+
        "\ndefault: 'hog'")
    ap.add_argument("-c", "--count-recon", type=int, default=15,
        help="number of times a subject must be recogised before granting "+
        "access while using `hog` detection method (it will auto calculate "+
        "it for `cnn`. Test to adjust manually\ndefault: 15")
    ap.add_argument("-Y", "--display", type=int, default=1,
        help="whether or not to display output frame to screen during live "+
        "recognition\ndefault: `1` (yes)")
    global args
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    # Call the argument parser function
    argParser()
    
    # Call the 'main' function with the parsed arguments
    main(args["encodings"], args["display"], args["detection_method"],
        args["count_recon"])
