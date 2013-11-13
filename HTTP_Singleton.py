import sys, os
import datetime
import collections
import httplib2, urllib, json
import time

import util



class GMT_timezone(datetime.tzinfo):
    def dst(self, dt):
        return datetime.timedelta(minutes=0)
        
    def tzname(self, dt):
        return "GMT"
        
    def utcoffset(self, dt):
        return datetime.timedelta(minutes=0)


'''
Verbosity levels
1)

2)

3)
request response
error_wwait interval

'''
class HTTP_Singleton(object):
    _instance = None
    
    def __new__(self, *args, **kwargs):
        if not self._instance:
            self._instance = super(HTTP_Singleton, self).__new__(self, *args, **kwargs)
            
            certificates_file = ca_certs=os.path.join(os.path.dirname(__file__), 'certs','Guildwars2_Certificats.txt')       
            self._client = httplib2.Http(ca_certs=certificates_file)
            self._session_id = None
            self._session_valid_thru = datetime.datetime.now(GMT_timezone())
            self._error_wait_time = datetime.timedelta(seconds=5)
        return self._instance
    
    
    def request(self, *args, **kwargs):
        verbosity = kwargs.pop('verbosity', 0)
        if datetime.datetime.now(GMT_timezone()) >= self._session_valid_thru:
            self.authenticate(verbosity = verbosity)

        
            
        response, content = self._client.request(*args, **kwargs)

        if verbosity >= 3:
            util.STDERR.write(str(response.status) + " for "+args[0]+"\n")
        
        if response.status == 200 and self._error_wait_time.seconds >= 5: 
            self._error_wait_time += datetime.timedelta(seconds=-5) # bring down the error wait for ever successfull request
        
        if response.status == 401:
            # clear connection and reauth
            self._session_id = None
            self._session_valid_thru = datetime.datetime.now(GMT_timezone()) - datetime.timedelta(seconds=1)
            self.authenticate()

            kwargs['headers'] = {'Cookie':"s="+self._session_id}
            
            response, content = self._client.request(*args, **kwargs)

        if response.status >= 500:
            start = datetime.datetime.now()
            now = start
            time.sleep(self._error_wait_time.seconds)
            unnamed_timer1 = 1
            while (response.status >= 500 and (now - start).seconds < 120):
                time.sleep(unnamed_timer1)
                response, content = self._client.request(*args, **kwargs)
                now = datetime.datetime.now()
                unnamed_timer1 *= 2
            
            self._error_wait_time = (now - start)
            if verbosity >= 3:
                util.STDERR.write("Now waiting " +str(self._error_wait_time.seconds)+ " seconds\n")
            
        
        if response.status >= 400:
            raise IOError(response.status)
        
        return (response, content)
    
    
    def authenticate(self, *args, **kwargs):
        if datetime.datetime.now(GMT_timezone()) < self._session_valid_thru:
            return #old session_id is still valid

        verbosity = kwargs.pop('verbosity', 0)
        if verbosity >= 1:
            util.STDERR.write("Authenticating "+str(util.account_email)+"\n")
        
        # Setup the request
        url = "https://account.guildwars2.com" + "/login"
        data = {'email':util.account_email, 'password':util.account_password}
        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Referer': "https://account.guildwars2.com/login",
        }

        # httplib2 does not accept cookies from redirects
        # Must manualy parse
        self._client.follow_redirects = False
        
        # Make the request
        response, content = self._client.request(url, "POST", headers=headers, body=urllib.urlencode(data))
        if response.status != 303:
            raise IOError(response.status)
        
        
        # Pull out cookies
        # look into 'Cookie' module
        if response.has_key('set-cookie'):
            cookies = response['set-cookie']
            #cookies = 
            session = cookies.split(';')[0].split('=')[1]
            expiry = cookies.split(';')[1].split('=')[1]
            
            self._session_id = session
            self._session_valid_thru = datetime.datetime.strptime(expiry, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=GMT_timezone())
        else:
            self._session_id = None
            self._session_valid_thru = datetime.datetime.now(GMT_timezone())

        
        # return redirect following to the default state
        self._client.follow_redirects = True
