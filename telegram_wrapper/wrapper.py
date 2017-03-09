# coding: utf-8
import json
import os
from time import strftime  # для логгирования
from uuid import uuid4

from numpy import cumsum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, InlineQueryHandler

from grabber import TotalDefaultGrabber
from utils import get_full_path

MSG_LIMIT_TELEGRAM = 4095
HELP_TEXT = u"""Я покажу тебе:
🔸 ближайшие концерты присланной тобой группы
🔸 твоих друзей вк, которые слушают этого исполнителя и могут составить тебе компанию
🔸 музыкальный портрет человека =) кинь на него ссылку или, если это твой друг, просто напиши его имя
🔸 список концертов всех исполнителей из твоего плейлиста в выбранных в настройках городах /concerts

Настроить бота можно здесь: /settings"""
START_TEXT = u"🙋 Привет! Я помогу найти интересные тебе концерты и компанию твоих друзей на них.\nТеперь получать удовольствие от концертов стало проще!)\n\n" + HELP_TEXT + "\n\nЕсли ты захочешь с кем-то поделиться этим ботом - можешь скинуть эту ссылку:\nhttp://telegra.ph/YourConcertsBot-12-02"
ABOUT_TEXT = u"""Concerts worth spreading"""


class TelegramWrapper(TotalDefaultGrabber):
    def __init__(self, TG_TOKEN, log_filename, feedback_filename):
        self.TG_TOKEN = TG_TOKEN
        self.log_filename = log_filename
        self.feedback_filename = feedback_filename
        self.DEFAULT_SETTINGS = {
            'city': []
            , 'friends': []
            , 'sort_type': 'date'
            , 'sort_order': 'az'
            , 'vk': {'id': None, 'last_update': None, 'name': None, 'url': None}
            , 'chat_state': ''
            , 'follow': []
            , 'unfollow': []
        }
        TotalDefaultGrabber.__init__(self)

    def split_msg(self, txt, size=MSG_LIMIT_TELEGRAM, delim='\n'):
        if len(txt) < size: return [txt]

        l = txt.split(delim)
        for p in l:
            if len(p) > size:
                return -1  # impossible then
                # may go into each p > 4095, change in loop there every last " " to "\n"
                # for poems may split firstly by "\n\n", only then inside by "\n", "."," "

        cs = cumsum([len(a) for a in l]) + range(0, len(l) * len(delim), len(delim))
        s = max(cumsum(cs <= size))

        resp = delim.join(l[:s])
        left = delim.join(l[s:])
        if len(left) < (size + 1):
            return [resp, left]
        else:
            return [resp] + self.split_msg(left, size, delim)

    def send_splitted_msg(self, bot, chat_id, msg, msg_limit=4095, reply_markup=-1, delim='\n'):
        l = self.split_msg(msg, msg_limit, delim)
        if len(l) > 3: bot.sendMessage(chat_id, text='Текст слишком большой и будет обрезан')
        if reply_markup == -1:
            for r in l[:3]:
                bot.sendMessage(chat_id, text=r)
        else:
            for r in l[:3]:
                bot.sendMessage(chat_id, text=r, reply_markup=reply_markup)

    def msg_with_buttons(self, bot, update, text, options, chat_id=-1, message_id=-1):
        if chat_id == -1: chat_id = update.message.chat_id
        text = text[:4095]
        if len(options) > 0:
            buttons = [InlineKeyboardButton(o[0], callback_data=o[1][:30]) for o in options]
            keyboard = [[b] for b in buttons]  # customize form
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id == -1:
                bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)
            else:
                bot.editMessageText(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            if message_id == -1:
                bot.sendMessage(chat_id=chat_id, text=text)
            else:
                bot.editMessageText(chat_id=chat_id, message_id=message_id, text=text)

    def spy(self, bot, update):
        try:
            user = update.message.from_user
        except:
            return False

        if str(user.username) == 'NikitaKuznetsov':
            return False

        txt = update.message.text

        logtxt = ["Слежка time!"
            , "Time: " + strftime("%Y-%m-%d %H:%M:%S")
            , "User: " + str(user.first_name) + ' ' + str(user.last_name)
            , "Username: @" + str(user.username)
            , "Chat_id: " + str(update.message.chat_id)
            , "Text: " + txt]

        with open(self.log_filename, "a") as log_file:
            log_file.write("\n" + "; ".join(logtxt))

    def slash_feedback(self, bot, update):
        self.spy(bot, update)
        chat_id = update.message.chat_id
        txt = update.message.text.strip()
        if txt.startswith('/feedback') and len(txt) > 9:
            with open(self.feedback_filename, "a") as feedback_file:
                feedback_file.write("\n" + txt[10:])
            bot.sendMessage(chat_id, text='Спасибо, с интересом ознакомлюсь!')
        else:
            self.msg_with_buttons(bot, update,
                                  "Ты можешь помочь улучшить бота: напиши, что тебе нравится, что не нравится, что стоило бы добавить. Всё это обязательно будет учтено. Жми кнопку)",
                                  options=[['Оставить отзыв', 'feedback']])

    def slash_start(self, bot, update):
        self.spy(bot, update)
        chat_id = update.message.chat_id
        bot.sendMessage(chat_id, text=START_TEXT)

    def slash_help(self, bot, update):
        self.spy(bot, update)
        chat_id = update.message.chat_id
        bot.sendMessage(chat_id, text=HELP_TEXT)

    def slash_about(self, bot, update):
        self.spy(bot, update)
        bot.sendMessage(update.message.chat_id, text=ABOUT_TEXT)

    def slash_error(self, bot, update, error):
        logtxt = ('Update "%s" caused error "%s"' % (update, error))
        if 'Bad Request: Input message content is not specified' not in logtxt:
            print(logtxt)

    def inside_idle(self, bot, update, text=-1, chat_id=-1):
        if text == -1:
            text = update.message.text
        if chat_id == -1:
            chat_id = update.message.chat_id
        d = self.get_settings(chat_id)
        chat_state = d['chat_state']

        if chat_state == 'settings-city-add':
            txt = text.replace(';', ',').replace('.', ',').replace('\n', ',').split(',')
            d['city'] = list(set([i.strip().capitalize() for i in d['city'] + txt]))
            if 'Питер' in d['city']:
                d['city'].remove('Питер')
                d['city'].append('Санкт-Петербург')
            if 'Спб' in d['city']:
                d['city'].remove('Спб')
                d['city'].append('Санкт-Петербург')
            if 'Мск' in d['city']:
                d['city'].remove('Мск')
                d['city'].append('Москва')
            d['chat_state'] = ''
            self.set_settings(chat_id, d)
            resp = 'Список городов с интересующими концертами обновлён. Теперь он выглядит так:\n' + ', '.join(
                d['city'])
            bot.sendMessage(chat_id, text=resp)
        elif chat_state == 'settings-follow-add':
            txt = text.replace('\n', ';').split(';')
            d['follow'] = list(set([i.strip().capitalize() for i in d['follow'] + txt]))
            d['chat_state'] = ''
            self.set_settings(chat_id, d)
            resp = 'Список исполнителей, за которыми нужно дополнительно к вк следить, обновлён. Теперь он выглядит так:\n' + ', '.join(
                d['follow'])
            bot.sendMessage(chat_id, text=resp)
        elif chat_state == 'settings-unfollow-add':
            txt = text.replace('\n', ';').split(';')
            d['unfollow'] = list(set([i.strip().capitalize() for i in d['unfollow'] + txt]))
            d['chat_state'] = ''
            self.set_settings(chat_id, d)
            resp = 'Список исполнителей, чьи концерты не нужно отслеживать, обновлён. Теперь он выглядит так:\n' + ', '.join(
                d['unfollow'])
            bot.sendMessage(chat_id, text=resp)
        elif chat_state == 'feedback':
            with open(self.feedback_filename, "a") as feedback_file:
                feedback_file.write("\n" + text)
            bot.sendMessage(chat_id, text='Спасибо, с интересом ознакомлюсь!')
            self.set_settings_field(chat_id, 'chat_state', '')
        elif chat_state == 'settings-vk-set':
            self.set_vk_profile(bot, chat_id, text)
        else:
            resp = self.get_resp_for_idle_text(text, cities=d['city'])
            bot.sendMessage(chat_id, text=resp)

    def get_resp_for_idle_text(self, text, cities=list(), chat_id=None):
        TEXT_IF_NOTHING_FOUND = u'Ничего не найдено. Попробуйте изменить запрос'
        if not cities:
            if not chat_id:
                cities = self.get_settings(chat_id)

        if 'vk.com/' in text:
            TOP_NUM = 10
            uid = self.get_user_id(text)
            url = 'https://vk.com/id%d' % uid
            resp = self.get_artists_popularity(uid, TOP_NUM)[1]
            if resp:
                resp = 'Топ-%d исполнителей %s по кол-ву треков:\n\n' % (TOP_NUM, url) + resp
            else:
                resp = TEXT_IF_NOTHING_FOUND
        else:
            concerts = self.get_concerts(text, log_print_freq=1)
            resp = self.get_text_from_concerts_list(concerts, cities)
            if resp is None or resp.strip() == '':
                resp = u'Концертов не найдено :('
        return resp

    def set_vk_profile(self, bot, chat_id, text):
        vk_info = self.get_user_info(text)
        vk_id = vk_info['uid']
        if not vk_id:
            bot.sendMessage(chat_id, text='Укажи свой профиль в вк. Указанная ссылка невалидна. Попробуй ещё раз')
            return False
        d = self.get_settings(chat_id)
        d['vk']['id'] = vk_id
        d['vk']['name'] = vk_info['first_name'] + ' ' + vk_info['last_name']
        d['vk']['url'] = 'https://vk.com/id' + str(vk_id)
        d['chat_state'] = ''
        self.set_settings(chat_id, d)
        bot.sendMessage(chat_id, text='Профиль обновлён. Ссылка на тебя: https://vk.com/id%d' % vk_id)
        TOP_NUM = 10
        PRE_COMMENT = 'Маленький бонус, топ-%d исполнителей по твоим аудиозаписям:\n\n' % TOP_NUM
        POST_COMMENT = '\n\nТы можешь посмотреть топ и по другим пользователям VK, просто кидай сюда на них ссылку. Именно ссылку'
        audios_top = self.get_artists_popularity(vk_id, TOP_NUM)[1]
        if audios_top:
            bot.sendMessage(chat_id, text=PRE_COMMENT + audios_top + POST_COMMENT)
        return True

    def idle_main(self, bot, update):
        self.spy(bot, update)
        self.inside_idle(bot, update)

    #### settings large menu

    def check_settings_existance(self, chat_id):
        return os.path.exists('userdata/settings/%d.txt' % chat_id)

    def set_settings(self, chat_id, d=-1):
        try:
            f = open('userdata/settings/' + str(chat_id) + '.txt', 'w')
            if d == -1:
                d = self.DEFAULT_SETTINGS
            f.write(str(d))
        except:
            return False
        return True

    def get_settings(self, chat_id):
        try:
            f = open('userdata/settings/' + str(chat_id) + '.txt')
            d = eval(f.read())
        except:
            f = open('userdata/settings/' + str(chat_id) + '.txt', 'w')
            d = self.DEFAULT_SETTINGS
            f.write(str(d))
        return d

    def set_settings_field(self, chat_id, field, value):
        try:
            d = self.get_settings(chat_id)
            d[field] = value
            return self.set_settings(chat_id, d)
        except:
            return False

    def button(self, bot, update, txt=None):
        query = update.callback_query
        if not txt:
            txt = query.data
        chat_id = query.message.chat_id

        if txt in {'download_concerts_no', 'download_concerts_vk_no'}:
            bot.sendMessage(chat_id, 'Хорошо, в другой раз.')
            return True
        if txt == 'feedback':
            self.set_settings_field(chat_id, 'chat_state', 'feedback')
            bot.sendMessage(chat_id, 'Классно, можешь писать')
            return True
        if txt == 'download_concerts_yes':
            user_settings = self.get_settings(chat_id)
            vk_uid = user_settings['vk']['id']
            if not vk_uid:
                self.msg_with_buttons(bot=bot,
                                      update=update,
                                      text='Для получения списка концертов необходимо указать профиль VK. Можешь сейчас это сделать?',
                                      options=[['Да', 'download_concerts_vk_yes'], ['Нет', 'download_concerts_vk_no']],
                                      chat_id=chat_id)
                return True
            self.download_and_show(bot, chat_id)
            return True
        if txt == 'download_concerts_vk_yes':
            bot.sendMessage(chat_id, 'Кидай ссылку на себя вконтакте. Или id. Или никнейм.')
            self.set_settings_field(chat_id, 'chat_state', 'download_concerts_vk_yes_waiting')
            return True
        text, options = self.settings_menu(txt, chat_id, bot)
        if len(text) > 0: self.msg_with_buttons(bot, update, text, options, chat_id, query.message.message_id)
        return True

    def download_and_show(self, bot, chat_id):
        bot.sendMessage(chat_id, 'типа скачал')

    def settings_menu(self, q, chat_id, bot):
        # ad-hoc func for inline button(): defines which text and buttons to send depending on entry inline query
        text = ''
        options = []
        if not self.check_settings_existance(chat_id):
            self.set_settings(chat_id)
        d = self.get_settings(chat_id)
        if q == 's':
            text = 'Текущие настройки:'
            text += '\n* Города: '
            if len(d['city']) == 0:
                text += 'все'
            else:
                text += ", ".join(d['city'])
            text += '\n* Профиль'
            if d['vk']['id'] is None:
                text += ' на vk.com: не указан'
            else:
                text += ': ' + d['vk']['name'] + ' (https://vk.com/id' + str(d['vk']['id']) + ')'
            text += '\n* Отслеживаемые исполнители: '
            if not d['follow']:
                text += 'пусто'
            elif len(d['follow']) > 4:
                text += str(len(d['follow'])) + ' исполнителей'
            else:
                text += '; '.join(d['follow'])
            text += '\n* Не отслеживаемые исполнители: '
            if not d['unfollow']:
                text += 'пусто'
            elif len(d['unfollow']) > 4:
                text += str(len(d['unfollow'])) + ' исполнителей'
            else:
                text += '; '.join(d['unfollow'])
            options.append(['Города', 'city'])
            options.append(['Профиль vk', 'vk'])
            options.append(['Список исполнителей', 'artists'])
        # cities story
        elif q == 's-city':
            text = 'Здесь ты можешь изменить список городов с интересующими концертами'
            options.append(['Добавить', 'add'])
            if len(d['city']) > 0:
                text += '. Выбранные города: %s' % ', '.join(d['city'])
                options.append(['Удалить', 'del'])
                options.append(['Удалить все', 'delall'])
        elif q == 's-city-add':
            self.set_settings_field(chat_id, 'chat_state', 'settings-city-add')
            bot.sendMessage(chat_id,
                            text='Какой город добавить? Если хочешь, можешь написать сразу несколько, но тогда используй знаки препинания, например:\nМосква, Санкт-Петербург, Нижний Новгород')
        elif q == 's-city-del':
            text = 'В каком городе концерты более не отслеживать?'
            for city in d['city']:
                options.append([city, city])
        elif q == 's-city-delall':
            d['city'] = []
            self.set_settings(chat_id, d)
            text = 'Список городов очищен'
        elif q.startswith('s-city-del-'):
            city_to_delete = q[11:]
            cities = set(d['city'])
            try:
                cities.remove(city_to_delete)
            except:
                pass
            d['city'] = list(cities)
            self.set_settings(chat_id, d)
            text = 'Город %s удален из списка интересующих городов' % city_to_delete
        # vk profile story
        elif q == 's-vk':
            if d['vk']['id'] is not None:
                text = 'Твой профиль: ' + d['vk']['name'] + ' (https://vk.com/id' + str(d['vk']['id']) + ')'
                options.append(['Изменить', 'set'])
                options.append(['Удалить', 'del'])
            else:
                text = 'Профиль не указан'
                options.append(['Установить', 'set'])
        elif q == 's-vk-set':
            self.set_settings_field(chat_id, 'chat_state', 'settings-vk-set')
            bot.sendMessage(chat_id, text='Кидай ссылку на себя вконтакте. Или id. Или никнейм.')
        elif q == 's-vk-del':
            d['vk']['id'] = None
            self.set_settings(chat_id, d)
            try:
                os.remove('userdata/concerts/%d.json' % chat_id)
            except:
                pass
            text = 'Профиль удалён. Можешь указать его вновь в любой момент, когда захочется'
        # artists set story
        elif q == 's-artists':
            text = 'Вноси изменения в список исполнителей, подгруженный из твоих аудио вк. Укажи, кого стоит отслеживать, даже если его нет в списке аудио вк, и кого не стоит, несмотря на то, что он там есть. '
            options.append(['Отслеживать', 'follow'])
            options.append(['Не отслеживать', 'unfollow'])
        elif q == 's-artists-follow':
            text = 'Текущий список исполнителей, за которыми стоит следить несмотря на их отсутствие в списке аудио вк'
            options.append(['Добавить', 'add'])
            if len(d['follow']) == 0:
                text += ', пуст'
            else:
                text += ': %s' % ', '.join(d['follow'])
                options.append(['Удалить', 'del'])
                options.append(['Удалить все', 'delall'])
        elif q == 's-artists-follow-add':
            self.set_settings_field(chat_id, 'chat_state', 'settings-follow-add')
            bot.sendMessage(chat_id,
                            text='Каких исполнителей стоит дополнительно отслеживать? Если хочешь, можешь написать сразу несколько, но тогда обязательно раздели их точкой с запятой, иначе я их не найду. Например,\nBeatles; Rolling Stones')
        elif q == 's-artists-follow-del':
            text = 'Чьи концерты больше не надо дополнительно отслеживать?'
            for artist in d['follow']:
                options.append([artist, artist])
        elif q == 's-artists-follow-delall':
            d['follow'] = []
            self.set_settings(chat_id, d)
            text = 'Список исполнителей для дополнительного отслеживания очищен'
        elif q == 's-artists-unfollow':
            text = 'Текущий список исполнителей, чьи концерты не нужно показывать'
            options.append(['Добавить', 'add'])
            if len(d['unfollow']) == 0:
                text += ', пуст'
            else:
                text += ': %s' % ', '.join(d['unfollow'])
                options.append(['Удалить', 'del'])
                options.append(['Удалить все', 'delall'])
        elif q == 's-artists-unfollow-add':
            self.set_settings_field(chat_id, 'chat_state', 'settings-unfollow-add')
            bot.sendMessage(chat_id,
                            text='Чьи концерты стоит скрывать из выдачи? Если хочешь, можешь написать сразу несколько, но тогда обязательно раздели их точкой с запятой, иначе я их не найду. Например,\nBeatles; Rolling Stones')
        elif q == 's-artists-unfollow-del':
            text = 'Чьи концерты больше не надо скрывать из выдачи?'
            for artist in d['unfollow']:
                options.append([artist, artist])
        elif q == 's-artists-unfollow-delall':
            d['unfollow'] = []
            self.set_settings(chat_id, d)
            text = 'Список исполнителей для дополнительного отслеживания очищен'

        # adding path for every command
        for o in options:
            o[1] = q + '-' + str(o[1])
        # adding 'back' button to all menu's but start menu
        if q != 's':
            options = [['⬅', '-'.join(q.split('-')[:-1])]] + options
        return (text, options)

    def slash_settings(self, bot, update):
        text, options = self.settings_menu('s', update.message.chat_id, bot)
        self.msg_with_buttons(bot, update, text, options)

    def inlinequery(self, bot, update):
        query = update.inline_query.query
        results = list()
        chat_id = update.inline_query.from_user.id

        resp = self.get_resp_for_idle_text(query, chat_id=chat_id)
        results.append(
            InlineQueryResultArticle(id=uuid4(), title=resp, input_message_content=InputTextMessageContent(resp)))
        update.inline_query.answer(results)

    def main(self):
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(self.TG_TOKEN)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher
        updater.dispatcher.add_handler(CallbackQueryHandler(self.button))

        # on different commands - answer in Telegram
        dp.add_handler(CommandHandler("start", self.slash_start), group=0)
        dp.add_handler(CommandHandler("help", self.slash_help), group=0)
        dp.add_handler(CommandHandler("feedback", self.slash_feedback), group=0)
        dp.add_handler(CommandHandler("about", self.slash_about), group=0)
        dp.add_handler(CommandHandler("settings", self.slash_settings), group=0)

        # on noncommand message
        dp.add_handler(MessageHandler(Filters.text, self.idle_main))
        dp.add_handler(InlineQueryHandler(self.inlinequery))

        # log all errors
        dp.add_error_handler(self.slash_error)

        # Start the Bot
        updater.start_polling()

        # Run the bot
        updater.idle()


class TelegramWrapperDefault(TelegramWrapper):
    def __init__(self):
        TG_TOKEN = json.loads(open(get_full_path('telegram_wrapper/workdata/credentials.json')).read())['tg_bot_token']
        log_filename = get_full_path('telegram_wrapper/workdata/log.txt')
        feedback_filename = get_full_path('telegram_wrapper/workdata/feedback.txt')
        TelegramWrapper.__init__(self, TG_TOKEN=TG_TOKEN, log_filename=log_filename,
                                 feedback_filename=feedback_filename)
