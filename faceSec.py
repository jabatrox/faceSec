# Import the necessary packages
from datetime import datetime
from argparse import RawTextHelpFormatter
from threading import Thread, Event
# from flask import Flask, flash, redirect, render_template, request, send_file, session, abort
from flask import *
from flask_socketio import SocketIO, emit
import argparse
import threading
import multiprocessing
import schedule
import time
import sys
import cv2
import faceEncode
import faceRecon
import logging


############################## ARGUMENT PARSER ##############################

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
ap.add_argument("-i", "--dataset", default="images/known_people",
    help="path to input directory of face images.\ndefault: "+
        "'images/known_people'")
ap.add_argument("-e", "--encodings", type=str, default="encodings.pickle",
    help="path to serialized db of facial encodings "+
        "\ndefault: 'encodings.pickle'")
ap.add_argument("-u", "--encodings-update-time", type=str, default="01:00:00",
    help="time when the encoding will be updated daily "+
        "\ndefault: '01:00:00'")
ap.add_argument("-d", "--encode-detection-method", type=str, default="hog",
    help="face detection model to use for encodings: either 'hog' or 'cnn'"+
        "\ndefault: 'hog'")
ap.add_argument("-r", "--recon-detection-method", type=str, default="hog",
    help="face detection model to use for live recognition: either 'hog' "+
        "or 'cnn'\ndefault: 'hog'")
ap.add_argument("-y", "--display", type=int, default=1,
    help="whether or not to display output frame to screen during live "+
        "recognition\ndefault: '1' (yes)")
args = vars(ap.parse_args())


###################### FLAKS AND SOCKET.IO INITIALIZER #####################

# Start and config Flask and Socket.io app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'This Is My Secret!'
socketio = SocketIO(app)

# To avoid seeing all the GET/POST requests on the terminal
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

############################# GENERAL VARIABLES ############################

# Some basic variables
accepted_cards = ['1234', '5678']
received_card_number = ""
onFirstRun = True
# doRecon = False # Is it doing face recognition or just streaming?

# Create the videoCamera object with the parsed arguments
videoCamera = faceRecon.VideoCamera(args["encodings"],
            args["recon_detection_method"], False)
videoCam_started = False


####################### UPDATE WELCOME MESSAGE CLASS #######################

updateWelcome_thread = threading.Thread()
# thread_stop_event = threading.Event()
thread_display_name = threading.Event()
thread_display_name.set()
class updateWelcomeThread(Thread):
    '''
        Updates the name of the person who has swiped the card (if any),
        otherwise shows "Waiting for user..."
    '''
    def __init__(self):
        self.delay = 1
        super(updateWelcomeThread, self).__init__()
    def updateWelcomeGenerator(self):
        while True:
            # Default message for waiting
            msg = "Waiting for user..."

            # Update name only if it has changed (someone has swiped the card)
            if received_card_number in accepted_cards:
                msg = "Hello "+received_card_number+"! Please now place yourself in front of the camera for face recognition"
            if thread_display_name.isSet():
                socketio.emit('newMessage', {'message': msg})
                thread_display_name.clear()

            # Restore to default messsage when live recon is finised
            if videoCamera.doRecon:
                thread_display_name.set()
            time.sleep(self.delay)
    def run(self):
        self.updateWelcomeGenerator()


########################### FUNCTIONS DEFINITION ###########################

def launchUpdateEncodings():
    '''
    Launch the scheduler to update the encodings at the specified time.
    '''
    print("[INFO] process to update encodings launched and running "+
        "in background. It will update encodings everyday at %s"
        % args["encodings_update_time"])
    schedule.every().day.at(args["encodings_update_time"]).do(updateEncodings,
        args["dataset"], args["encodings"], args["encode_detection_method"])
    while True:
        schedule.run_pending()


def updateEncodings(dataset, encodings, encode_detection_method):
    '''
    Performs the encodings update.

        :param dataset: path to input directory of face images to encode (default: 'images/known_people').
        :param encodings: output path to serialized db of facial encodings (default: 'encodings.pickle').
        :param encode_detection_method: face detection model to use for encodings: either 'hog' or 'cnn' (default: 'hog').
    '''
    # python faceEncode.py
    #   --dataset images/known_people
    #   --encodings encodings.pickle
    #   --encode-detection-method hog
    print("-"*60)
    print("Updating encodings...")

    # Start the time counter
    startTime = datetime.now()
    print("[INFO] current time: "+
        startTime.strftime("%Y-%m-%d at %H:%M:%S"))
    print("[INFO] dataset: '%s'" % dataset)
    print("[INFO] encodings output path: '%s'" % encodings)
    print("[INFO] face detection method: '%s'" % encode_detection_method)
    # Update the encodings
    faceEncode.main(dataset, encodings, encode_detection_method)
    endTime = datetime.now()
    print("==> Encodings successfully updated on "+
        endTime.strftime("%Y-%m-%d at %H:%M:%S"))

    # Calculate the elapsed time to make the encodings
    elapsedTime = (endTime - startTime)
    print(f"[FINISHED] encoding time: {elapsedTime} ({elapsedTime.total_seconds()}s)")

    # Force reload of the encodings in the videoCamera object if it's not the
    # first startup run of the program (encodings are already loaded when the
    # camera object is created)
    if not onFirstRun:
        videoCamera.load_encodings()
    print("-"*60)


def liveFaceRecon(encodings, display, recon_detection_method):
    '''
    Performs the live face recognition.

        :param encodings: input path to serialized db of facial encodings (default: 'encodings.pickle').
        :param display: whether or not to display output frame to screen during live recognition (default: 1 (yes)).
        :param recon_detection_method: face detection model to use for live recognition: either 'hog' or 'cnn' (default: 'hog').
        :return The list of granted subject received from the live recognition module
    '''
    # python faceRecon.py
    #     --encodings encodings.pickle
    #     --display 0
    #     --recon-detection-method hog
    print("-"*60)
    print("Live recognition starting...")
    print("[INFO] encodings input path: '%s'" % encodings)
    print("[INFO] display frame: '%s'" % display)
    print("[INFO] face detection method: '%s'" % recon_detection_method)

    # Reset faceRecon variables to default and start facial recognition
    faceRecon.startup()
    videoCamera.doRecon = True
    # Check for recognized subject, return the list of the ones having access
    # granted, and stop facial recognition
    granted = faceRecon.accessControl()
    videoCamera.doRecon = False
    
    # granted = faceRecon.main(encodings, display, recon_detection_method)
    # granted = ['Javier_Soler_Macias_A20432537']
    print("-"*60)
    return granted


def accesslog(received_card_number, onDB, granted):
    '''
    Log for the door access. Keeps record of whether the attemp was successful
    or unsuccessful, and the reason for it in the latter case

        :param received_card_number: number of the card swiped at the door.
        :param onDB: boolean of whether or not the card number is on the list of accepted cards.
        :param granted: boolean of whether the access was granted or denied.
    '''
    # Save a different message depending if the user attempt was successful or
    # not
    if granted:
        with open("accesslog.txt", "a") as accesslogfile:
            print(f"Access granted on: {datetime.now()} "
                +f"for card ID '{received_card_number}'", 
                file=accesslogfile)
    elif (not granted) and onDB:
        with open("accesslog.txt", "a") as accesslogfile:
            print(f"Access refused on: {datetime.now()} "
                +f"for card ID '{received_card_number}' "
                +"(no face detection)", 
                file=accesslogfile)
    else: 
        with open("accesslog.txt", "a") as accesslogfile:
            print(f"Access refused on: {datetime.now()} "
                +f"for card ID '{received_card_number}' "
                +"(card ID not accepted)",  
                file=accesslogfile)


def waitForCard():
    '''
    Waits for an input of the access card swiping and, if accepted, launches 
    the face recognition module.
    '''
    time.sleep(5) # Delay for the encodings update process to start
    while True:
        global received_card_number
        received_card_number = input("Insert card number: ")
        # received_card_number = "1234"
        if received_card_number not in accepted_cards:
            print("Access refused!\n")
            accesslog(received_card_number, False, False)
        else:
            # Trigger the tread event to show the name of the person who
            # swipped the card
            thread_display_name.set()
            print("Card accepted. Please now place yourself in front of the "+
                "camera for face recognition")
            granted = liveFaceRecon(args["encodings"], args["display"],
                args["recon_detection_method"])
            if granted:
                print("[SUCCESS] you can now enter the lab")
                accesslog(received_card_number, True, True)
            else:
                accesslog(received_card_number, True, False)
            received_card_number = ""


############################### MAIN PROGRAM ###############################

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route("/")#, methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route("/admin/", methods=['GET', 'POST'])
def admin():
    # message = {'msg': 'Hello Admin!'}
    global encodings_process
    if request.method == 'POST':
        if "forceUpdate" in request.form:
            updateEncodings(args["dataset"], args["encodings"],
                args["encode_detection_method"])
        elif "startProcess" in request.form:
            if not encodings_process.is_alive():
                print("[INFO] Encodings update process started")
                encodings_process = multiprocessing.Process(
                    target = launchUpdateEncodings)
                encodings_process.start()
                onFirstRun = False
            else:
                print("[WARNING] Encodings update process already running")
        elif "stopProcess" in request.form:
            print("[INFO] Encodings update process stopped")
            encodings_process.terminate()
            onFirstRun = True
            time.sleep(0.1)
        elif "quit" in request.form:
            if encodings_process.is_alive():
                print("[INFO] stopping encodings update process before "
                    +"exiting...", end=" ")
                encodings_process.terminate()
                time.sleep(0.1)
                print("[DONE]")
            # cv2.destroyAllWindows()
            print("[FINISHED] program existing")
            shutdown_server()
            return 'Server shutting down...'
    elif request.method == 'GET':
        print("[INFO] admin website loaded")
    return render_template('index.html', userType="admin")#message=message, userType="admin")


@socketio.on('newMessage')
def updateWelcome():
    global updateWelcome_thread
    if not updateWelcome_thread.isAlive():
        updateWelcome_thread = updateWelcomeThread()
        updateWelcome_thread.setDaemon(True)
        updateWelcome_thread.start()


def gen(camera):
    '''
    The generator to display the video stream from the camera on the website.

        :param camera: the videoCamera object
    '''
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route('/video_feed2')
def video_feed2():
    # global videoCamera #### A ELIMINAR SI NO FUNCIONA
    # videoCamera = faceRecon.VideoCamera(args["encodings"],
    #         args["recon_detection_method"], doRecon)
    # if videoCamera.doRecon:
    global videoCam_started
    if not videoCam_started:
        videoCam_started = True
        videoCamera.start()
    return Response(gen(videoCamera),
        mimetype='multipart/x-mixed-replace; boundary=frame')
    # else:
        # return send_file("static/img/Facial-Recognition.png", mimetype='image/png', cache_timeout=0)


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

# @app.route('/post', methods = ["POST"])
# def post():
 
#     print(request.data)
#     return ''

# @app.route('/logo.png')
# def video_stream():
#     """The logo of the website"""
#     # img = get_main_image()
#     return send_file("static/img/Facial-Recognition.png")#, cache_timeout=0)

# @app.route("/members/<string:name>/")
# def getMember(name):
#     # return f"Hello {name}!"
#     return render_template('index.html',name=name)#</name>

# def flask_thread():
#     app.run(host='0.0.0.0', port=3000)

if __name__ == "__main__":
    # Initialize some variables
    accepted_cards = ['1234', '5678']
    received_card_number = ""

    # Logging config
    # logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="a+",
    #     format="%(levelname)-15s: %(asctime)-8s %(message)s")

    try:
        waitForCard_thread = threading.Thread(name='Card reader',
            target = waitForCard)
        waitForCard_thread.setDaemon(True)
        waitForCard_thread.start()
        print("[START] running main program, waiting for card reading")
        encodings_process = multiprocessing.Process(name='Encodings',
            target = launchUpdateEncodings)
        encodings_process.daemon = True
        encodings_process.start()
        onFirstRun = False
        
        # app.run(host='0.0.0.0', port=3000)#, debug=True)
        socketio.run(app, host='0.0.0.0', port=3000)#, debug=True)
        # flask_thread = threading.Thread(target=flask_thread)
        # flask_thread.setDaemon(True)
        # flask_thread.start()

        # while True:
        #     # Start/stop the encodings update process when `n` or `m` keys
        #     # are pressed, force encodings update with `f` key and exit the
        #     # program with the `q` key
        #     cv2.imshow('img',cv2.imread('static/img/Facial-Recognition.png'))
        #     key = cv2.waitKey(0)
        #     if key == ord("q"):    # Esc key to stop
        #         if encodings_process.is_alive():
        #             print("[INFO] stopping encodings update process before "
        #                 +"exiting...", end=" ")
        #             encodings_process.terminate()
        #             time.sleep(0.1)
        #             print("[DONE]")
        #         break
        #     elif key == ord("f"):
        #         updateEncodings(args["dataset"], args["encodings"],
        #             args["encode_detection_method"])
        #     elif key == ord("n"): #14: # CTRL + n
        #         print("[INFO] Encodings update process stopped")
        #         encodings_process.terminate()
        #         time.sleep(0.1)
        #     elif key == ord("m"): #13: # CTRL + m
        #         if not encodings_process.is_alive():
        #             print("[INFO] Encodings update process started")
        #             encodings_process = multiprocessing.Process(
        #                 target = launchUpdateEncodings)
        #             encodings_process.start()
        #         else:
        #             print("[WARNING] Encodings update process already running")
        # cv2.destroyAllWindows()
        # print("[FINISHED] program existing")
        # sys.exit(0)

    except KeyboardInterrupt:
        print("KeyboardInterrupt: main loop interrupted")
        # cv2.destroyAllWindows()
        encodings_process.terminate()
        time.sleep(0.1)
        sys.exit(1)