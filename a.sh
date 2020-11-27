api_key="AIzaSyD-dcMsjsQsWbJ1tPwjsnMdwym79mE8xDU"
reg_id="APA91bGUbVujvpR2LsqF40VVUW0aO9I9WAfG-K5-gvCibG7Auk3ZT83Mx1feokyoZ7YOl2C94C-YggV_S37l3HzER6fVJo0L61n41Hu0o0n_rzvni_oMeESRyzRaIXuR2bkP8zUMHjy0"
curl --header "Authorization: key=$api_key" --header Content-Type:"application/json" https://android.googleapis.com/gcm/send  -d "{\"registration_ids\":[\"$reg_id\"],\"data\":{\"code\":123}}"

