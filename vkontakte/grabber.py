# coding: utf-8
import json
import os
import time

from .utils import count_list_values
from vkontakte.grabber_api_methods import VKAPIMethods
from vkontakte.grabber_html_audio import VKAudioParser

"""
время: 20ms запись и чтение json, 150ms на нахождение id, 450-750ms на скачивание плейлиста
"""


class VKGrabber(VKAudioParser, VKAPIMethods):
    """
    класс объединяет 2 отдельных способа извлечения информации и рождает на их пересечении новые методы
    например, из метода одного класса получить id по username, а по другому - его аудио
    """

    def __init__(self, credentials, archive_foldername=None, vk_first=True, cookies_filename=None):
        """
        :param credentials: словарь с полями 'login', 'password', 'app_token'
        :param archive_foldername: имя папки, где хранятся файлики со списками аудио вида vk_user_id.json
        :param vk_first: в классе появляется хранение аудио в бд, vk_first показывает, куда смотреть сначала
        можно по фану задавать это не True/False, а вероятность сначала брать вк, и только потом бд
        каждый запрос кидать рандомное число и решать в зависимости от него
        :param cookies_filename: параметр для VkAudioParser, который позволяет не логиниться заново
        """
        VKAPIMethods.__init__(self, credentials)
        VKAudioParser.__init__(self, credentials, cookies_filename)
        self.ARCHIVE_FOLDERNAME = archive_foldername
        self.vk_first = vk_first

    """
    если кто-то хочет держать свои аудио закрытыми, но пользоваться сервисом, надо уметь сохранять его список аудио и
    использовать его, чтобы человек мог просто 1 раз открыть аудио и закрыть обратно
    """

    def _get_audios_from_db(self, vk_uid):
        if not self.ARCHIVE_FOLDERNAME:
            return None
        try:
            filename = os.path.join(self.ARCHIVE_FOLDERNAME, str(vk_uid) + '.json')
            audios = json.loads(open(filename).read())
            return audios
        except:
            return None

    def set_audios_to_db(self, vk_uid, audios_list):
        if not self.ARCHIVE_FOLDERNAME:
            return False
        try:
            filename = os.path.join(self.ARCHIVE_FOLDERNAME, str(vk_uid) + '.json')
            with open(filename, 'w', encoding='utf8') as outfile:
                json.dump(audios_list, outfile, ensure_ascii=False)
            return True
        except IndexError:
            return False

    def get_audios(self, target_person):
        """
        переопределим get_audios, а тем самым косвенно и все остальные внешние методы с музыкой. Из нового:
        1) они принимают не только user_id, но и username и url
        2) если не получается достать аудио из вк, есть попытка вернуть список из архива
        3) можно задать порядок доставания аудио и при большой загрузке сначала смотреть в базу, а не вк
        4) результат каждого успешного скачивания вк обновляет архивные данные
        side-effect: если я прикинусь тобой - то я обновлю твои аудио, а ты мб этого не хотел
        можно это вылечить дописыванием вначале telegram_chat_id - тогда его надо передавать как параметр куда-то
        """
        target_id = self.get_user_id(target_person)
        if self.vk_first:
            audios_from_vk = VKAudioParser.get_audios(self, target_id)
            if audios_from_vk:
                audios = audios_from_vk
            else:
                audios = self._get_audios_from_db(target_id)
        else:
            audios_from_db = self._get_audios_from_db(target_id)
            if audios_from_db:
                audios = audios_from_db
            else:
                audios = VKAudioParser.get_audios(self, target_id)
        if audios:
            self.set_audios_to_db(target_id, audios)
        return audios

    def get_artists_from_several_users(self, users_list, freezetime=0.35, save_to_json_filename=None, log_print=False):
        "метод качает аудио сразу с нескольких юзеров. Появляется логгирование и сохранение в файлике на случай обрыва"
        users_artists = dict()
        users_number = len(users_list)
        # можно указать 10 юзеров в users_list, и все они будут одним и тем же user_id, за этим имеет смысл следить
        vk_uid_visited = []
        if log_print:
            t0 = time.time()
        for i, man in enumerate(users_list):
            try:
                uid = self.get_user_id(man)
                if uid in vk_uid_visited:
                    pass
                vk_uid_visited.append(uid)
                artists = self.get_artists(uid)
                if artists:
                    artists = list(artists)
                    users_artists.update({man: artists})
                    if save_to_json_filename:
                        with open(save_to_json_filename, 'w', encoding='utf8') as outfile:
                            json.dump(users_artists, outfile, ensure_ascii=False)
                if log_print:
                    print('%d/%d: vk.com/id%s; time spent: %.2f sec' % (i + 1, users_number, man, time.time() - t0))
                if (i + 1) != users_number:
                    time.sleep(freezetime)
            except:
                pass
        return users_artists

    def get_artists_popularity(self, target_person, top_len = 10):
        # user_id -> [ ['artist#1',num_of_artist#1_tracks_in_target_id_audio], ... ], 'artist1-#1\nartist2-#2..'
        target_id = self.get_user_id(target_person)
        audios = self.get_audios(target_id)
        if audios:
            popularity = count_list_values([audio['artist'] for audio in audios])
            if top_len:
                text_popularity = '\n'.join([a[0]+' - '+str(a[1]) for a in popularity[:top_len]])
            else:
                text_popularity = None
            return popularity, text_popularity
        return None, None
