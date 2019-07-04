'''
Retrieve the information needed for the app to work. This is:
    - infomation configured for the app in the Google API console under \
"Credentials" (Google OAuth Client ID): Google client ID, Google client \
secret, and authorized redirect URI.
    - the home URI of the app (to redirect after logout).
    - the login URI of the app (to redirect to after the login).
'''

import json

def loadJsonEnvFile(envFile):
    '''
    Load the JSON file containing the information for the app.

    :param `envFile`: the JSON file to be loaded.\n
    :return The `JSON data` loaded.
    '''
    try:
        with open(envFile, 'r') as json_file:
            json_text = json_file.read()
            return json.loads(json_text)
    except IOError as e:
        # Does not exist or no read permissions for the JSON access file
        print("\n[ERROR] Unable to open file "+str(envFile))
        sys.exit(1)


def getCliendID():
    '''
    Get from the JSON file the Google client ID configured for the app 
    in the Google API console under "Credentials" (Google OAuth Client ID).

    :return The client `ID`.
    '''
    return envData["id"]


def getClientSecret():
    '''
    Get from the JSON file the Google client secret configured for the app 
    in the Google API console under "Credentials" (Google OAuth Client ID).

    :return The client `secret`.
    '''
    return envData["secret"]


def getAuthRedirectURI():
    '''
    Get from the JSON file the authorized redirect URI configured for the app 
    in the Google API console under "Credentials" (Google OAuth Client ID).

    :return The `authorized redirect URI`.
    '''
    return envData["auth_redirect_URI"]


def getHomeURI():
    '''
    Get from the JSON file the home URI to which the app will have to redirect to
    after the logout.

    :return The `home URI`.
    '''
    return envData["home_URI"]


def getLoginURI():
    '''
    Get from the JSON file the URI to which the app will have to redirect to
    after the login.

    :return The `login URI`.
    '''
    return envData["login_URI"]

envFile = "google_auth.json"
envData = loadJsonEnvFile(envFile)
