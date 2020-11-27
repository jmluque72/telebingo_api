from bet import models

def run():
    users = models.UserProfile.objects.all()
    for i in users:
        test = [x.strip() for x in i.user.username.split('@')]
	if x != "gmail.com" and x != "hotmail.com" and x != "yahoo.com.ar" and x != "hotmail.com.ar" and x != "hotmail.es" and x != 'outlook.es' and x != 'outlook.com' and x != 'live.com.ar':
	    print(test)
