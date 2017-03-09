# coding: utf-8
"""
VK обладает отличным API, здесь тонкий буфер между ним и получателем информации
"""
import json
import re

import vk


class VKAPIMethods(object):
    def __init__(self, credentials=None):
        # логинимся по API token для получения доступа к API
        self.api = vk.API(vk.Session(access_token=credentials['app_token']))
        self._regex_id_from_string = re.compile(r'(https://)?(vk.com/)?((id(\d+))|(\w+))')

    def _get_username_from_string(self, q):
        """
        returns id or username for any format of user id/url,
        f.e., https://vk.com/id123/photos -> 123, https://vk.com/attas/photos -> attas, 123->123, attas->attas
        """
        try:
            return int(q)
        except:
            try:
                return ''.join(self._regex_id_from_string.findall(q)[0][-2:])
            except:
                return None

    def get_user_info(self, q):
        # any_string_containing_username_or_id ->  {'last_name':'', 'first_name':'', 'uid':''}
        try:
            q = self._get_username_from_string(q)
            user = self.api.users.get(user_ids=q)[0]
            return user
        except:
            return None

    def get_user_id(self, q):
        # any_string_containing_username_or_id -> user_id
        username = self._get_username_from_string(q)
        if isinstance(username, int):
            return username
        else:
            return self.get_user_info(username)['uid']

    def get_friends_id_list(self, q):
        # any_string_containing_username_or_id -> [friend1_user_id, ..]
        uid = self.get_user_id(q)
        friends_id_list = self.api.friends.get(user_id=uid)
        return friends_id_list
