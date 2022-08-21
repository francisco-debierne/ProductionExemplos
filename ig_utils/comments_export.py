import csv
import json
from datetime import datetime

import pandas as pd

class CommentsExport:

    def __init__(self):
        pass

    def format_csv(self, filename):
        comments = pd.read_json('exports/' + filename + '.json')
        comments = comments['comments']
        for comment in comments:
            comment['timestamp'] = dt_object = datetime.fromtimestamp(comment['timestamp'])
            if '\n' in comment['text']:
                comment['text'] = comment['text'].replace('\n', '')
        with open('exports/' + filename + '.csv', "w", newline="", encoding='UTF8') as f:
            title = "timestamp,author_username,text".split(",")  # quick hack
            cw = csv.DictWriter(f, title, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
            cw.writeheader()
            cw.writerows(comments)
        #comments.to_csv('exports/' + filename + '.csv', index=None, columns=['timestamp', 'author_username', 'text'])


ce = CommentsExport()
ce.format_csv('CYh9fvjs5ps')