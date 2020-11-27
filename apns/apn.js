"use strict";

const apn = require('apn');
 
let options = {
  token: {
    key: "/home/ubuntu/proyects/loteriamovil/src/apns/AuthKey_JYR99W8N24.p8",
    // Replace keyID and teamID with the values you've previously saved.
    keyId: "JYR99W8N24",
    teamId: "4ZMBR9L67J"
  },
  production: true
};


let apnProvider = new apn.Provider(options);

// Replace deviceToken with your particular token:
let deviceToken =process.argv.slice(2)[0];
console.log(deviceToken);
 
// Prepare the notifications
let notification = new apn.Notification();
notification.expiry = Math.floor(Date.now() / 1000) + 24 * 3600; // will expire in 24 hours from now
notification.badge = 0;
notification.alert = {"title": process.argv.slice(2)[1], "body": ""}
notification.payload = JSON.parse(process.argv.slice(2)[2]);
 
// Replace this with your app bundle ID:
notification.topic = "com.poten.agenciasc";
apnProvider.send(notification, deviceToken).then( result => {
	// Show the result of the send operation:
 	console.log(JSON.stringify(result));
 });
 

// Close the server
apnProvider.shutdown();
setTimeout(function() {
process.exit(0)
}, 3000);

