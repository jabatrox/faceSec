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
import logging
import base64

# from authlib.client import OAuth2Session
# import google.oauth2.credentials
# import googleapiclient.discovery

import faceEncode
import faceRecon
import accessmanager
import google_auth

# import functools


############################### ARGUMENT PARSER ###############################

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
ap.add_argument("-i", "--dataset",  type=str, default="images/known_people",
    help="path to input directory of face images.\ndefault: "+
        "'images/known_people'")
ap.add_argument("-u", "--unknown",  type=str, default="images/unknown_people",
    help="path to output directory of unknown face images.\ndefault: "+
        "'images/unknown_people'")
ap.add_argument("-e", "--encodings", type=str, default="encodings.pickle",
    help="path to serialized db of facial encodings "+
        "\ndefault: 'encodings.pickle'")
ap.add_argument("-t", "--encodings-update-time", type=str, default="01:00:00",
    help="time when the encoding will be updated daily "+
        "\ndefault: '01:00:00'")
ap.add_argument("-d", "--encode-detection-method", type=str, default="hog",
    help="face detection model to use for encodings: either 'hog' or 'cnn'"+
        "\ndefault: 'hog'")
ap.add_argument("-r", "--recon-detection-method", type=str, default="hog",
    help="face detection model to use for live recognition: either 'hog' "+
        "or 'cnn'\ndefault: 'hog'")
ap.add_argument("-c", "--count-recon", type=int, default=15,
        help="number of times a subject must be recogised before granting "+
        "access while using `hog` detection method (it will auto calculate "+
        "it for `cnn`. Test to adjust manually\ndefault: 15")
ap.add_argument("-L", "--local", type=int, default=0,
    help="whether or not to run the script in local computer (without web "+
        "server).\ndefault: '0' (no)")
ap.add_argument("-Y", "--display", type=int, default=1,
    help="whether or not to display output frame to screen during live "+
        "recognition. Used when the script is run in local (see option '-L')"+
        "\ndefault: '1' (yes)")
args = vars(ap.parse_args())


####################### FLASK AND SOCKET.IO INITIALIZER ######################

# Start and config Flask and Socket.io app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'This Is My Secret!'
app.register_blueprint(google_auth.app)
# app.config.update(
#     SESSION_COOKIE_SECURE=True,
#     SESSION_COOKIE_HTTPONLY=True,
#     SESSION_COOKIE_SAMESITE='Lax',
# )
socketio = SocketIO(app)

# To avoid seeing all the GET/POST requests on the terminal
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


############################## GENERAL VARIABLES #############################

# Some basic variables
received_card_number = ""   # Empty string to store the card number received
received_card_event = threading.Event() # Event for when a card number is
                                        # received
granted_cards = accessmanager.getAllGrantedCardIDs()# List of cards allowed
# granted_CWIDs = accessmanager.getAllGrantedCWIDs()  # List of CWIDs allowed
admin_users = accessmanager.getAllAdminIDs()        # List of admin Google IDs
# accessData = accessmanager.loadJsonAccessFile("access.json")

# Create the videoCamera object with the parsed arguments
if not args["local"]:
    videoCamera = faceRecon.VideoCamera(args["unknown"], args["encodings"],
                args["recon_detection_method"], int(args["count_recon"]))
    videoCam_started = False


####################### 'UPDATE WELCOME MESSAGE' CLASS #######################

updateWelcome_thread = threading.Thread()
# thread_stop_event = threading.Event()
thread_display_name = threading.Event()
thread_display_name.set()
class updateWelcomeThread(Thread):
    '''
    Updates the name of the person who has swiped the card (if any),
    otherwise it shows "Waiting for user...".
    '''
    def __init__(self):
        self.delay = 1
        super(updateWelcomeThread, self).__init__()
    def updateWelcomeGenerator(self):
        while True:
            # Default message for waiting
            msg = "Waiting for user..."

            # Update name only if it has changed (someone has swiped the card)
            if received_card_number in granted_cards:
                name = accessmanager.getGrantedName(received_card_number)
                msg = f"Hello {name}! Please now place yourself in front of "\
                    "the camera for face recognition"
            if thread_display_name.isSet():
                socketio.emit('newMessage', {'message': msg})
                # thread_display_name.clear()

            # Restore to default messsage when live recon is finised
            if not videoCamera.doRecon:
                thread_display_name.clear()
            # if videoCamera.doRecon:
            #     thread_display_name.set()
            time.sleep(self.delay)
    def run(self):
        self.updateWelcomeGenerator()


############################ FUNCTIONS DEFINITION ############################

def launchUpdateEncodings():
    '''
    Launch the scheduler to update the encodings at the specified time.
    '''
    try:
        print("[INFO] process to update encodings launched and running "+
            "in background. It will update encodings everyday at %s"
            % args["encodings_update_time"])
        schedule.every().day.at(args["encodings_update_time"]).do(updateEncodings,
            args["dataset"], args["encodings"], args["encode_detection_method"])
        while True:
            schedule.run_pending()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt: stopping encodings update process and "
            +"ending...", end=" ")
        schedule.clear()
        print("DONE")
        print("PROGRAM KILLED")


def updateEncodings(dataset, encodings, encode_detection_method):
    '''
    Performs the encodings update.

    :param `dataset`: path to input directory of face images to encode 
    (default: `'images/known_people'`).\n
    :param `encodings`: output path to serialized db of facial encodings 
    (default: `'encodings.pickle'`).\n
    :param `encode_detection_method`: face detection model to use for 
    encodings: either `'hog'` or `'cnn'` (default: `'hog'`).
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

    if not args["local"]:
        # Force reload of the encodings in the videoCamera object
        videoCamera.load_encodings()
    print("-"*60)


def liveFaceRecon(encodings, display, recon_detection_method, count_recon):
    '''
    Performs the live face recognition.

    :param `encodings`: input path to serialized db of facial encodings 
    (default: `'encodings.pickle'`).\n
    :param `display`: whether or not to display output frame to screen during 
    live recognition (default: `1` (yes)).\n
    :param `recon_detection_method`: face detection model to use for live 
    recognition: either `'hog'` or `'cnn'` (default: `'hog'`).\n
    :return The list of `granted` subject received from the live recognition 
    module
    '''
    # python faceRecon.py
    #     --encodings encodings.pickle
    #     --display 0
    #     --recon-detection-method hog
    print("-"*60)
    print("Live recognition starting...")
    print("[INFO] encodings input path: '%s'" % encodings)
    if args["local"]:
        print("[INFO] display frame: '%s'" % display)
    print("[INFO] face detection method: '%s'" % recon_detection_method)
    print("[INFO] times before recognition success (for HOG): '%s'" % count_recon)

    if not args["local"]:
        # Reset faceRecon variables to default and start facial recognition
        faceRecon.startup()
        videoCamera.doRecon = True
        # Check for recognized subject, return the list of the ones having access
        # granted, and stop facial recognition
        granted = faceRecon.accessControl(videoCamera.detection_method, 
            videoCamera.known_count_max)
        videoCamera.doRecon = False
    else: # Running in local
        granted = faceRecon.main(encodings, display, recon_detection_method,
            count_recon)
    # granted = ['Javier_Soler_Macias_A20432537']
    print("-"*60)
    return granted


def accesslog(received_card_number, onDB, faceRecognized, granted):
    '''
    Log for the door access. Keeps record of whether the attemp was successful
    or unsuccessful, and the reason for it in the latter case.

    :param `received_card_number`: number of the card swiped at the door.\n
    :param `onDB`: boolean of whether or not the card number is on the list 
    of accepted cards.\n
    :param `faceRecognized`: boolean of whether or not at least one face has  
    been recognized during the live recognition process.\n
    :param `granted`: boolean of whether the access was granted or denied.
    '''
    # Save a different message depending if the user attempt to access was 
    # successful or not
    if faceRecognized:
        if granted:
            with open("accesslog.txt", "a") as accesslogfile:
                print(f"Access granted on: {datetime.now()} "
                    +f"for card ID '{received_card_number}'", 
                    file=accesslogfile)
        else:
            with open("accesslog.txt", "a") as accesslogfile:
                print(f"Access refused on: {datetime.now()} "
                    +f"for card ID '{received_card_number}' "
                    +"(not recognized on camera)", 
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


def getCardNumber():
    '''
    Receive from the Raspberry Pi the number of the card that the user has 
    swiped on the reader.

    :return The `card number`.
    '''
    global received_card_number
    while True:
        # If a card number has been received (flag set to True), clear the
        # flag and return the card number
        if received_card_event.isSet():
            received_card_event.clear()
            return received_card_number


def waitForCard():
    '''
    Waits for an input of the access card swiping and, if accepted, launches 
    the face recognition module.
    '''
    time.sleep(5) # Delay for the encodings update process to start
    while True:
        global received_card_number
        received_card_number = getCardNumber()
        if received_card_number not in granted_cards:
            print("[ERROR] swiped card is not on the DB")
            print("[FAIL] access refused\n")
            accesslog(received_card_number, False, False, False)
        else:
            # Trigger the tread event to show the name of the person who
            # swipped the card on the website
            thread_display_name.set()
            name = accessmanager.getGrantedName(received_card_number)
            print(f"Card for {name} accepted. Please now place yourself in "+
                "front of the camera for facial recognition")
            granted = liveFaceRecon(args["encodings"], args["display"],
                args["recon_detection_method"], args["count_recon"])
            received_CWID = accessmanager.getCWIDFromCardID(received_card_number)
            # myindexes = [i for (i, cwid) in enumerate(granted) if cwid == received_CWID]
            if received_CWID in granted:
                print("[SUCCESS] face recognition and swiped card match")
                print("[SUCCESS] [ACCESS GRANTED] you can now enter the lab\n")
                accessmanager.setGrantedLastAccess(received_card_number, 
                    datetime.now())
                accesslog(received_card_number, True, True, True)
            elif granted and not received_CWID in granted:
                print("[ERROR] face recognition and swiped card don't match!")
                print("[FAIL] access refused\n")
                accesslog(received_card_number, True, True, False)
            elif not granted:
                print("[ERROR] no known subject has been recognized")
                print("[FAIL] access refused\n")
                accesslog(received_card_number, True, False, False)
            received_card_number = ""


################################ MAIN PROGRAM ################################

def shutdown_server():
    '''
    Shutdown the server.
    '''
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route("/")
def index():
    '''
    Main landing page for a non-logged in user.
    '''
    return render_template('index.html')


@app.route("/", methods=['POST'])
def receiveCardData():
    '''
    Receive data from the Raspberry Pi containing the information from card
    that the user has swiped on the reader..
    '''
    global received_card_number
    # Wait for a JSON in the request
    if request.is_json:
        # Get the JSON and obtain the data in bits
        data = request.get_json()
        cardID_encoded = data.get('cardID', None)
        facilityCode_encoded = data.get('facilityCode', None)
        cardCode_encoded = data.get('cardCode', None)

        # Decode the data and get the string of bits
        received_card_number = base64.b64decode(cardID_encoded).decode()
        facilityCode = base64.b64decode(facilityCode_encoded).decode()
        cardCode = base64.b64decode(cardCode_encoded).decode()

        infoMessage = "[INFO] swiped card with:\n"\
            f"\tID = {received_card_number}\n"\
            f"\tFC = {facilityCode}\n"\
            f"\tCC = {cardCode}"
        print(infoMessage)

        # Set the received_card_event flag to True, so the card number is sent
        # to the waitForCard() function
        received_card_event.set()
        return Response('{"result": "ok"}', mimetype='application/json')
    else:
        print("Nothing received")
        return Response('{"result": "error", "error": "JSON not found"}',
            status=500, mimetype='application/json')


@app.route("/admin/", methods=['GET', 'POST'])
def admin():
    '''
    Admin page, handling the button's requests. Only loads if the user is
    identified, otherwise it redirects to "/".
    '''
    if google_auth.is_logged_in():
        # Get information from the user logged in
        user_info = google_auth.get_user_info()

        # If the user is in de DB of admins, proceed to admin's website.
        # Otherwise, logout, display an error flash message and redirect to
        # root (general users' site)
        if user_info['id'] in accessmanager.getAllAdminIDs():
            # Update timestamp of last access for the logged in administrator
            accessmanager.setAdminLastAccess(user_info['id'], datetime.now())
            global encodings_process
            # Actions on each button pressed
            if request.method == 'POST':
                # Force encodings update with 'HOG'
                if "forceUpdateHOG" in request.form:
                    forced_encodings_HOG_process = multiprocessing.Process(
                        name='Encodings',
                        target = updateEncodings,
                        args=(args["dataset"], args["encodings"], "hog"))
                    forced_encodings_HOG_process.daemon = True
                    forced_encodings_HOG_process.start()
                    forced_encodings_HOG_process.join()
                    flash("Encodings succesfully updated with 'HOG'", 'success')
                # Force encodings update with 'CNN'
                elif "forceUpdateCNN" in request.form:
                    forced_encodings_CNN_process = multiprocessing.Process(
                        name='Encodings',
                        target = updateEncodings,
                        args=(args["dataset"], args["encodings"], "cnn"))
                    forced_encodings_CNN_process.daemon = True
                    forced_encodings_CNN_process.start()
                    forced_encodings_CNN_process.join()
                    flash("Encodings succesfully updated with 'CNN'", 'success')
                # Start the automatic encodings update process, if it's not 
                # already running
                elif "startProcess" in request.form:
                    if not encodings_process.is_alive():
                        message = "[INFO] Encodings update process is "\
                            "started and running"
                        flash(message[6:], 'info')
                        print(message)
                        encodings_process = multiprocessing.Process(
                            target = launchUpdateEncodings)
                        encodings_process.start()
                    else:
                        message = "[WARNING] Encodings update process is "\
                            "already running"
                        flash(message[9:], 'warning')
                        print(message)
                # Stop the automatic encodings update process, if it's not 
                # already stopped
                elif "stopProcess" in request.form:
                    if encodings_process.is_alive():
                        message = "[INFO] Encodings update process is stopped"
                        flash(message[6:], 'info')
                        print(message)
                        encodings_process.terminate()
                        time.sleep(0.1)
                    else:
                        message = "[WARNING] Encodings update process is "\
                            "been stopped"
                        flash(message[9:], 'warning')
                        print(message)
                # Shutdown the webserver and end the program
                elif "quit" in request.form:
                    if encodings_process.is_alive():
                        print("[INFO] stopping encodings update process "
                            +"before exiting...", end=" ")
                        encodings_process.terminate()
                        time.sleep(0.1)
                        print("DONE")
                    print("[FINISHED] program existing")
                    shutdown_server()
                    return '<h3>Server shutted down</h3>'
            elif request.method == 'GET':
                print("[INFO] admin website loaded")
            return render_template('index.html', userType="admin")
        else:
            print(f"[WARNING] Account '{user_info['name']}' with Google ID "
                +f"'{user_info['id']}' tried to access administrator's site "
                +f"on {datetime.now()}")
            flash("User not accepted (no admin rights)", 'danger')
            return redirect('/google/logout')
    flash("User not logged in. Please login to access administrator's site", 'danger')
    return redirect('/')


@socketio.on('newMessage')
def updateWelcome():
    '''
    Launch thread that will manage the real-time update of the welcome message
    shown to the user (default one and on card swipe)
    '''
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
        try:
            frame = camera.get_frame()
        except ValueError as error:
            print(error)
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route('/video_feed')
def video_feed():
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
        # return send_file("static/img/faceSec.png", mimetype='image/png', cache_timeout=0)


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also for not to cache the rendered page.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    # r.headers['X-Frame-Options'] = 'DENY'
    # r.headers['X-XSS-Protection'] = '1; mode=block'
    # r.headers['X-Content-Type-Options'] = 'nosniff'
    return r

if __name__ == "__main__":
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
        
        if not args["local"]: # Start as Fask/socket.io app, with webserver
            # app.run(host='0.0.0.0', port=3000)#, debug=True)
            context = ('certificates/cert-faceSec.pem', 'certificates/key-faceSec.pem')
            socketio.run(app, host='0.0.0.0', port=3000, ssl_context=context)
            #, processes=1, debug=True)
        else: # Run in local
            print("Script running in local")
            import cv2

            while True:
                # Start/stop the encodings update process when `n` or `m` keys
                # are pressed, force encodings update with `f` key and exit the
                # program with the `q` key
                cv2.imshow('img',cv2.imread('static/img/faceSec.png'))
                key = cv2.waitKey(0)
                if key == ord("q"):    # Esc key to stop
                    if encodings_process.is_alive():
                        print("[INFO] stopping encodings update process before "
                            +"exiting...", end=" ")
                        encodings_process.terminate()
                        time.sleep(0.1)
                        print("DONE")
                    break
                elif key == ord("f"):
                    updateEncodings(args["dataset"], args["encodings"],
                        args["encode_detection_method"])
                elif key == ord("n"): # 14 = CTRL + n ?
                    print("[INFO] Encodings update process stopped")
                    encodings_process.terminate()
                    time.sleep(0.1)
                elif key == ord("m"): # 13 = CTRL + m ?
                    if not encodings_process.is_alive():
                        print("[INFO] Encodings update process started")
                        encodings_process = multiprocessing.Process(
                            target = launchUpdateEncodings)
                        encodings_process.start()
                    else:
                        print("[WARNING] Encodings update process already running")
            cv2.destroyAllWindows()
            print("[FINISHED] program existing")
            sys.exit(0)

    except KeyboardInterrupt:
        print("KeyboardInterrupt: main loop interrupted")
        if args["local"]:
            cv2.destroyAllWindows()
        encodings_process.terminate()
        time.sleep(0.1)
        sys.exit(1)
