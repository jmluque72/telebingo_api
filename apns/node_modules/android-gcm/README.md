# Android GCM Client for Node.js

A simple interface for Google Cloud Messaging (GCM) in Node.js


## Installation
```bash
$ npm install android-gcm
```

## Usage

#### Simplest Usage
```js
var gcm = require('android-gcm');

// initialize new androidGcm object
var gcmObject = new gcm.AndroidGcm('API_KEY');

// create new message
var message = new gcm.Message({
    registration_ids: ['x', 'y', 'z'],
    data: {
        key1: 'key 1',
        key2: 'key 2'
    }
});

// send the message
gcmObject.send(message, function(err, response) {});

```

#### Message Class
```js
// You can initialize the message object as an empty object and alter it later.
var message = new gcm.Message();

// add new value to data object (as key-value)
message.addNew_Data('key3', 'key 3');

// OR add new value(s) to data object
message.addNew_DataObject({
    key3: 'key 3',
    key4: 'key 4'
});

// add new registration_id (device token)
message.addNew_RegistrationId('a');
message.addNew_RegistrationId('b');

// OR add many registration ids at once
message.addNew_RegistrationIdArray(['a', 'b', 'c']);

// other message options
message.collapse_key = 'urgent_news';
message.delay_while_idle = false; // The message should not be sent immediately if the device is idle.
message.time_to_live = 11; // How long (in seconds) the message should be kept on GCM storage if the device is offline.
message.dry_run = false; // If true, test the request without actually sending a message
```
For full list of message options, check payload table [here](http://developer.android.com/google/gcm/server.html).


#### Debugging Requests to GCM Server
To debug requests made to GCM server, set `DEBUG=https`.


## Bugs, Issues and Feature Requests
[Here](https://github.com/MuhammadReda/android-gcm/issues)

## License
[MIT](http://opensource.org/licenses/MIT)
