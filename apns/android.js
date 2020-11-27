var gcm = require('android-gcm');

// initialize new androidGcm object 
var gcmObject = new gcm.AndroidGcm('AAAAaJoh_ns:APA91bEJLfZKl_I3ypN_C_nRQO4REVagSMivymoagYk4ISsSJJQKlsLfc9zFJ71uSuX6igGxVz41e7QDP4JPIOFIv4-VcVWMc41K38iICZwa_DSyJO6uK57lzqh3GmAB_usmTx3anHc7');

// create new message 
var message = new gcm.Message({
    registration_ids: [process.argv.slice(2)[2]],
    notification: {
        title: process.argv.slice(2)[0],
        body: process.argv.slice(2)[1]
    }
});

// send the message 
gcmObject.send(message, function(err, response) {console.log(response);});
