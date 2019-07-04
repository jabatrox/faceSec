import json
from datetime import datetime

def loadJsonAccessFile(accessFile):
    '''
    Load the JSON file containing the access data for admins and users.

    :param `accessFile`: the JSON file to be loaded.\n
    :return The `JSON data` loaded.
    '''
    try:
        with open(accessFile, 'r', encoding='utf-8-sig') as json_file:
            json_text = json_file.read()
            return json.loads(json_text)
    except IOError as e:
        # Does not exist or no read permissions for the JSON access file
        print("\n[ERROR] Unable to open file "+str(accessFile))
        sys.exit(1)


def reloadJsonAccessFile(accessFile):
    global accessData
    accessData = loadJsonAccessFile(accessFile)


def getAllGrantedCardIDs():
    granted_cards = []
    for user in accessData["granted"]:
        granted_cards.append(user["cardID"])
    return granted_cards


def getAllGrantedCWIDs():
    granted_CWIDs = []
    for user in accessData["granted"]:
        granted_CWIDs.append(user["CWID"])
    return granted_CWIDs


def getGrantedName(cardID):
    for user in accessData["granted"]:
        if user["cardID"] == cardID:
            return user["name"]


def setGrantedLastAccess(cardID, time):
    with open(accessFile, 'r', encoding='utf-8-sig') as json_file:
            json_text = json_file.read()
            data = json.loads(json_text)
    for user in data["granted"]:
        if user["cardID"] == cardID:
            timeHuman = time.strftime("%Y-%m-%d_%H%M%S.%f")
            user["last-access-human"] = timeHuman
            user["last-access-timestamp"] = datetime.timestamp(time)
    with open(accessFile, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4, sort_keys=True)
    reloadJsonAccessFile(accessFile)


def getCWIDFromCardID(cardID):
    for user in accessData["granted"]:
        if user["cardID"] == cardID:
            return user["CWID"]


# def isGrantedCWID(cwid):
#     for user in accessData["granted"]:
#         if user["CWID"] == cwid:
#             return True
#     return False


def getAllAdminIDs():
    admin_users = []
    for admin in accessData["admins"]:
        admin_users.append(admin["googleID"])
    return admin_users


def getAdminName(googleID):
    for admin in accessData["admins"]:
        if admin["googleID"] == googleID:
            return admin["name"]


def setAdminLastAccess(googleID, time):
    with open(accessFile, 'r', encoding='utf-8-sig') as json_file:
            json_text = json_file.read()
            data = json.loads(json_text)
    for admin in data["admins"]:
        if admin["googleID"] == googleID:
            timeHuman = time.strftime("%Y-%m-%d_%H%M%S.%f")
            admin["last-access-human"] = timeHuman
            admin["last-access-timestamp"] = datetime.timestamp(time)
    with open(accessFile, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4, sort_keys=True)
    reloadJsonAccessFile(accessFile)

accessFile = "access.json"
accessData = loadJsonAccessFile(accessFile)