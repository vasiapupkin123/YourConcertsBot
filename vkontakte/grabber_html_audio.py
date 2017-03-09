# coding: utf-8
"""
VK закрыл доступ к разделу API audio для всех разработчиков, для чего придётся парсить страницы
VKAudioParser принимает на вход словарик с полями 'login' и 'password', логинится, качает списки аудио по user_id

todo: обработка внезапного фейла авторизации уже сильно после пройденной авторизации
"""
import json
import pycurl
import re
from io import BytesIO
from urllib.parse import urlencode

from .utils import replace_html_symbols, count_list_values


class VKAudioParser(object):
    def __init__(self, credentials, cookies_filename=None):
        self._headers = {
            'accept': 'text/html,application/xhtml+xml,application/xmlq=0.9,image/webp,*/*q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0 WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36'
        }
        self._cookies = self._login_and_get_cookies(credentials, cookies_filename)
        self.audio_parsing_available = self._cookies is not None

    def _post(self, url=None, headers=None, cookies=None, params=None):
        print(url)
        client = pycurl.Curl()
        client.setopt(pycurl.URL, url)
        client.setopt(pycurl.HEADER, 1)
        client.setopt(pycurl.CONNECTTIMEOUT, 30)

        if params:
            client.setopt(pycurl.POST, 1)
            client.setopt(pycurl.POSTFIELDS, urlencode(params))

        if headers:
            if type(headers) is dict:
                headers = ["%s: %s" % (k, v) for k, v in headers.items()]
            client.setopt(pycurl.HTTPHEADER, headers)

        if cookies:
            if type(cookies) is list:
                cookies = "; ".join(cookies)
            client.setopt(pycurl.COOKIE, cookies)

        response_headers = BytesIO()
        contents = BytesIO()
        client.setopt(pycurl.WRITEDATA, contents)
        client.setopt(pycurl.HEADERFUNCTION, response_headers.write)
        client.perform()
        response_headers = response_headers.getvalue().decode('utf8')
        response_cookies = re.findall(r"^Set-Cookie: ([^\;]*)\;", response_headers, re.MULTILINE)

        return response_headers, response_cookies, contents.getvalue().decode('1251', errors='ignore')

    def _getUserPage(self, id=None, cookies=None):
        return self._post('https://vk.com/id%s' % id, {
            'headers': self._headers,
            'cookies': cookies
        })

    def _login_and_get_cookies(self, credentials, cookies_filename=None):
        # можно хранить куки и тогда не придётся делать лишнюю авторизацию
        if cookies_filename:
            try:
                cookies = json.loads(open(cookies_filename).read())
                # мб здесь стоит проверить работоспособность этих куков, если нет - то идти дальше
                return cookies
            except:
                pass
        # если не получилось считать из файла - авторизуемся и записываем куки на будущее
        _, ck, contents = self._post('https://vk.com', headers=self._headers)
        # парсим с главной страницы параметры ip_h и lg_h
        ip_h = re.search('name=\"ip_h\" value=\"(.*?)\"', contents, re.MULTILINE).group(1)
        lg_h = re.search('name=\"lg_h\" value=\"(.*?)\"', contents, re.MULTILINE).group(1)
        login_params = {
            'act': 'login',
            'role': 'al_frame',
            '_origin': 'https://vk.com',
            'ip_h': ip_h,
            'lg_h': lg_h,
            'email': credentials['login'],
            'pass': credentials['password']
        }
        # логинимся
        hdr, ck, _ = self._post('https://login.vk.com/?act=login', params=login_params, headers=self._headers,
                                cookies=ck)
        location = re.search(r'^Location\: (.*)$', hdr, re.MULTILINE).group(1).strip()
        if not '__q_hash' in location:
            return None
        # в случае успешной авторизации - переходим по редиректу
        _, ck, _ = self._post(location, headers=self._headers, cookies=ck)
        if cookies_filename:
            with open(cookies_filename, 'w', encoding='utf8') as outfile:
                json.dump(ck, outfile, ensure_ascii=False)
        return ck

    def get_audios(self, target_id):
        # user_id -> [{'artist':'', 'name':''}, ...]
        if not self.audio_parsing_available:
            return None
        hdr, ck, contents = self._post("https://vk.com/al_audio.php", headers=self._headers, cookies=self._cookies,
                                       params={
                                           "act": "load_silent",
                                           "al": 1,
                                           "album_id": -2,
                                           "band": False,
                                           "owner_id": target_id
                                       })
        try:
            audios_json = re.search(r'list\"\:(\[\[(.*)\]\])', contents, re.MULTILINE | re.UNICODE).group(1)
            audios = json.loads(audios_json, encoding='utf-8')
            audios = [{'artist': replace_html_symbols(audio[4]), 'name': replace_html_symbols(audio[3])}
                      for audio in audios]
            return audios
        except:
            return None

    def get_artists(self, target_id):
        # user_id -> {'artist1', 'artist2', ..}
        if not self.audio_parsing_available:
            return None
        audios = self.get_audios(target_id)
        if audios:
            return set([audio['artist'] for audio in audios])
        return None

    def get_artists_popularity(self, target_id, top_len = 10):
        # user_id -> [ ['artist#1',num_of_artist#1_tracks_in_target_id_audio], ... ]
        # по-хорошему это надо считать вне класса с учётом словарика замен различных названий одной группы
        if not self.audio_parsing_available:
            return None
        audios = self.get_audios(target_id)
        if audios:
            popularity = count_list_values([audio['artist'] for audio in audios])
            if top_len:
                text_popularity = '\n'.join([a[0]+' - '+str(a[1]) for a in popularity[:top_len]])
            else:
                text_popularity = None
            return popularity, text_popularity
        return None, None
