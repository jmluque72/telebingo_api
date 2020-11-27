#!/usr/bin/env python

from gcm import GCM

# JSON request

API_KEY = "AIzaSyD-dcMsjsQsWbJ1tPwjsnMdwym79mE8xDU"

gcm = GCM(API_KEY, debug=True)

registration_ids = ["eABAUx6WYmM:APA91bGXkTTNNBBbgbZQJfHDBjyjnOpFYHuTSfO6yYBjNiJQxt9QcFTctmkg14g3RovR1q42LSXX-gfZccjxNYvL7lFxM6T2uFzKzM6BDpyD4JaBCqIyv9kopeYPnFxhy3tAmDRUyKqq"]

notif = dict(
    title="Awesome App Update",
    body="Tap here to start the update!", 
    icon="small_notification_icon", 
    color="#438CDE"
)

data = {
    "content_available" : True,
    "notification": notif,
    "data": {
        "type": 5
    }
}

response = gcm.json_request(registration_ids=registration_ids,
                            data=data,
                            #collapse_key='awesomeapp_update',
                            #restricted_package_name="gcm.play.android.samples.com.gcmquickstart",
                            priority='high',
                            delay_while_idle=False)
print response

# Successfully handled registration_ids
if response and 'success' in response:
    for reg_id, success_id in response['success'].items():
        print 'Successfully sent notification for reg_id {0}'.format(reg_id)

# Handling errors
if 'errors' in response:
    for error, reg_ids in response['errors'].items():
        # Check for errors and act accordingly
        if error in ['NotRegistered', 'InvalidRegistration']:
            # Remove reg_ids from database
            for reg_id in reg_ids:
                print "Removing reg_id: {0} from db".format(reg_id)
        else:
            print error

# Repace reg_id with canonical_id in your database
if 'canonical' in response:
    for reg_id, canonical_id in response['canonical'].items():
        print "Replacing reg_id: {0} with canonical_id: {1} in db".format(reg_id, canonical_id)
