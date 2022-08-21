import json
from traceback import format_exc
import requests
import sys
import time
from requests import Response
from hashlib import md5
from typing import Literal, Union

from .constants import BASE_URL, LOGIN_URL, CHROME_WIN_UA, STORIES_UA, LOGOUT_URL, MAX_RETRY_DELAY, \
                        RETRY_DELAY, MAX_RETRIES,  CONNECT_TIMEOUT
from .IG_Account import IG_Account
from .IG_Session import IG_Session
from .IG_Mongo import IG_Mongo
from .Slack_Bot import ErrorBot


class IG_Connection(IG_Account, IG_Session):
    """Manages the connection to Instagram"""    
    
    def __init__(self, rhx_gis='') -> None:
        print('CONNECTION INIT')
        IG_Account.__init__(self)
        IG_Session.__init__(self)
        
        self.login = self.get_account()
        self.set_proxy(self.login['user'])
        
        self.error_bot = ErrorBot('scrapper-errors')
        
        self.rhx_gis = rhx_gis
        self.logged_in = False


    def authenticate_with_login(self, mongo_conn: IG_Mongo = None, rotate: bool = True,):
        """Logs in to instagram. Each method call uses a different account."""
        
        # Used all accounts available
        if not self.login:
            return False
        
        if rotate:
            # Change account 
            self.login = self.get_account()
            self.set_proxy(self.login['user'])
        
        print(f'Current account {self.login}')
        print(f'Login status: {self.logged_in}')

        
        if not self.logged_in:
            try:
                self.update_header({'Referer': BASE_URL, 'user-agent': STORIES_UA})
                print(1)
                
                req = self.get(BASE_URL)
                print(req)
                
                self.update_header({'X-CSRFToken': req.cookies['csrftoken']})
                print(2)
                
                login_data = {'username': self.login['user'], 'password': self.login['password']}
                login = self.post(LOGIN_URL, data=login_data, allow_redirects=True)
                print(login)
                
                self.update_header({'X-CSRFToken': login.cookies['csrftoken']})
                print(3)
                
                self.cookies = login.cookies
                print(4)
                
                login_text = json.loads(login.text)
                print(login_text)
                
                if login_text.get('authenticated') and login.status_code == 200:
                    self.logged_in = True
                    self.update_header({'user-agent': CHROME_WIN_UA})
                    self.rhx_gis = ""
                    print(f'Authentication Successfully for user {self.login["user"]}')
                    
                    return login_text, "Authentication successfully"
                else:
                    if 'checkpoint_url' in login_text:
                        print('Login Challenge')
                        checkpoint_url = login_text.get('checkpoint_url')
                        resp = self.__login_challenge(checkpoint_url)
                        
                        if resp == 'error':
                            if mongo_conn is not None:
                                
                                mongo_conn.log_error(f'Login failed for user {self.login["user"]}', 'Login challenge failed')
                            
                            self.error_bot.send_message(f'Login challenge failed for user {self.login["user"]}')
                            print('Error: trying with another account')
                            self.logout()
                            return self.authenticate_with_login()
                        
                        return resp, "Login challenge"

                    else:
                        if mongo_conn is not None:
                            mongo_conn.log_error(f'Error in login for user {self.login["user"]}', 'Checkpoint url not found')
                            
                        self.error_bot.send_message(f'Checkpoint url not found for user {self.login["user"]}')
                        print(f'Error in login for user {self.login["user"]}: Checkpoint_url not found')
                        print('Trying with another account')
                        self.logout()
                        return self.authenticate_with_login()
                    
            except Exception as e:
                if mongo_conn is not None:
                    mongo_conn.log_error(f'Error in login procces for user {self.login["user"]}', format_exc())
                    
                self.error_bot.send_message(f'Error in login process for user {self.login["user"]}')
                print(f'Error in login process for user {self.login["user"]}')
                print(e)
                self.logout()
                return self.authenticate_with_login()


    # TODO: IMPLEMENT AUTO COLLECT OF EMAIL CODE
    def __login_challenge(self, checkpoint_url: str) -> Literal["ok", "error"]:
        """Handles the IG login code challenge 
        
        Args:
            checkpoint_url (str): The url for the checkpoint returned by IG

        Returns:
            'ok': If the login challenge was successful
            'error': If the login challenge failed
        """   
        
        self.update_header({'Referer': BASE_URL})
        req = self.get(BASE_URL[:-1] + checkpoint_url)
        
        self.update_header({'X-CSRFToken': req.cookies['csrftoken'], 'X-Instagram-AJAX': '1', 'Referer': BASE_URL[:-1] + checkpoint_url})
        
        #mode = int(input('Choose a challenge mode (0 - SMS, 1 - Email): '))
        
        # Choose email code option
        mode = 1
        
        challenge_data = {'choice': mode}
        challenge = self.post(BASE_URL[:-1] + checkpoint_url, data=challenge_data, allow_redirects=True)
        
        self.update_header({'X-CSRFToken': challenge.cookies['csrftoken'], 'X-Instagram-AJAX': '1'})
        
        time.sleep(5)
        
        if self.login['imap_pass']:
            code = self.get_code_from_email(self.login['user'], self.login['email'], self.login['imap_pass'])
                    
            if not code:
                return 'error'
        else:
            code = input('Enter code received: ')
            
        code_data = {'security_code': int(code)}
        print(code_data)
        
        code = self.post(BASE_URL[:-1] + checkpoint_url, data=code_data, allow_redirects=True)
        
        self.update_header({'X-CSRFToken': code.cookies['csrftoken']})
        self.cookies = code.cookies
        code_text = json.loads(code.text)
        
        if code_text.get('status') == 'ok':
            self.logged_in = True
            print('User logged in')
            
            return 'ok'
        else:
            print(f'Error in login for user {self.login["user"]}')
            return 'error'


    def logout(self) -> bool:
        """Logs out of instagram. Clears all session data"""
        
        if self.logged_in:
            try:
                logout_data = {'csrfmiddlewaretoken': self.cookies['csrftoken']}
                self.post(LOGOUT_URL, data=logout_data)
                
                self.logged_in = False
                print('User logged out')
                
                self.clear_session()
                self.rhx_gis = ''
                
                return True
            except requests.exceptions.RequestException:
                print("Failed to log out")
                
                return False
            
    
    def get_ig_gis(self, rhx_gis: str, params: str) -> str:
        """Format x-instagram-gis header value

        Args:
            rhx_gis (str): First part of x-instagram-gis
            params (str): Second part of x-instagram-gis

        Returns:
            str: md5 hashed string
        """
        
        data = rhx_gis + ":" + params
        
        if sys.version_info.major >= 3:
            return md5(data.encode('utf-8')).hexdigest()
        else:
            return md5(data).hexdigest()


    def update_ig_gis_header(self, params: str) -> None:
        """Update x-instagram-gis header

        Args:
            params (str): Header parameters
        """
        
        self.update_header({'x-instagram-gis': self.get_ig_gis(self.rhx_gis, params)})
        
    
    def safe_get(self, *args, **kwargs) -> Union[int, Response]:
        """Send GET request to IG. If in case of a RequestException, retry send request again

        Returns:
            int: if in case of a 400 family HTTP code
            Response: if in case of a successful response
        """
        
        retry = 0
        retry_delay = RETRY_DELAY
        url = ''
        
        while True:
            try:
                response = self.get(timeout=CONNECT_TIMEOUT, cookies=self.cookies, *args, **kwargs)
                
                if response.status_code == 404:
                    print('404 not found')
                    return 404
                elif response.status_code == 429:
                    print('429 Too many requests')
                    return 429

                return response
            except (KeyboardInterrupt):
                print('Keyboard Interrupt')
                raise
            except requests.exceptions.RequestException as e:
                print(e)
                if 'url' in kwargs:
                    url = kwargs['url']
                elif len(args) > 0:
                    url = args[0]
                if retry < MAX_RETRIES:
                    self.sleep(retry_delay)
                    retry_delay = min(2 * retry_delay, MAX_RETRY_DELAY)
                    retry = retry + 1
                    continue
                else:
                    keep_trying = self._retry_prompt(url, repr(e))
                    if keep_trying:
                        retry = 0
                        continue
                    elif not keep_trying:
                        return
                raise
            
            
    def _retry_prompt(self, url: str, exception_message: str) -> Union[bool, None]:
        """Show prompt to decide whether retry the unsuccessful request or not in case of repeated exceptions

        Args:
            url (str): url of the unsuccesfull request
            exception_message (str): current exception message

        Returns:
            bool: True if user decided to rety or False if user decided to ignore
            None: if user decided to abort
        """        
        """Show prompt and return True: retry, False: ignore, None: abort"""
        
        answer = input('Repeated error {0}\n(A)bort, (I)gnore, (R)etry or retry (F)orever?'.format(exception_message))
        if answer:
            answer = answer[0].upper()
            if answer == 'I':
                print('The user has chosen to ignore {0}'.format(url))
                return False
            elif answer == 'R':
                return True
            elif answer == 'F':
                print('The user has chosen to retry forever')
                return True
            else:
                print('The user has chosen to abort')
                return None
            
    
    def sleep(self, secs: int) -> None:
        min_delay = 1
        for _ in range(secs // min_delay):
            time.sleep(min_delay)
        time.sleep(secs % min_delay)

