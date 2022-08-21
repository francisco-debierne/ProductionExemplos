from requests import Session, Response
import json

class IG_Session:
    """Manage IG sessions."""
    
    def __init__(self) -> None:
        self.clear_session()
    
    
    def set_proxy(self, username: str) -> bool:
        """Set up the proxy.
        
        Args:
            username (str): The username to link link

        Returns:
            bool: True if the proxy was set up successfully, False otherwise.
        """
        
        with open('ig_utils/data/IG_proxy_data.json', 'r') as f:
            proxy_data = json.load(f)
            proxy_data = proxy_data[username]
            proxy_url = f'socks5h://{proxy_data["username"]}:{proxy_data["password"]}@{proxy_data["geonode_dns"]}'
        
        self.proxy = {'https': proxy_url}

        try:
            self.session.proxies = self.proxy
            print(f'Proxy obj {self.session.proxies}')
            
            return True
        except ValueError:
            print("Error on proxies JSON")
            return False


    def get(self, *args, **kwargs) -> Response:
        """Send a GET HTTP request.

        Returns:
            Response: Instagram response object.
        """  
          
        try:
            return self.session.get(*args, **kwargs)
        except Exception:
            print("Connection error... trying again")
            return self.get(*args, **kwargs)


    def post(self, *args, **kwargs) -> Response:
        """Send a POST HTTP request.

        Returns:
            Response: Instagram response object.
        """
        
        try:
            return self.session.post(*args, **kwargs)
        except Exception:
            print("Connection error... trying again")
            return self.post(*args, **kwargs)


    def update_header(self, headers: 'dict[str, str]') -> None:
        """Update HTTP requests header.

        Args:
            headers (dict[str, str]): dictionary containing headers' field and value. Multiple headers are accepted.
        """
        
        self.session.headers.update(headers)
        
    
    def clear_session(self) -> None:
        """Clear all session data (cookies, headers, etc)."""
        
        self.session = Session()
        self.cookies = None
        self.proxy = {}
