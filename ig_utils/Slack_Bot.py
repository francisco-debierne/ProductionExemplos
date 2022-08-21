from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class ErrorBot:
    
    def __init__(self, channel: str):
        self.channel = channel
        self.client_slack = WebClient(token='xoxb-1488958381536-3505389429747-1ydOnPk5rsBwpys8sIeJleAs')
        
    def send_message(self, text: str) -> str:
        try:
            response = self.client_slack.chat_postMessage(channel=self.channel, text=text)
            return response['ok']
        except SlackApiError as e:
            print(f"Got an error: {e.response['error']}")
 