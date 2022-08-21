from pymongo import MongoClient
from datetime import datetime

class IG_Mongo():
    def __init__(self, server: str, local_conn: bool):
        
        if local_conn:
            conn_str = {'wix_app_prod': 'mongodb://wix:XugSfbUZ27@127.0.0.1:50001/DataDB?authSource=admin',
                        'main_app_prod': 'mongodb://data_user:data#db2018@127.0.0.1:50002/DataDB',
                        'main_app_staging': 'mongodb://data_user:mongoSTGdata#2020@127.0.0.1:50004/DataDB',
                        'verdane_prod': 'mongodb://data_user:mongoPRDdata#2021@127.0.0.1:50005/DataDB',
                        'verdane_staging': 'mongodb://data_user:mongoSTGdata#2020@127.0.0.1:50003/DataDB'}
        else:
            conn_str = {'wix_app_prod': 'mongodb://wix:XugSfbUZ27@wix-mongo.internal.net/DataDB?authSource=admin',
                        'main_app_prod': 'mongodb://data_user:data#db2018@mongodb.internal.net/DataDB',
                        'main_app_staging': 'mongodb://data_user:mongoSTGdata#2020@mongodb-stg.internal.net/DataDB',
                        'verdane_prod': 'mongodb://data_user:mongoPRDdata#2021@mongodb-verdane-prd.internal.net/DataDB',
                        'verdane_staging': 'mongodb://data_user:mongoSTGdata#2020@mongodb-verdane-stg.internal.net/DataDB'}
            
        #print(conn_str[server])
        client = MongoClient(conn_str[server])
        client = client['DataDB']
        
        self.db_client = client
        
        
    def log_error(self, message: str, error_message: str) -> None:
        self.db_client['logs'].insert_one({
            'status': 'Error',
            'message': message,
            'error_message': error_message,
            'at': 'Fleeksocial IG Scraper Microservice',
            'timestamp': datetime.now()
        })
