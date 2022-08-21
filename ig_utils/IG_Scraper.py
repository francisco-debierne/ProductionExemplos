import json
import re
import time
from traceback import format_exc
import boto3
import os
import requests
import tqdm as tqdm
from typing import Union
from random import randint
from urllib.parse import urlparse

from .constants import BASE_URL, QUERY_MEDIA_VARS, QUERY_MEDIA, USER_URL, VIEW_MEDIA_URL, QUERY_COMMENTS_VARS, \
    QUERY_COMMENTS, QUERY_FOLLOWINGS_VARS, QUERY_FOLLOWINGS, QUERY_FOLLOWERS_VARS, QUERY_FOLLOWERS
    
from .IG_Connection import IG_Connection
from .IG_Mongo import IG_Mongo
from .Slack_Bot import ErrorBot

class IG_Scraper:

    def __init__(self):
        self.s3_bucket_name = '1nf-bucket'
        self.s3_key_id = 'AKIA2R3HYAISQOQKLN5E'
        self.s3_key_secret = '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'
        self.s3_default_region = 'eu-west-1'
        self.s3_default_acl = 'public-read'
        
        self.error_bot = ErrorBot('scrapper-errors')
        
        self.ig_connection = IG_Connection()
        self.ig_connection.authenticate_with_login(rotate=False)

        self.mongo = None
        self.virtual_database = {}

        print(self.ig_connection.login)
        time.sleep(5)


    def scrape(self, parameter: str, endpoint: str):
        """Crawls through and downloads user's media
        
        Args:
            parameter (str): username or post shortcode
            endpoint (str): what to scrape
        """

        #self.ig_connection.authenticate_with_login(self.mongo, rotate=False)
        user = {}
        #virtual_db_key = endpoint + parameter
        
        # If the requested data have already been colleted, just return it. This way we save requests
        #if virtual_db_key in self.virtual_database.keys():
        #    return self.virtual_database[virtual_db_key]
        
        if endpoint != 'comments' and endpoint != 'post':
            
            # If requested IG user have already been checked
            if 'check_user_' + parameter in self.virtual_database.keys():
                user = self.virtual_database['check_user_' + parameter]
            else:
                user = self._check_user(parameter)
                self.virtual_database['check_user_' + parameter] = user
            
            # this means that we reached the requests limit for the current IP
            if user == 'Error' or user == 'Too many requests':
                print(f'message: {user}')
                print('Current user limit reached, loading next user.')
                
                self.ig_connection.logout()
                
                if self.ig_connection.authenticate_with_login(self.mongo) == False:
                    self.error_bot.send_message('No more IG accounts available for use')
                    self.mongo.log_error('No more IG account available', 'No IG account available for use')
                    return 'Error: no more users available'        
                
                time.sleep(10)
                return self.scrape(parameter, endpoint)
            
            elif user == "Invalid":
                return 'User is Invalid. Check if user exists'
            
            elif user == "Private":
                return 'User account is private. Cannot retrieve data'


        # check if requested data has already been scraped
        #if virtual_db_key in self.virtual_database.keys():
        #    return self.virtual_database[virtual_db_key]
        
        time.sleep(9)   

        if endpoint == 'user':

            profile = self.get_profile_info(parameter)
            #self.virtual_database[virtual_db_key] = profile

            return profile
        
        elif endpoint == 'posts':

            posts = {'posts': self.get_media(user)}
            #self.virtual_database[virtual_db_key] = posts
            
            return posts

        elif endpoint == 'post':

            response = self.__get_media_json(parameter)
            post = self.get_node_info(response, post_json = True)

            #self.virtual_database[virtual_db_key] = post

            return post
        
        elif endpoint == 'comments':
            
            comments = {"comments": self.get_post_comments(parameter)}
            #self.virtual_database[virtual_db_key] = comments

            return comments
        
        elif endpoint == 'followers':

            followers = {'follower_list': self.get_user_followers(user)}
            #self.virtual_database[virtual_db_key] = followers

            return followers
        
        elif endpoint == 'following':
            
            following = {'following_list': self.get_user_following(user)}
            #self.virtual_database[virtual_db_key] = following

            return following

        elif endpoint == 'audience':
            
            audience = self.get_user_audience(user)
            #self.virtual_database[virtual_db_key] = audience

            return audience
        else:
            return "No data for that endpoint"


    def get_media(self, user: str) -> 'list[dict]':
        """Scrapes latest posts from user

        Args:
            user (str): target username

        Returns:
            list[dict]: list of latest posts
        """        

        if type(user) is str:
            return f"Invalid user {user}"

        username = user['username']
        items = []
        
        for item in tqdm.tqdm(self.query_media_gen(user), desc='Searching {0} for posts'.format(username), unit='media', disable=False):          
            
            items.append(item)

        return items


    def get_profile_info(self, username: str) -> Union[None, str, dict]:
        """Scrapes information about an IG profile

        Args:
            username (str): profile username

        Returns:
            None: If didn't get a response from IG
            str: If an error occurred
            dict: user data
        """
        
        url = USER_URL.format(username)
        resp = self.get_json(url)
        
        if type(resp) == int:
            return 'Blocked' if resp == 429 else 'Invalid'
        
        elif not resp:
            print(f'Error getting user info for {username}')
            return None

        info = {}

        try:
            info = json.loads(resp)
            user_info = info['graphql']['user']
        except Exception:
            self.error_bot.send_message(f'Error collection profile information for {username}')
            self.mongo.log_error(f'Error collection profile information for {username}', format_exc())
            return f'Error in JSON'

        try:
            profile_info = {
                'biography': user_info['biography'],
                'followers_count': user_info['edge_followed_by']['count'],
                'following_count': user_info['edge_follow']['count'],
                'full_name': user_info['full_name'],
                'id': user_info['id'],
                'is_business_account': user_info['is_business_account'],
                'is_joined_recently': user_info['is_joined_recently'],
                'is_private': user_info['is_private'],
                'posts_count': user_info['edge_owner_to_timeline_media']['count'],
                'profile_pic_url': user_info['profile_pic_url'],
                'external_url': user_info['external_url'],
                'business_email': user_info['business_email'],
                'business_phone_number': user_info['business_phone_number'],
                'business_category_name': user_info['business_category_name']
            }

        except (KeyError, IndexError, StopIteration):
            self.error_bot.send_message(f'Failed to build profile for {username}')
            self.mongo.log_error(f'Failed to build profile for {username}', format_exc())
            return f'Error failed to build {username} profile info'

        item = {'username': username, 'info': profile_info}

        return item


    def query_media_gen(self, user: str, end_cursor: str='') -> 'list[dict]':
        """Query latest posts of an IG profile
        
        Args:
            id (str): profile shortcode
            end_cursor (str, optional): Defaults to ''
            
        Retuns:
            list[dict]: information of the latest posts
        """
        
        """Generator for media."""
        
        media, end_cursor = self.__query_media(user['id'], end_cursor)

        return media


    def __query_media(self, id: str, end_cursor: str='') -> Union[None, list, str]:
        """Query latest posts of an IG profile
        
        Args:
            id (str): profile shortcode
            end_cursor (str, optional): Defaults to ''

        Returns:
            None: If didn't get a response from IG
            (list, str): list with the posts information and a string containing the end_cursor
        """        
        
        params = QUERY_MEDIA_VARS.format(id, end_cursor)
        self.ig_connection.update_ig_gis_header(params)
        resp = self.get_json(QUERY_MEDIA.format(params))
        
        if resp is not None:
            payload = json.loads(resp)['data']['user']

            try:
                if payload:
                    container = payload['edge_owner_to_timeline_media']
                    nodes = self._get_nodes(container)
                    end_cursor = container['page_info']['end_cursor']
                    
                    return nodes, end_cursor
            except Exception:
                self.error_bot.send_message(f'Error colleting posts information for profile id {id}')
                self.mongo.log_error(f'Error colleting posts information for profile id {id}', format_exc())

        return None, None


    def get_json(self, *args, **kwargs) -> Union[int, None, str]:
        """Retrieve Instagram JSON for a given URL

        Returns:
            Union[int, None, str]: _description_
            int: If IG returned a 400 family HTTP code
            None: If didn't get a response from IG
            str: response JSON
        """        
        
        resp = self.ig_connection.safe_get(*args, **kwargs)
        
        if resp == 404:
            return 404
        elif resp == 429:
            self.error_bot.send_message('Blocked by Instagram')
            self.mongo.log_error('Blocked by Instagram', 'Instagram returned the 429 code (too many requests)')
            return 429
        elif resp is not None:
            return resp.text
        else:
            return


    def deep_get(self, dict, path):
        def _split_indexes(key):
            split_array_index = re.compile(r'[.\[\]]+')  # ['foo', '0']
            return filter(None, split_array_index.split(key))

        ends_with_index = re.compile(r'\[(.*?)\]$')  # foo[0]

        keylist = path.split('.')

        val = dict

        for key in keylist:
            try:
                if ends_with_index.search(key):
                    for prop in _split_indexes(key):
                        if prop.isdigit():
                            val = val[int(prop)]
                        else:
                            val = val[prop]
                else:
                    val = val[key]
            except (KeyError, IndexError, TypeError):
                return None

        return val


    def _get_nodes(self, container: dict) -> list:
        """Iterates oves a posts JSON returned by IG and return detailed information about for the lastest 4 posts

        Args:
            container (dict): posts container

        Returns:
            list: information of the lastest 4 posts
        """        
        
        nodes = []
        
        for node in container['edges']:
            nodes.append(self.get_node_info(node['node']))
            
            # control the number of posts we want
            if len(nodes) >= 4:
                return nodes
            
            time.sleep(randint(6, 8))
        
        return nodes
        #return [self.get_node_info(container['edges'][0]['node'])]  # return just one node


    def get_node_info(self, node: dict, post_json=False) -> dict:
        """Manages the post info scraping. This method detects the post type and act accordinly to the post type

        Args:
            node (dict): post raw data from IG
            post_json (bool, optional): True if this method purpose is being used for scraping of a single post. False to many posts. Defaults to False.

        Returns:
            dict: post's informations
        """        
        
        if post_json:
            shortcode = node['code']
            media_type = node['media_type']
            
            # shortcode > 2 = carousel
            if media_type <= 2:
                return self.get_img_vid_details(shortcode)
            else:
                return self.get_carousel_details(shortcode)
        
        else:
            shortcode = node['shortcode']
            media_type = node['__typename']
        
            if media_type == 'GraphImage' or media_type == 'GraphVideo':
                return self.get_img_vid_details(shortcode)
            else:
                return self.get_carousel_details(shortcode)
    
    
    def get_img_vid_details(self, shortcode: str) -> dict:
        """Scrapes detailed information for an image or video post

        Args:
            shortcode (str): post shortcode

        Returns:
            dict: post detailed information
        """        
        
        media_json = self.__get_media_json(shortcode)
        image_info = media_json['image_versions2']['candidates'][0]
        
        video_url = media_json.get('video_versions', [])
        if video_url:
            video_url = video_url[0]['url']
            
        # 1 = image; 2 = video
        media_type = media_json['media_type']
        
        caption = media_json.get('caption')
        if caption:
            caption = caption['text']
        
        comments_number = media_json['comment_count']
        latest_comments = []
        
        # latest comments
        if comments_number > 0:
            comments_raw = media_json['comments']
            
            for comment in comments_raw:
                comment_author = comment['user']
                latest_comments.append({'author_profile_pic': comment_author['profile_pic_url'],
                                        'author_username': comment_author['username'],
                                        'text': comment['text'],
                                        'timestamp': comment['created_at']})
                
        
        details = {
            'shortcode': shortcode,
            'author_username': media_json['user']['username'],
            'url': f'{BASE_URL}p/{shortcode}',
            'image_url': image_info['url'],
            'caption': caption,
            'latest_comments': latest_comments,
            'comments_number': comments_number,
            'likes_number': media_json['like_count'],
            'is_video': False if media_type == 1 else True,
            'video_url': video_url,
            'location': self.get_media_location(media_json),
            'tags': self.extract_hashtags(caption) if caption else [],
            'mentions': self.extract_mentions(caption, media_json),
            'timestamp': media_json['taken_at'],
            'dimensions': {'height': image_info['height'], 'width': image_info['width']},
            
            # reels data
            'total_shares': None,  # FIXME: check how to find this data
            'total_plays': media_json.get('play_count'),
            'total_views': media_json.get('view_count'),
            'video_duration': media_json.get('video_duration')
        }
        
        return details
    
    
    def get_carousel_details(self, shortcode: str) -> dict:
        """Scrapes detailed information of a carousel post

        Args:
            shortcode (str): post shortcode

        Returns:
            dict: detailed informations of a carousel post
        """        
        
        media_json = self.__get_media_json(shortcode)
        carousel_medias_info = media_json['carousel_media']
        
        has_image = False
        has_video = False
        urls = []
        video_url = []
        
        for media in carousel_medias_info:
            if media['media_type'] == 1:               
                urls.append(media['image_versions2']['candidates'][0]['url'])
                
                # We want info for the first carousel image
                if not has_image:
                    image_info = media
                    
                has_image = True
                
            elif media['media_type'] == 2:
                single_video_url = media['video_versions'][0]['url']
    
                video_url.append(single_video_url)
                urls.append(single_video_url)
                
                # We want info for the first carousel video
                if not has_video:
                    video_info = media

                has_video = True
        
        comments_number = media_json['comment_count']
        latest_comments = []
        
        # latest comments
        if comments_number > 0:
            comments_raw = media_json['comments']
            
            for comment in comments_raw:
                comment_author = comment['user']
                latest_comments.append({'author_profile_pic': comment_author['profile_pic_url'],
                                        'author_username': comment_author['username'],
                                        'text': comment['text'],
                                        'timestamp': comment['created_at']})
        
        caption = media_json.get('caption')
        if caption:
            caption = caption['text']
        
        details = {
            'shortcode': shortcode,
            'author_username': media_json['user']['username'],
            'url': f'{BASE_URL}p/{shortcode}',
            'image_url': image_info['image_versions2']['candidates'][0]['url'] if has_image else video_info['image_versions2']['candidates'][0]['url'],
            'caption': caption,
            'comments_number': comments_number,
            'latest_comments': latest_comments,
            'likes_number': media_json['like_count'],
            'is_video': False if has_video == False else True,
            'video_url': video_url,
            'urls': urls,
            'location': self.get_media_location(media_json),
            'tags': self.extract_hashtags(caption) if caption else [],
            'mentions': self.extract_mentions(caption, media_json),
            'timestamp': media_json['taken_at'],
            'dimensions': {'height': image_info['original_height'], 'width': image_info['original_width']} if has_image else {'height': video_info['original_height'], 'width': video_info['original_width']}       
        }
        
        return details
    
    
    def get_media_location(self, media_json: dict) -> 'dict | None':
        return media_json.get('location')


    def extract_hashtags(self, caption_text: str) -> list:
        """Extracts the hashtags from the caption text."""
        
        hashtags = []

        if caption_text:
            # include words and emojis
            hashtags = re.findall(
                r"(?<!&)#(\w+|(?:[\xA9\xAE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u231A\u231B\u2328\u2388\u23CF\u23E9-\u23F3\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB-\u25FE\u2600-\u2604\u260E\u2611\u2614\u2615\u2618\u261D\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2648-\u2653\u2660\u2663\u2665\u2666\u2668\u267B\u267F\u2692-\u2694\u2696\u2697\u2699\u269B\u269C\u26A0\u26A1\u26AA\u26AB\u26B0\u26B1\u26BD\u26BE\u26C4\u26C5\u26C8\u26CE\u26CF\u26D1\u26D3\u26D4\u26E9\u26EA\u26F0-\u26F5\u26F7-\u26FA\u26FD\u2702\u2705\u2708-\u270D\u270F\u2712\u2714\u2716\u271D\u2721\u2728\u2733\u2734\u2744\u2747\u274C\u274E\u2753-\u2755\u2757\u2763\u2764\u2795-\u2797\u27A1\u27B0\u27BF\u2934\u2935\u2B05-\u2B07\u2B1B\u2B1C\u2B50\u2B55\u3030\u303D\u3297\u3299]|\uD83C[\uDC04\uDCCF\uDD70\uDD71\uDD7E\uDD7F\uDD8E\uDD91-\uDD9A\uDE01\uDE02\uDE1A\uDE2F\uDE32-\uDE3A\uDE50\uDE51\uDF00-\uDF21\uDF24-\uDF93\uDF96\uDF97\uDF99-\uDF9B\uDF9E-\uDFF0\uDFF3-\uDFF5\uDFF7-\uDFFF]|\uD83D[\uDC00-\uDCFD\uDCFF-\uDD3D\uDD49-\uDD4E\uDD50-\uDD67\uDD6F\uDD70\uDD73-\uDD79\uDD87\uDD8A-\uDD8D\uDD90\uDD95\uDD96\uDDA5\uDDA8\uDDB1\uDDB2\uDDBC\uDDC2-\uDDC4\uDDD1-\uDDD3\uDDDC-\uDDDE\uDDE1\uDDE3\uDDEF\uDDF3\uDDFA-\uDE4F\uDE80-\uDEC5\uDECB-\uDED0\uDEE0-\uDEE5\uDEE9\uDEEB\uDEEC\uDEF0\uDEF3]|\uD83E[\uDD10-\uDD18\uDD80-\uDD84\uDDC0]|(?:0\u20E3|1\u20E3|2\u20E3|3\u20E3|4\u20E3|5\u20E3|6\u20E3|7\u20E3|8\u20E3|9\u20E3|#\u20E3|\\*\u20E3|\uD83C(?:\uDDE6\uD83C(?:\uDDEB|\uDDFD|\uDDF1|\uDDF8|\uDDE9|\uDDF4|\uDDEE|\uDDF6|\uDDEC|\uDDF7|\uDDF2|\uDDFC|\uDDE8|\uDDFA|\uDDF9|\uDDFF|\uDDEA)|\uDDE7\uD83C(?:\uDDF8|\uDDED|\uDDE9|\uDDE7|\uDDFE|\uDDEA|\uDDFF|\uDDEF|\uDDF2|\uDDF9|\uDDF4|\uDDE6|\uDDFC|\uDDFB|\uDDF7|\uDDF3|\uDDEC|\uDDEB|\uDDEE|\uDDF6|\uDDF1)|\uDDE8\uD83C(?:\uDDF2|\uDDE6|\uDDFB|\uDDEB|\uDDF1|\uDDF3|\uDDFD|\uDDF5|\uDDE8|\uDDF4|\uDDEC|\uDDE9|\uDDF0|\uDDF7|\uDDEE|\uDDFA|\uDDFC|\uDDFE|\uDDFF|\uDDED)|\uDDE9\uD83C(?:\uDDFF|\uDDF0|\uDDEC|\uDDEF|\uDDF2|\uDDF4|\uDDEA)|\uDDEA\uD83C(?:\uDDE6|\uDDE8|\uDDEC|\uDDF7|\uDDEA|\uDDF9|\uDDFA|\uDDF8|\uDDED)|\uDDEB\uD83C(?:\uDDF0|\uDDF4|\uDDEF|\uDDEE|\uDDF7|\uDDF2)|\uDDEC\uD83C(?:\uDDF6|\uDDEB|\uDDE6|\uDDF2|\uDDEA|\uDDED|\uDDEE|\uDDF7|\uDDF1|\uDDE9|\uDDF5|\uDDFA|\uDDF9|\uDDEC|\uDDF3|\uDDFC|\uDDFE|\uDDF8|\uDDE7)|\uDDED\uD83C(?:\uDDF7|\uDDF9|\uDDF2|\uDDF3|\uDDF0|\uDDFA)|\uDDEE\uD83C(?:\uDDF4|\uDDE8|\uDDF8|\uDDF3|\uDDE9|\uDDF7|\uDDF6|\uDDEA|\uDDF2|\uDDF1|\uDDF9)|\uDDEF\uD83C(?:\uDDF2|\uDDF5|\uDDEA|\uDDF4)|\uDDF0\uD83C(?:\uDDED|\uDDFE|\uDDF2|\uDDFF|\uDDEA|\uDDEE|\uDDFC|\uDDEC|\uDDF5|\uDDF7|\uDDF3)|\uDDF1\uD83C(?:\uDDE6|\uDDFB|\uDDE7|\uDDF8|\uDDF7|\uDDFE|\uDDEE|\uDDF9|\uDDFA|\uDDF0|\uDDE8)|\uDDF2\uD83C(?:\uDDF4|\uDDF0|\uDDEC|\uDDFC|\uDDFE|\uDDFB|\uDDF1|\uDDF9|\uDDED|\uDDF6|\uDDF7|\uDDFA|\uDDFD|\uDDE9|\uDDE8|\uDDF3|\uDDEA|\uDDF8|\uDDE6|\uDDFF|\uDDF2|\uDDF5|\uDDEB)|\uDDF3\uD83C(?:\uDDE6|\uDDF7|\uDDF5|\uDDF1|\uDDE8|\uDDFF|\uDDEE|\uDDEA|\uDDEC|\uDDFA|\uDDEB|\uDDF4)|\uDDF4\uD83C\uDDF2|\uDDF5\uD83C(?:\uDDEB|\uDDF0|\uDDFC|\uDDF8|\uDDE6|\uDDEC|\uDDFE|\uDDEA|\uDDED|\uDDF3|\uDDF1|\uDDF9|\uDDF7|\uDDF2)|\uDDF6\uD83C\uDDE6|\uDDF7\uD83C(?:\uDDEA|\uDDF4|\uDDFA|\uDDFC|\uDDF8)|\uDDF8\uD83C(?:\uDDFB|\uDDF2|\uDDF9|\uDDE6|\uDDF3|\uDDE8|\uDDF1|\uDDEC|\uDDFD|\uDDF0|\uDDEE|\uDDE7|\uDDF4|\uDDF8|\uDDED|\uDDE9|\uDDF7|\uDDEF|\uDDFF|\uDDEA|\uDDFE)|\uDDF9\uD83C(?:\uDDE9|\uDDEB|\uDDFC|\uDDEF|\uDDFF|\uDDED|\uDDF1|\uDDEC|\uDDF0|\uDDF4|\uDDF9|\uDDE6|\uDDF3|\uDDF7|\uDDF2|\uDDE8|\uDDFB)|\uDDFA\uD83C(?:\uDDEC|\uDDE6|\uDDF8|\uDDFE|\uDDF2|\uDDFF)|\uDDFB\uD83C(?:\uDDEC|\uDDE8|\uDDEE|\uDDFA|\uDDE6|\uDDEA|\uDDF3)|\uDDFC\uD83C(?:\uDDF8|\uDDEB)|\uDDFD\uD83C\uDDF0|\uDDFE\uD83C(?:\uDDF9|\uDDEA)|\uDDFF\uD83C(?:\uDDE6|\uDDF2|\uDDFC))))[\ufe00-\ufe0f\u200d]?)+",
                caption_text, re.UNICODE)
            
            hashtags = list(set(hashtags))

        return hashtags
    
    
    def extract_mentions(self, caption_text: str, post_json: dict, media_type: str = 'image') -> list:
        mentions = []
        
        if caption_text: 
            # look for mentions in media caption
            mentions = re.findall(r"@[A-Za-z0-9-_.]+", caption_text, re.UNICODE)
            mentions = [mention[1:] for mention in mentions]  # remove 'at' simbol
        
        # look for tagged users inside media
        if media_type == 'image':
            try:
                tagged_users_info = post_json['usertags']['in']
                
                for user in tagged_users_info:
                    mentions.append(user['user']['username'])
                    
            except KeyError:
                pass
            
        mentions = list(set(mentions))
        return mentions  


    def __get_media_json(self, shortcode):
        resp = self.get_json(VIEW_MEDIA_URL.format(shortcode))
        if resp is not None:
            try:
                return json.loads(resp)['items'][0]
            except ValueError:
                print('Failed to get media details for ' + shortcode)
                return {'message': 'Failed to get media details for ' + shortcode}

        else:
            print('Failed to get media details for ' + shortcode)
            return 'Failed to get media details for ' + shortcode


    def get_post_comments(self, shortcode: str, end_cursor='') -> list:
        """Scrapes the latest post's comments

        Args:
            shortcode (str): post shortcode
            end_cursor (str, optional): Defaults to ''

        Returns:
            list: list with the lastest comments
        """        
        
        comments, end_cursor = self.__query_comments(shortcode, end_cursor)

        total_comments = []
        if comments:
            try:
                for item in comments:
                    comment_owner = item['owner']
                    
                    comment = {}
                    comment['timestamp'] = item['created_at']
                    comment['author_username'] = comment_owner['username']
                    comment['author_profile_pic'] = comment_owner.get('profile_pic_url', '')
                    comment['text'] = item['text']

                    total_comments.append(comment)

                    if len(total_comments) >= 50:
                        return total_comments

                return total_comments
            except ValueError:
                return 'Failed to query comments for shortcode ' + shortcode


    def __query_comments(self, shortcode: str, end_cursor='') -> list:
        """Query the lastest comments of a post

        Args:
            shortcode (str): post shortcode
            end_cursor (str, optional): Defaults to ''

        Returns:
            list: list of latest comments of a post
        """        
        
        params = QUERY_COMMENTS_VARS.format(shortcode, end_cursor)
        self.ig_connection.update_ig_gis_header(params)

        resp = self.get_json(QUERY_COMMENTS.format(params))

        if resp is not None:

            payload = json.loads(resp)
            if 'data' not in payload.keys():
                print(payload)
                return None, None

            payload = payload['data']['shortcode_media']

            if payload:
                container = payload['edge_media_to_comment']
                comments = [node['node'] for node in container['edges']]
                end_cursor = container['page_info']['end_cursor']
                return comments, end_cursor

        return None
  
    
    def __query_followings(self, id: str, end_cursor='', followings=[]):      
        """Recursevely scrapes users that are followed by the influencer until reach 50 usernames

        Args:
            id (str): user shortcode
            end_cursor (str, optional): Defaults to ''.
            followings (list, optional): Internal method arg. Defaults to [].

        Returns:
            list: latest 50 followings' usernames
        """
        
        
        params = QUERY_FOLLOWINGS_VARS.format(id, end_cursor)
        resp = self.get_json(QUERY_FOLLOWINGS.format(params))
        
        if resp is not None:
            payload = json.loads(resp)['data']['user']['edge_follow']
            end_cursor = payload['page_info']['end_cursor']
            
            if payload:
                                
                for node in payload['edges']:
                    if len(followings) >= 200:
                        return followings
                    followings.append(node['node']['username'])
                    
                # Recursive
                if end_cursor:
                    followings = self.__query_followings(id, end_cursor, followings)
                        
                return followings

        return None


    def __query_followers(self, id: str, end_cursor='', followers=[]) -> list:
        """Recursevely scrapes followers until reach 50 followers

        Args:
            id (str): user shortcode
            end_cursor (str, optional): Defaults to ''.
            followers (list, optional): Internal method arg. Defaults to [].

        Returns:
            list: latest 50 followers's usernames
        """
        
        params = QUERY_FOLLOWERS_VARS.format(id, end_cursor)
        resp = self.get_json(QUERY_FOLLOWERS.format(params))
        
        if resp is not None:
            payload = json.loads(resp)['data']['user']['edge_followed_by']
            end_cursor = payload['page_info']['end_cursor']
            
            if payload:
                                
                for node in payload['edges']:
                    if len(followers) >= 50:
                        return followers
                    followers.append(node['node']['username'])
                    
                # Recursive
                if end_cursor:
                    followers = self.__query_followers(id, end_cursor, followers)
                        
                return followers

        else:
            return None


    def _check_user(self, username: str) -> Union[str, dict]:
        """Check if a IG user exists and if it's not private

        Args:
            username (str): username of the target profile

        Returns:
            str: If invalid username or private. It can return a str in case o getting blocked by IG
            dict: user shared data
        """        
        
        #resp = get_shared_data_userinfo(username)
        resp = self.get_profile_info(username)
        
        if resp:
            if type(resp) == str:
                return 'Too many requests' if resp == 'Blocked' else 'Invalid'
            
            else:
                if resp['info']['is_private'] or not (resp['info']['posts_count'] > 0):
                    return 'Private'
        
        else:
            return 'Error'

        return resp


    def get_user_followers(self, user: dict) -> list:
        """Scrapes the user's followers'

        Args:
            user (dict): dict containing the user id (shortcode)

        Returns:
            list: list followers's usernames
        """
        
        try:
            followers = self.__query_followers(user['info']['id'])
        except Exception:
            self.error_bot.send_message(f'Error collecting user followers for user id {user["info"]["id"]}')
            self.mongo.log_error(f'Error collecting user followers for user id {user["info"]["id"]}', format_exc())
        return followers
    
    
    def get_user_following(self, user: dict) -> list:
        """Scrapes the user's that the influencers follows'

        Args:
            user (dict): dict containing the user id (shortcode)

        Returns:
            list: users been followed by the influencer
        """
        
        following = self.__query_followings(user['id'])
        return following


    def create_aws_resource(self):
        s3 = boto3.resource(
            's3',
            aws_access_key_id=self.s3_key_id,
            aws_secret_access_key=self.s3_key_secret,
            region_name=self.s3_default_region
        )
        return s3


    def save_file_to_aws_bucket(self, url, key, tiktok_video=False):
        file_url = None
        # get the connection of AWS S3 Bucket
        s3 = self.create_aws_resource()

        if tiktok_video:
            headers = {
                'Accept-language': 'en',
                'referer': url,
                'User-Agent': 'Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, '
                              'like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.102011-10-16 20:23:10 '
            }
            response = requests.get(url, headers=headers)
        else:
            response = requests.get(url)

        if response.status_code == 200:
            raw_data = response.content
            url_parser = urlparse(url)
            file_name = os.path.basename(url_parser.path)

            try:
                # Write the raw data as byte in new file_name in the server
                with open(file_name, 'wb') as new_file:
                    new_file.write(raw_data)

                # Open the server file as read mode and upload in AWS S3 Bucket.
                data = open(file_name, 'rb')
                s3.Bucket(self.s3_bucket_name).put_object(Key=key, Body=data, ACL=self.s3_default_acl)
                data.close()

                # Format the return URL of upload file in S3 Bucket
                file_url = 'https://%s.%s/%s' % (
                    self.s3_bucket_name, 's3.' + self.s3_default_region + '.amazonaws.com', key)
            except Exception:
                print("Error in file upload %s." % (format_exc()))

            finally:
                # Close and remove file from Server
                new_file.close()
                
                try:
                    os.remove(file_name)
                except Exception:
                    pass
                
                print(f'Attachment successfully saved in S3 Bucket url {file_url}')
        else:
            print('Error: Could not parse url')
        return file_url


    def save_profile_pic_to_s3(self, image_url, profile_username):
        key = 'audience/' + profile_username + '/profile_' + profile_username + '.jpg'
        uploaded_url = self.save_file_to_aws_bucket(image_url, key)
        return uploaded_url


    def get_user_audience(self, user: dict) -> Union[str, dict]:
        """Computes the audience metrics

        Args:
            user (dict): user informations
            
        Returns:
            str: if error ocurred
            dict: audience metrics
        """

        col_audience = self.mongo.db_client['audience']
        audiences = col_audience.find({'influencers_followed': user['username']})
        audience_size = len(list(audiences.clone()))  # Doesn't consume the cursor
        audience_profile = []
        audi_expec_size = 20

        if audience_size < audi_expec_size:
            followers = self.get_user_followers(user)
            count = 0

            for follower in followers:
                if audience_size + count > audi_expec_size:
                    break

                profile = col_audience.find_one({'username': follower})
                
                if profile:
                    if 'influencers_followed' not in profile.keys():
                        profile['influencers_followed'] = []

                    if user['username'] not in profile['influencers_followed']:
                        if not profile['influencers_followed']:
                            profile['influencers_followed'] = []

                        profile['influencers_followed'].append(user['username'])
                        col_audience.update_one({'username': profile['username']},
                                                {'$set': {'influencers_followed': profile['influencers_followed']}})

                    audience_profile.append(profile)
                    count += 1
                    continue


                # this sleep is going to delay the data collection a lot
                # but the chances of getting blocked are smaller
                time.sleep(randint(2, 4))
                # TODO: check if there's a way of collecting the same info about the follower without the next line of code
                profile = self.get_profile_info(follower)

                if 'Error' in profile:
                    count += 1
                    continue
                
                # if we get blocked by instagram, return a message with the issue
                elif profile == 'Blocked':
                    return 'Blocked by instagram (too many resquests)'

                formated_profile = {
                    'username': profile['username'],
                    'name': profile['info']['full_name'],
                    'number_following': profile['info']['following_count'],
                    'number_followers': profile['info']['followers_count'],
                    'profile_picture': self.save_profile_pic_to_s3(profile['info']['profile_pic_url'], profile['username']),
                    'description': profile['info']['biography'],
                    'number_media': profile['info']['posts_count'],
                    'influencers_followed': [user['username']],
                    'is_business': profile['info']['is_business_account']
                }

                col_audience.insert_one(formated_profile)

                audience_profile.append(formated_profile)

                count += 1
        else:
            for audience in audiences:
               audience_profile.append(audience)
        
        # TODO: move the metrics computations below to the metrics microservice
        total_score = 0
        reach = 0
        fakes = 0
        influencers = 0
        real = 0
        mass = 0

        for profile in audience_profile:
            score = 0

            try:
                follower_count = profile['number_followers']
                if follower_count == 0:
                    follower_count = 1

                following_count = profile['number_following']

                follow_diff = following_count / follower_count

                if follow_diff > 10:
                    score += 25

                if len(re.findall('[0-9]+', profile['username'])) > 5:
                    score += 10

                number_vowels = len(re.findall('(?i)([aeiou])', profile['username']))
                if number_vowels == 0:
                    number_vowels = 1

                number_consonants = len(re.findall('(?i)([bcdfghjklmnpqrstvwxz])', profile['username']))
                if (number_consonants / number_vowels) > 5:
                    score += 10

                if profile['number_media'] < 10:
                    score += 25

                # No profile picture
                if 'profile_picture' in profile.keys():
                    if 't51.2885-19/44884218_345707102882519_2446069589734326272_n.jpg' in profile['profile_picture']:
                        score += 25

                profile_score = 100 - score
                total_score += profile_score

                # Fake
                if profile_score <= 30:
                    fakes += 1
                    
                # Mass Follower
                elif 30 < profile_score <= 60:
                    mass += 1
                    
                # Real People
                elif 60 < profile_score <= 100:
                    real += 1
                    
                # Influencer     
                elif 'is_business' in profile.keys():
                    if follower_count > 5000 and profile['is_business'] and follow_diff <= 10:
                        influencers += 1

                # the higher the following_count, the chances of seeing the influencer post in the
                # feed gets smaller
                if following_count < 1500:
                    reach += 1
            except:
                continue

        audience_number = len(audience_profile)
        if audience_number == 0:
            audience_number = 1

        final_score = round(total_score / audience_number, 2)
        final_reach = round((reach / audience_number) * 100, 2)
        final_real = round((real / audience_number) * 100, 2)
        final_mass = round((mass / audience_number) * 100, 2)
        final_fake = round((fakes / audience_number) * 100, 2)
        final_inf = round((influencers / audience_number) * 100, 2)

        influencer = self.mongo.db_client['profiles'].find_one({'username': user['username']})
        credibility_score = 0
        
        if influencer:
            if 'engagement_rate' in influencer.keys():
                engagement_rate = influencer['engagement_rate']
                credibility_score = (engagement_rate + final_score + final_reach) / 3
                credibility_score = round(credibility_score, 1)
            # credibility_score = ...

        audience = {
            'reachability': final_reach,
            'authenticity': final_score,
            'audience_type': {
                'real_people': final_real,
                'suspicious_accounts': final_fake,
                'mass_followers': final_mass,
                'influencers': final_inf
            },
            'credibility_score': credibility_score
        }

        return audience
    
    
    def connect_mongo(self, database: str):
        self.mongo = IG_Mongo(database, local_conn=False) 
