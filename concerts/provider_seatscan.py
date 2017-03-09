# coding=utf-8
import json
import re
import time

import requests
from .base import Concert


class SeatscanGrabber(object):
    '''
    класс для сбора информации о концертах исполнителей с сайта seatscan.ru
    запрос идёт в 2 этапа:
    1) в поиске находим ссылку на исполнителя через https://seatscan.ru/msk/search?q=%%%query%%%
    2) на страничке исполнителя вытаскиваем концерты
    используется 3 кэша, все позволяют порой экономить запрос 1) и кэш#3 экономит и запрос 2)
    1) словарик название_исполнителя_с_сайта.lower() -> url
    2) словарик запрос -> название_исполнителя_с_сайта.lower()
    3) список запрос.lower(), которые ничего не выдали
    '''

    def __init__(self,
                 artist_2_url_json_filename,
                 artist_2_artist_json_filename,
                 artists_that_failed_on_seatscan_filename,
                 all_concerts_filename):
        # подкачиваются вспомогательные словарики и списки
        self.artist_2_url_json_filename = artist_2_url_json_filename
        self.artist_2_artist_json_filename = artist_2_artist_json_filename
        self.artists_that_failed_on_seatscan_filename = artists_that_failed_on_seatscan_filename
        self.all_concerts_filename = all_concerts_filename
        self.artists_2_urls = json.loads(open(self.artist_2_url_json_filename).read())
        self.artists_2_artists = json.loads(open(self.artist_2_artist_json_filename).read())
        with open(self.artists_that_failed_on_seatscan_filename) as f:
            self.artists_that_failed_on_seatscan = set(f.read().split('\n'))
        try:
            self.all_concerts_as_dicts = json.loads(open(self.all_concerts_filename).read())
            self.all_concerts = [Concert(dict_source=concert_dict) for concert_dict in self.all_concerts_as_dicts]
        except:
            self.all_concerts_as_dicts = []
            self.all_concerts = []


    def _rewrite_artist_2_url_file(self):
        with open(self.artist_2_url_json_filename, 'w', encoding='utf8') as outfile:
            json.dump(self.artists_2_urls, outfile, ensure_ascii=False)

    def _rewrite_artist_2_artist_file(self):
        with open(self.artist_2_artist_json_filename, 'w', encoding='utf8') as outfile:
            json.dump(self.artists_2_artists, outfile, ensure_ascii=False)

    def _rewrite_artists_that_failed_on_seatscan(self):
        with open(self.artists_that_failed_on_seatscan_filename, 'w') as f:
            f.write('\n'.join(set(self.artists_that_failed_on_seatscan)))

    def _del_markup(self, html):
        return (re.sub(r'\<[^>]*\>', '', html))

    def _get_html(self, url):
        html = requests.get(url).text.replace('&#34;', "'")
        return html

    def _get_artist_url_and_name(self, artist):
        '''
        функция возвращает ссылку на список концертов группы и нормальное название группы
        сначала смотрим в сохранённых файликах. если там нет - уже идём на сайт
        '''
        artist = artist.lower()
        artist_original_name = self.artists_2_artists.get(artist, artist)
        url_artist = self.artists_2_urls.get(artist_original_name.lower())
        if url_artist:
            return url_artist, artist_original_name
        if artist in self.artists_that_failed_on_seatscan:
            return None, None
        try:
            url_search = 'https://seatscan.ru/msk/search?q=' + artist_original_name
            html_search = self._get_html(url_search)
            temp = html_search.split('performer/')[1].split('">')
            artist_name = temp[0]
            artist_original_name = temp[1].split('<')[0]
            url_artist = 'https://seatscan.ru/performer/' + artist_name
            self.artists_2_urls.update({artist_original_name.lower(): url_artist})
            self._rewrite_artist_2_url_file()
            self.artists_2_artists.update({artist: artist_original_name})
            self._rewrite_artist_2_artist_file()
            return url_artist, artist_original_name
        except IndexError:
            self.artists_that_failed_on_seatscan.add(artist)
            self._rewrite_artists_that_failed_on_seatscan()
            return None, None

    def _get_events_from_html(self, html_artist, artist_original_name):
        'из готовой странички вытаскивает все события и раскладывает в список словарей'
        html_artist = html_artist.replace('<tr class="even">\n<td>', '<tr class="odd">\n<td>')
        event_html_blocks = html_artist.split('<tr class="odd">\n<td>')[1:]
        events_list = [self._del_markup(html_block).split('\n')[:5] for html_block in event_html_blocks]
        concerts = []
        for event in events_list:
            try:
                price = int(event[1].split()[0])
            except:
                price = None
            new_concert = Concert(artist=artist_original_name, city=event[2], datetime_str=event[0], url=None,
                                  price=price, place=event[4], concert_name=event[3])
            concerts.append(new_concert)
        return concerts

    def get_concerts(self, artists, save_to_json_filename=None, log_print_freq=None):
        '''
        самая главная функция: возвращает список концертов по одной или нескольким группам
        293ms уходит на получение url_artist
        390ms уходит на получение concerts_html
        1ms уходит на обращение списка концертов в текст
        ---
        кеширование концертов
        1) в рамках одного запроса не ходить по одним и тем же url'ам. Это отслеживаем в urls_visited
        2) между пользователями: все концерты сначала ищем в локальной базе.
        Если есть - берём оттуда, иначе - качаем и пополняем базу
        '''
        # настроим всё для логгирования, если это необходимо
        if log_print_freq:
            t0 = time.time()

        def log_it(artist_number, print_last=False, comment=''):
            if artist_number + 1 != len(artists) or print_last:
                if log_print_freq and (artist_number + 1) % log_print_freq == 0:
                    log_tuple = (artist_number + 1, len(artists), time.time() - t0, len(concerts), comment)
                    print('%d / %d; %.3f sec; %d concerts; %s' % log_tuple)

        # подформатируем список артистов (в запрос могла прийти и строка)
        if isinstance(artists, str):
            artists = [artists]
        else:
            artists = [artist.lower() for artist in artists]
        artists = list(set(artists))
        # начинаем качать
        concerts = []
        urls_visited = set()
        # всё известное сначала сформировать, всё неизвестное циклом: лаконичнее и чуть быстрее
        for artist_number, artist in enumerate(artists):
            url_artist, artist_original_name = self._get_artist_url_and_name(artist)
            log_it(artist_number)
            # не нашли исполнителя или уже посещали его - идём дальше
            if not url_artist or url_artist in urls_visited:
                continue
            urls_visited.add(url_artist)
            concerts_html = self._get_html(url_artist)
            try:
                concerts_html = concerts_html.split('рошедшие концерты')[2]
            except:
                pass  # может не быть прошедших концертов - тогда идём дальше
            if not concerts_html:
                continue
            new_concerts = self._get_events_from_html(concerts_html, artist_original_name)
            concerts += new_concerts
            self.all_concerts += new_concerts
            new_concerts_as_dicts = [new_concert.get_dict() for new_concert in new_concerts]
            self.all_concerts_as_dicts += new_concerts_as_dicts
            with open(self.all_concerts_filename, 'w', encoding='utf8') as outfile:
                json.dump(self.all_concerts_as_dicts, outfile, ensure_ascii=False)
            if save_to_json_filename:
                with open(save_to_json_filename, 'w', encoding='utf8') as outfile:
                    json.dump(concerts, outfile, ensure_ascii=False)
        log_it(len(artists) - 1, True)
        return concerts

    def get_text_from_concerts_list(self, concerts=None, cities=None, delim='\n---\n'):
        if concerts is None:
            concerts = []
        if cities is None:
            cities = []
        cities = [city.lower() for city in cities]
        if cities:
            return delim.join([concert.description for concert in concerts if concert.city.lower() in cities])
        else:
            return delim.join([concert.description for concert in concerts])

    def get_concerts_in_text(self, artists, cities = None, delim='\n---\n', log_print_freq=None):
        concerts = self.get_concerts(artists=artists, log_print_freq=log_print_freq)
        return self.get_text_from_concerts_list(concerts=concerts, cities=cities, delim=delim)
