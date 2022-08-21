import json
import re
import imaplib
import email as ml


class IG_Account:
    '''Manage IG accounts credentials.'''
    
    def __init__(self) -> None:
        with open('ig_utils/data/IG_acc_data.json', 'r') as f:
            self.__accounts = json.load(f)
            self.__accounts_count = len(self.__accounts)
            
        self.__next_account_index = 0
            
            
    def get_account(self) -> 'dict[str, str] | False':
        '''Retrieve Instagram account user and password. Each call to this method returns a different IG account.

        Returns:
            dict[str, str]: user account data e.g. {'user': 'username', 'password': 'user_pass', 'email': 'email_addr', 'imap_pass', 'pass'}.
            False: all accounts available have already been used
        '''
        
        # Check if already used all accounts available
        if self.__next_account_index >= self.__accounts_count:
            return False
            
        IG_account = self.__accounts[self.__next_account_index]
        self.__next_account_index += 1
              
        return IG_account
    
    
    def get_accounts_count(self) -> int:
        """Get number of available IG accounts.

        Returns:
            int: Number of available IG accounts.
        """
        
        return self.__accounts_count
    
    
    def get_code_from_email(self, username: str, email: str, imap_pass: str):
        mail = imaplib.IMAP4_SSL("imap.mail.ru")
        mail.login(email, imap_pass)
        mail.select("inbox")
        result, data = mail.search(None, "(UNSEEN)")
        
        assert result == "OK", "Error1 during get_code_from_email: %s" % result
        
        ids = data.pop().split()
        
        for num in reversed(ids):
            mail.store(num, "+FLAGS", "\\Seen")  # mark as read
            result, data = mail.fetch(num, "(RFC822)")
            
            assert result == "OK", "Error2 during get_code_from_email: %s" % result

            msg = ml.message_from_string(data[0][1].decode())
            payloads = msg.get_payload()
            
            if not isinstance(payloads, list):
                payloads = [msg]
                
            code = None
            
            for payload in payloads:
                body = payload.get_payload(decode=True).decode()
                
                if "<div" not in body:
                    continue
                
                match = re.search(">([^>]*?({u})[^<]*?)<".format(u=username), body)
                
                if not match:
                    continue
                
                print("Match from email:", match.group(1))
                match = re.search(r">(\d{6})<", body)
                
                if not match:
                    print('Skip this email, "code" not found')
                    continue
                code = match.group(1)
                
                if code:
                    return code
        return False
