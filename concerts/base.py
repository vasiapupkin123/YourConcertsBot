# coding=utf-8

import time
from datetime import datetime


class Concert:
    def __init__(self, artist=None, city=None, datetime_str=None,
                 datetime=None, url=None, price=None, place=None, concert_name=None,
                 dict_source = None):
        if dict_source:
            self.set_from_dict(dict_source)
        else:
            self.artist = artist
            self.city = city
            self.datetime_str = datetime_str
            self.datetime = datetime or self._extract_date_from_seatscan_txt(self.datetime_str)
            self.url = url
            self.price = price
            self.place = place
            self.concert_name = concert_name

    @property
    def description(self):
        # часто описание выглядит в стиле "Группа *GroupName*" - такое лучше отбрасывать
        if self.concert_name:
            concert_name = self.concert_name.replace('.', ' ')
            tokens_from_artist_name = set([word.lower() for word in self.artist.split()] + ['группа'])
            tokens_from_concert_name = set([word.lower() for word in concert_name.split()] + ['группа'])
            if not tokens_from_concert_name <= tokens_from_artist_name:
                concert_name = self.concert_name + '\n'
            else:
                concert_name = ''
        else:
            concert_name = ''
        if self.place:
            place = ', ' + self.place
        else:
            place = ''
        if self.price:
            price = '\nМинимальная цена: %s руб.' % self.price
        else:
            price = ''
        pattern = '%s - %s\n%s%s%s%s'
        tuple = (self.artist, self.datetime_str, concert_name, self.city, place, price)
        return pattern % tuple

    def get_dict(self):
        d = self.__dict__
        del d['datetime']
        return self.__dict__

    def set_from_dict(self, dict_source):
        dt = (dict_source.get('year', None), dict_source.get('month', None), dict_source.get('day', None),
              dict_source.get('hour', None), dict_source.get('minute', None))
        dict_source['datetime'] = datetime(*dt)
        self.__dict__.update(dict_source)

    def _extract_date_from_seatscan_txt(self, text):
        '''
        "17 Фев" -> {'datenum': 20171702, 'day': 17, 'month': 2, 'year': 2017}
        или год может быть и 2018, в зависимости от текущей даты
        '''
        months_dict = {'Янв': '01', 'Фев': '02', 'Мар': '03', 'Апр': '04', 'Май': '05', 'Июн': '06',
                       'Июл': '07', 'Авг': '08', 'Сен': '09', 'Окт': '10', 'Ноя': '11', 'Дек': '12'}
        datetime_items = text.split(' ')
        try:
            # day
            day = int(datetime_items[0])
            # month
            month = int(months_dict[datetime_items[1]])
            # year
            lcltime = time.localtime()
            now_date = ('0' + str(lcltime.tm_mon))[-2:] + ('0' + str(lcltime.tm_mday))[-2:]
            event_date_string = ('0' + str(month))[-2:] + ('0' + str(day))[-2:]
            year = lcltime.tm_year + 1 * (int(event_date_string) < int(now_date))
        except:
            day = None
            month = None
            year = None
        try:
            # hour
            hour = int(datetime_items[2][:2])
            # minute
            minute = int(datetime_items[2][3:5])
        except:
            hour = None
            minute = None
        return datetime(*(year, month, day, hour, minute))
