'''
Read Wiegand codes of an arbitrary length, and return the string of bits.

This module can also be runned as an independent script.

Original script from the pigpio library:
https://abyz.me.uk/rpi/pigpio/python.html
'''

from argparse import RawTextHelpFormatter
from gooey import Gooey
import sys
import pigpio
import base64
import json
import requests
import argparse

## To disable the warning the following warning due to a self-signed certificate
################## TO BE CORRECTED ##################
# InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate
# verification is strongly advised.
# See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warningsInsecureRequestWarning)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class decoder:
    '''
    A class to read Wiegand codes of an arbitrary length.
    The code length and value are returned.

    EXAMPLE:
        #!/usr/bin/env python

        import time
        import pigpio
        import wiegand

        def callback(bitCount, value, cardBits):
            print(f"bitCount={bitCount}, value={value}, cardBits={cardBits}")

        pi = pigpio.pi()
        wiegand_card = wiegand.decoder(pi, 14, 15, callback)
        time.sleep(300)
        wiegand_card.cancel()
        pi.stop()
    '''

    def __init__(self, pi, gpio_0, gpio_1, callback, bit_timeout=5):
        '''
        Instantiate with the pi, gpio for 0 (green wire), the gpio for 1
        (white wire), the callback function, and the bit timeout in
        milliseconds which indicates the end of a code.

        The callback is passed the code length in bits and the value.
        '''
        self.pi = pi
        self.gpio_0 = gpio_0
        self.gpio_1 = gpio_1
        self.callback = callback
        self.bit_timeout = bit_timeout

        self.in_code = False

        self.pi.set_mode(gpio_0, pigpio.INPUT)
        self.pi.set_mode(gpio_1, pigpio.INPUT)

        self.pi.set_pull_up_down(gpio_0, pigpio.PUD_UP)
        self.pi.set_pull_up_down(gpio_1, pigpio.PUD_UP)

        self.cb_0 = self.pi.callback(gpio_0, pigpio.FALLING_EDGE, self._cb)
        self.cb_1 = self.pi.callback(gpio_1, pigpio.FALLING_EDGE, self._cb)

    def _cb(self, gpio, level, tick):
        '''
        Accumulate bits until both gpios 0 and 1 timeout.
        '''
        if level < pigpio.TIMEOUT:
            if self.in_code == False:
                self.bitCount = 1   # Number of bits read so far
                self.cardBits = ""  # Chain of bits read
                self.num = 0        # Decimal value of the bit chain

                self.in_code = True
                self.code_timeout = 0
                self.pi.set_watchdog(self.gpio_0, self.bit_timeout)
                self.pi.set_watchdog(self.gpio_1, self.bit_timeout)
            else:
                self.bitCount += 1
                # Left shift and add a "0" at the end (multiply by 2)
                self.num = self.num << 1
                self.cardBits += "0"

            if gpio == self.gpio_0:
                self.code_timeout = self.code_timeout & 2 # clear gpio 0 timeout
            else:
                self.code_timeout = self.code_timeout & 1 # clear gpio 1 timeout
                # Set the last bit to "1" (binary OR with "1")
                self.num = self.num | 1
                self.cardBits = self.cardBits[:-1]+"1"
        else:
            if self.in_code:
                if gpio == self.gpio_0:
                    self.code_timeout = self.code_timeout | 1 # timeout gpio 0
                else:
                    self.code_timeout = self.code_timeout | 2 # timeout gpio 1

                if self.code_timeout == 3: # both gpios timed out
                    self.pi.set_watchdog(self.gpio_0, 0)
                    self.pi.set_watchdog(self.gpio_1, 0)
                    self.in_code = False
                    self.callback(self.bitCount, self.num, self.cardBits)

    def cancel(self):
        '''
        Cancel the Wiegand decoder.
        '''
        self.cb_0.cancel()
        self.cb_1.cancel()


def processCode(bitCount, value, cardID_bits):
    global facilityCode, cardCode
    # Clean values from previous card reading
    facilityCode = 0
    cardCode = 0

    print(f"bitCount={bitCount}, value={value}, cardBits={cardID_bits}")
    cardID_binary_list = list(cardID_bits)
    if bitCount == 35:
        # Facility code = bits 3 to 14
        # Card code = bits 15 to 34
        # NOTE: array[a,b] goes from "a" to "b-1"!
        facilityCode = int(cardID_bits[2:14], 2)
        cardCode = int(cardID_bits[14:34], 2)
        print(f"FC = {facilityCode}, CC = {cardCode}") 
    elif bitCount == 26:
        # Facility code = bits 2 to 9
        # Card code = bits 10 to 25
        # NOTE: array[a,b] goes from "a" to "b-1"!
        facilityCode = int(cardID_bits[1:9], 2)
        cardCode = int(cardID_bits[9:25], 2)
        print(f"FC = {facilityCode}, CC = {cardCode}") 
    else:
        # More formats can be added here
        print("Unable to decode.")

    # Send a request to faceSec.py running program
    sendRequest(cardID_bits, facilityCode, cardCode)


def sendRequest(cardID_bits, facilityCode, cardCode):
    # Converting the cardID string of bits to bytes, and encode it in base64
    cardID_bits_bytes = base64.b64encode(str.encode(cardID_bits))
    facilityCode_bytes = base64.b64encode(str.encode(str(facilityCode)))
    cardCode_bytes = base64.b64encode(str.encode(str(cardCode)))
    # URL of the server, parsed from the arguments
    ipaddr = args["address"]
    port = str(args["port"])
    url = "https://" + ipaddr + ":" + port
    # Payload to send in JSON format
    payload = {
        "cardID": cardID_bits_bytes.decode(),
        "facilityCode": facilityCode_bytes.decode(),
        "cardCode": cardCode_bytes.decode()
        }
    print("Sending HTTP request...", end = " ")
    try:
        r = requests.post(url, json=payload, verify=False)
        print(r)
    except ValueError:
        print("[ERROR] exception raised while sending POST request")
    print("DONE")


@Gooey(program_name="Face Recognition", image_dir='.')
def argParser():
    # Construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    ap.add_argument("-a", "--address", type=str, required=True,
        help="IP address of the server where the card details will be sent ")
    ap.add_argument("-p", "--port", type=int, required=True,
        help="port where the destination server is running")
    global args
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    # Call the argument parser function
    argParser()

    # Initialize some variables
    facilityCode = 0    # Decoded facility code
    cardCode = 0        # Decoded card code

    # Start the Raspberry Pi and the decoding process
    try:
        pi = pigpio.pi()
        wiegand_card = decoder(pi, 14, 15, processCode)
    except ValueError:
        print("[ERROR] exception raised while instantiating the RPi. This "
            +"is probably to pigpio daemon not running.\n\tTo start it, run "
            +"'sudo pigpiod'")
        sys.exit(1)
    
    # Infinite loop to keep it running unless a KeyboardInterrupt is raised
    while True:
        try:
            pass
        except KeyboardInterrupt:
            print("KeyboardInterrupt: exiting program...", end = " ")
            wiegand_card.cancel()
            pi.stop()
            print("DONE")
            sys.exit(0)
