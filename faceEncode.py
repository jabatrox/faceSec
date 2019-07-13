'''
Generate a file of encodings from a dataset of images of faces.

It is important to note that this task requires a high level of performance.
Therefore:
    - When encoding on laptop, desktop, or GPU (slower, more accurate): use \
`cnn` detection method
    - When encoding on Raspberry Pi or just with CPU (no GPU) (faster, less \
accurate): use `hog` detection method

This module can also be runned as an independent script.

Usage examples:
    python faceEncode.py
    python faceEncode.py --dataset dataset --encodings myEncodings.pickle \
--detection-method cnn
Default params are '--dataset images/known_people --encodings encodings.pickle \
--detection-method hog'
'''

# Import the necessary packages
from imutils import paths
from argparse import RawTextHelpFormatter
from gooey import Gooey, GooeyParser
import cv2
import face_recognition
import argparse
import os
import pickle

def main(dataset, encodings, detection_method):
    '''
    Performs the encodings update.

    :param `dataset`: path to input directory of face images to encode 
    (default: `'images/known_people'`).\n
    :param `encodings`: output path to serialized db of facial encodings 
    (default: `'encodings.pickle'`).\n
    :param `encode_detection_method`: face detection model to use for 
    encodings: either `'hog'` or `'cnn'` (default: `'hog'`).
    '''
    # Check if the input path for the dataser folder has "/" at the end, and
    # remove it if does
    if dataset[-1:] == "/":
        dataset = dataset[:-1]

    # Grab the paths to the images of the dataset and count them
    print("[INFO] quantifying faces...", end=" ")
    imagePaths = list(paths.list_images(dataset))
    print("DONE")

    # Initialize the list of known face encodings and names
    known_face_encodings = []
    known_face_names = []

    # Loop over the image paths
    for (i, imagePath) in enumerate(imagePaths):
        # Extract the person name from the image path
        print("[INFO] processing image {}/{}...".format(i + 1,
            len(imagePaths)), end=" ")
        name = imagePath.split(os.path.sep)[-2]

        # Load the input image and convert it from RGB (OpenCV ordering)
        # to RGB (dlib ordering, which face_recognition uses)
        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect the (x, y)-coordinates of the bounding face locations
        # corresponding to each face in the input image, and then compute
        # the facial embeddings for each face
        face_locations = face_recognition.face_locations(rgb,
            model=detection_method)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        # Loop over the encodings
        for encoding in face_encodings:
            # Add each encoding + name to the set of known names and
            # encodings
            known_face_encodings.append(encoding)
            known_face_names.append(name)
        print("DONE")

    # Dump the facial encodings + names to disk
    print("[INFO] Serializing encodings...", end=" ")
    data = {"encodings": known_face_encodings, "names": known_face_names}
    f = open(encodings, "wb")
    f.write(pickle.dumps(data))
    f.close()
    print("DONE")

@Gooey(program_name="Face Encoder", image_dir='.')
def argParser():
    # Construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    ap.add_argument("-i", "--dataset", type=str, default="images/known_people",
        help="path to input directory of face images.\ndefault: "+
        "'images/known_people'")
    ap.add_argument("-e", "--encodings", type=str, default="encodings.pickle",
        help="output path to serialized db of facial encodings "+
        "\ndefault: 'encodings.pickle'")
    ap.add_argument("-d", "--detection-method", type=str, default="hog",
        help="face detection model to use: either `hog` or `cnn`"+
        "\ndefault: 'hog'")
    global args
    args = vars(ap.parse_args())
    return args

if __name__ == "__main__":
    # Call the argument parser function
    argParser()

    # Start the time counter
    from datetime import datetime
    startTime = datetime.now()

    # Call the 'main' function with the parsed arguments
    main(args["dataset"], args["encodings"], args["detection_method"])

    # Calculate the elapsed time to make the encodings
    elapsedTime = (datetime.now() - startTime)
    print(f"[FINISHED] encoding time: {elapsedTime} ({elapsedTime.total_seconds()}s)")
