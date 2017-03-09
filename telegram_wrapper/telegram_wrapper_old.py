# coding: utf-8
# telegram
import json
import os
from time import strftime  # для логгирования

from numpy import cumsum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from concerts import SeatscanGrabber
from vkontakte import VKGrabber

# consts
MSG_LIMIT_TELEGRAM = 4095
CREATOR_CHAT_ID = 34600304
TG_TOKEN = '228172322:AAG620f2nZUQqMxAf4ux9SxrFcyDZmFmuzQ'
HELP_TEXT = u"""Я покажу тебе:
🔸 ближайшие концерты присланной тобой группы
🔸 твоих друзей вк, которые слушают этого исполнителя и могут составить тебе компанию
🔸 музыкальный портрет человека =) кинь на него ссылку или, если это твой друг, просто напиши его имя
🔸 список концертов всех исполнителей из твоего плейлиста в выбранных в настройках городах /concerts

Настроить бота можно здесь: /settings"""
# 🔸 концерты, которые будут интересны и тебе, и указанным тобой друзьям /together
ABOUT_TEXT = u"""Concerts worth spreading"""
START_TEXT = u"🙋 Привет! Я помогу найти интересные тебе концерты и компанию твоих друзей на них.\nТеперь получать удовольствие от концертов стало проще!)\n\n" + HELP_TEXT + "\n\nЕсли ты захочешь с кем-то поделиться этим ботом - можешь скинуть эту ссылку:\nhttp://telegra.ph/YourConcertsBot-12-02"

# help_funcs
folder = 'concerts/'
artist_2_url_filename = folder + 'seatscan_artist_2_url_2.json'
artist_2_artist_filename = folder + 'seatscan_artist_2_artist.json'
artists_failed_filename = folder + 'seatscan_artists_that_failed.txt'
ssg = SeatscanGrabber(artist_2_url_json_filename=artist_2_url_filename,
                      artist_2_artist_json_filename=artist_2_artist_filename,
                      artists_that_failed_on_seatscan_filename=artists_failed_filename)
VK_PRIVATE_CREDENTIALS = json.loads(open('vkontakte/credentials.json').read())
vk_parser = VKGrabber(credentials=VK_PRIVATE_CREDENTIALS)


def split_msg(txt, size=MSG_LIMIT_TELEGRAM, delim='\n'):
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
        return [resp] + split_msg(left, size, delim)


def send_splitted_msg(bot, chat_id, msg, msg_limit=4095, reply_markup=-1, delim='\n'):
    l = split_msg(msg, msg_limit, delim)
    if len(l) > 3: bot.sendMessage(chat_id, text='Текст слишком большой и будет обрезан')
    if reply_markup == -1:
        for r in l[:3]:
            bot.sendMessage(chat_id, text=r)
    else:
        for r in l[:3]:
            bot.sendMessage(chat_id, text=r, reply_markup=reply_markup)


def msg_with_buttons(bot, update, text, options, chat_id=-1, message_id=-1):
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


def spy(bot, update, send2creator=True):
    try:
        user = update.message.from_user
    except:
        print('spy: nothing to get')
        return (False)

    if str(user.username) == 'NikitaKuznetsov': return (False)

    txt = update.message.text

    logtxt = ["Слежка time!"
        , "Time: " + strftime("%Y-%m-%d %H:%M:%S")
        , "User: " + str(user.first_name) + ' ' + str(user.last_name)
        , "Username: @" + str(user.username)
        , "Chat_id: " + str(update.message.chat_id)
        , "Text: " + txt]

    if send2creator:
        bot.sendMessage(CREATOR_CHAT_ID, text="\n".join(logtxt))
    text_file = open('log.txt', "a")
    text_file.write("\n" + "; ".join(logtxt))
    text_file.close()


def slash_feedback(bot, update):
    spy(bot, update)
    chat_id = update.message.chat_id
    lang_chat = 'ru'
    txt = update.message.text
    if txt[:9] == '/feedback' and len(txt) > 9:
        bot.sendMessage(chat_id, text='Спасибо, с интересом ознакомлюсь!')
    else:
        bot.sendMessage(chat_id,
                        text="Люблю отзывчивых людей. Пиши свои пожелания, впечатления и предложения прямо сюда, начиная сообщение меткой /feedback, я обязательно их получу и прочитаю. Спасибо!")


def slash_start(bot, update):
    spy(bot, update)
    chat_id = update.message.chat_id
    bot.sendMessage(chat_id, text=START_TEXT)


def slash_help(bot, update):
    spy(bot, update)
    chat_id = update.message.chat_id
    bot.sendMessage(chat_id, text=HELP_TEXT)


def slash_about(bot, update):
    spy(bot, update)
    bot.sendMessage(update.message.chat_id, text=ABOUT_TEXT)


def slash_error(bot, update, error):
    logtxt = ('Update "%s" caused error "%s"' % (update, error))
    # with open('log.txt', "a") as text_file:
    #    text_file.write("\n" + logtxt)
    if 'Bad Request: Input message content is not specified' not in logtxt:
        print(logtxt)


def slash_concerts(bot, update):
    spy(bot, update)
    chat_id = update.message.chat_id
    filename = 'userdata/concerts/' + str(chat_id) + '.json'
    delim = '\n---\n'
    if os.path.exists(filename):
        concerts = json.loads(open(filename).read())
        user_settings = get_settings(chat_id)
        # удаляем лишнее
        unfollowed = [artist.lower() for artist in user_settings['unfollow']]
        if len(unfollowed)>0:
            concerts = [concert for concert in concerts if concert['artist'].lower() not in unfollowed]
        # формируем ответ
        resp = ssg.get_text_from_concerts_list(events=concerts, cities=user_settings['city'], delim=delim)
        if len(resp) == 0:
            bot.sendMessage(update.message.chat_id, text='Нет концертов исполнителей в выбранных городах')
            return False
        bot.sendMessage(update.message.chat_id, text='🎷 Твоя индивидуальная афиша музыкальных концертов:')
        send_splitted_msg(bot, chat_id, resp, delim=delim)
    else:
        resp = 'База концертов по твоим исполнителям ещё не собрана, это может занять время. Начать скачивание?'
        msg_with_buttons(bot, update, text=resp,
                         options=[['Да', 'download_concerts_yes'], ['Нет', 'download_concerts_no']])


def set_vk_profile(bot, chat_id, text):
    vk_info = vk_parser.get_user_info(text)
    vk_id = vk_info['uid']
    if not vk_id:
        bot.sendMessage(chat_id, text='Укажи свой профиль в вк. Указанная ссылка невалидна. Попробуй ещё раз')
        return False
    d = get_settings(chat_id)
    d['vk']['id'] = vk_id
    d['vk']['name'] = vk_info['first_name'] + ' ' + vk_info['last_name']
    d['vk']['url'] = 'https://vk.com/id' + str(vk_id)
    d['chat_state'] = ''
    set_settings(chat_id, d)
    bot.sendMessage(chat_id, text='Профиль обновлён. Ссылка на тебя: https://vk.com/id%d' % vk_id)
    TOP_NUM = 10
    PRE_COMMENT = 'Маленький бонус, топ-%d исполнителей по твоим аудиозаписям:' % TOP_NUM
    POST_COMMENT = 'Ты можешь посмотреть топ и по другим пользователям VK, просто кидай сюда на них ссылку. Именно ссылку'
    audios_top = get_top_artists_string(vk_id, TOP_NUM, PRE_COMMENT, POST_COMMENT)
    if audios_top:
        bot.sendMessage(chat_id, text=audios_top)
    return True


def get_top_artists_string(query, top_num=10, pre_comment=None, post_comment=None):
    audios_top = vk_parser.get_artists_popularity(query)
    if not audios_top:
        return None
    resp = '\n'.join([artist[0] + ' - ' + str(artist[1]) for artist in audios_top[:top_num]])
    if pre_comment:
        resp = pre_comment + '\n\n' + resp
    if post_comment:
        resp = resp + '\n\n' + post_comment
    return resp


def inside_idle(bot, update, text=-1, chat_id=-1):
    TEXT_IF_NOTHING_FOUND = u'Ничего не найдено. Попробуйте изменить запрос'

    if text == -1:
        text = update.message.text
    if chat_id == -1:
        chat_id = update.message.chat_id
    d = get_settings(chat_id)
    chat_state = d['chat_state']

    if chat_state == 'settings-city-add':
        txt = text.replace(',', ' ').replace(';', ' ').replace('.', ' ').replace('\n', ' ').split()
        d['city'] = list(set([i.capitalize() for i in d['city'] + txt]))
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
        set_settings(chat_id, d)
        resp = 'Список городов с интересующими концертами обновлён. Теперь он выглядит так:\n' + ', '.join(d['city'])
        bot.sendMessage(chat_id, text=resp)
    elif chat_state == 'settings-follow-add':
        txt = text.replace(',', ' ').replace(';', ' ').replace('.', ' ').replace('\n', ' ').split()
        d['follow'] = list(set([i.capitalize() for i in d['follow'] + txt]))
        d['chat_state'] = ''
        set_settings(chat_id, d)
        resp = 'Список исполнителей, за которыми нужно дополнительно к вк следить, обновлён. Теперь он выглядит так:\n' + ', '.join(
            d['follow'])
        bot.sendMessage(chat_id, text=resp)
    elif chat_state == 'settings-unfollow-add':
        txt = text.replace(',', ' ').replace(';', ' ').replace('.', ' ').replace('\n', ' ').split()
        d['unfollow'] = list(set([i.capitalize() for i in d['unfollow'] + txt]))
        d['chat_state'] = ''
        set_settings(chat_id, d)
        resp = 'Список исполнителей, чьи концерты не нужно отслеживать, обновлён. Теперь он выглядит так:\n' + ', '.join(
            d['unfollow'])
        bot.sendMessage(chat_id, text=resp)
    elif chat_state == 'settings-vk-set':
        set_vk_profile(bot, chat_id, text)
    elif chat_state == 'download_concerts_vk_yes_waiting':
        if set_vk_profile(bot, chat_id, text):
            download_and_show(bot, chat_id)
    else:
        if 'vk.com/' in text:
            TOP_NUM = 10
            resp = get_top_artists_string(text, TOP_NUM,
                                          pre_comment='Топ-%d исполнителей по кол-ву треков:' % TOP_NUM) or TEXT_IF_NOTHING_FOUND
        else:
            concerts = ssg.get_concerts(text, log_print_freq=1)
            resp = ssg.get_text_from_concerts_list(concerts, d['city'])
            if resp is None or resp.strip() == '':
                resp = u'Концертов не найдено :('
        bot.sendMessage(chat_id, text=resp)


def idle_main(bot, update):
    spy(bot, update)
    inside_idle(bot, update)


def download_and_show(bot, chat_id):
    TEXT_IF_NO_VK_AUDIOS = 'Видимо, у тебя закрыты для просмотра аудиозаписи и я не смогу собрать нужную информацию'
    TEXT_IF_NO_AUDIOS = 'Видимо, у тебя закрыты для просмотра аудиозаписи и я не смогу собрать нужную информацию'
    TEXT_IF_EMPTY_CITIES = 'Рекомендую предварительно указать города в /settings, чтобы отображались только подходящие концерты'
    # качаем список аудио вк
    user_settings = get_settings(chat_id)
    artists = vk_parser.get_artists(user_settings['vk']['id'])
    print(len(artists))
    if TEXT_IF_NO_AUDIOS != '' and not artists:
        bot.sendMessage(chat_id, TEXT_IF_NO_VK_AUDIOS)
        return True
    artists = set([artist.lower() for artist in artists])
    # редактируем его с помощью кастомных списков
    artists.update(set(user_settings['follow']))
    for artist2unfollow in user_settings['unfollow']:
        if artist2unfollow in artists:
            artists.remove(artist2unfollow)
    # получаем список концертов и отправляем его с учётом выбранных городов
    concerts = ssg.get_concerts(artists, log_print_freq=1, save_to_json_filename='userdata/concerts/%d.json' % chat_id)
    send_splitted_msg(bot, chat_id, ssg.get_text_from_concerts_list(concerts, user_settings['city']))
    if TEXT_IF_EMPTY_CITIES != '' and len(user_settings['city']) == 0:
        bot.sendMessage(chat_id, TEXT_IF_EMPTY_CITIES)


#### settings large menu

DEFAULT_SETTINGS = {
    'city': []
    , 'friends': []
    , 'sort_type': 'date'
    , 'sort_order': 'az'
    , 'vk': {'id': None, 'last_update': None, 'name': None, 'url': None}
    , 'chat_state': ''
    , 'follow': []
    , 'unfollow': []
}


def check_settings_existance(chat_id):
    return os.path.exists('userdata/settings/%d.txt' % chat_id)


def set_settings(chat_id, d=-1):
    try:
        f = open('userdata/settings/' + str(chat_id) + '.txt', 'w')
        if d == -1:
            d = DEFAULT_SETTINGS
        f.write(str(d))
    except:
        return False
    return True


def get_settings(chat_id):
    try:
        f = open('userdata/settings/' + str(chat_id) + '.txt')
        d = eval(f.read())
    except:
        f = open('userdata/settings/' + str(chat_id) + '.txt', 'w')
        d = DEFAULT_SETTINGS
        f.write(str(d))
    return d


def set_settings_field(chat_id, field, value):
    try:
        d = get_settings(chat_id)
        d[field] = value
        return set_settings(chat_id, d)
    except:
        return False


def button(bot, update, txt=None):
    query = update.callback_query
    if not txt:
        txt = query.data
    chat_id = query.message.chat_id

    if txt.startswith('vk.com/'):
        inside_idle(bot, update, txt, chat_id)
        return True
    if txt.startswith(str(CREATOR_CHAT_ID)+' '):
        inside_idle(bot, update, txt, chat_id)
        return True
    if txt in {'download_concerts_no', 'download_concerts_vk_no'}:
        bot.sendMessage(chat_id, 'Хорошо, в другой раз.')
        return True
    if txt == 'download_concerts_yes':
        user_settings = get_settings(chat_id)
        vk_uid = user_settings['vk']['id']
        if not vk_uid:
            msg_with_buttons(bot=bot, update=update,
                             text='Для получения списка концертов необходимо указать профиль VK. Можешь сейчас это сделать?',
                             options=[['Да', 'download_concerts_vk_yes'], ['Нет', 'download_concerts_vk_no']],
                             chat_id=chat_id)
            return True
        download_and_show(bot, chat_id)
        return True
    if txt == 'download_concerts_vk_yes':
        bot.sendMessage(chat_id, 'Кидай ссылку на себя вконтакте. Или id. Или никнейм.')
        set_settings_field(chat_id, 'chat_state', 'download_concerts_vk_yes_waiting')
        return True
    text, options = settings_menu(txt, chat_id, bot)
    if len(text) > 0: msg_with_buttons(bot, update, text, options, chat_id, query.message.message_id)
    return True


def settings_menu(q, chat_id, bot):
    # ad-hoc func for inline button(): defines which text and buttons to send depending on entry inline query
    text = ''
    options = []
    if not check_settings_existance(chat_id):
        set_settings(chat_id)
    d = get_settings(chat_id)
    if q == 's':
        text = 'Текущие настройки:'
        text += '\n* Города: '
        if len(d['city']) == 0:
            text += 'все'
        else:
            text += ", ".join(d['city'])
        if d['vk']['id'] is None:
            text += '\n* Профиль на vk.com: не указан'
        else:
            text += '\n* Профиль: ' + d['vk']['name'] + ' (https://vk.com/id' + str(d['vk']['id']) + ')'
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
        set_settings_field(chat_id, 'chat_state', 'settings-city-add')
        bot.sendMessage(chat_id, text='Какой город добавить? Если хочешь, можешь написать сразу несколько')
    elif q == 's-city-del':
        text = 'В каком городе концерты более не отслеживать?'
        for city in d['city']:
            options.append([city, city])
    elif q == 's-city-delall':
        d['city'] = []
        set_settings(chat_id, d)
        text = 'Список городов очищен'
    elif q.startswith('s-city-del-'):
        city_to_delete = q[11:]
        cities = set(d['city'])
        try:
            cities.remove(city_to_delete)
        except:
            pass
        d['city'] = list(cities)
        set_settings(chat_id, d)
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
        set_settings_field(chat_id, 'chat_state', 'settings-vk-set')
        bot.sendMessage(chat_id, text='Кидай ссылку на себя вконтакте. Или id. Или никнейм.')
    elif q == 's-vk-del':
        d['vk']['id'] = None
        set_settings(chat_id, d)
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
        set_settings_field(chat_id, 'chat_state', 'settings-follow-add')
        bot.sendMessage(chat_id,
                        text='Каких исполнителей стоит дополнительно отслеживать? Если хочешь, можешь написать сразу несколько')
    elif q == 's-artists-follow-del':
        text = 'Чьи концерты больше не надо дополнительно отслеживать?'
        for artist in d['follow']:
            options.append([artist, artist])
    elif q == 's-artists-follow-delall':
        d['follow'] = []
        set_settings(chat_id, d)
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
        set_settings_field(chat_id, 'chat_state', 'settings-unfollow-add')
        bot.sendMessage(chat_id,
                        text='Чьи концерты стоит скрывать из выдачи? Если хочешь, можешь написать сразу несколько')
    elif q == 's-artists-unfollow-del':
        text = 'Чьи концерты больше не надо скрывать из выдачи?'
        for artist in d['unfollow']:
            options.append([artist, artist])
    elif q == 's-artists-unfollow-delall':
        d['unfollow'] = []
        set_settings(chat_id, d)
        text = 'Список исполнителей для дополнительного отслеживания очищен'

    # adding path for every command
    for o in options:
        o[1] = q + '-' + str(o[1])
    # adding 'back' button to all menu's but start menu
    if q != 's':
        options = [['⬅', '-'.join(q.split('-')[:-1])]] + options
    return (text, options)


def slash_settings(bot, update):
    text, options = settings_menu('s', update.message.chat_id, bot)
    msg_with_buttons(bot, update, text, options)


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TG_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", slash_start), group=0)
    dp.add_handler(CommandHandler("help", slash_help), group=0)
    dp.add_handler(CommandHandler("feedback", slash_feedback), group=0)
    dp.add_handler(CommandHandler("about", slash_about), group=0)
    dp.add_handler(CommandHandler("settings", slash_settings), group=0)
    dp.add_handler(CommandHandler("concerts", slash_concerts), group=0)

    # on noncommand message
    dp.add_handler(MessageHandler(Filters.text, idle_main))

    # log all errors
    dp.add_error_handler(slash_error)

    # Start the Bot
    updater.start_polling()

    # Run the bot
    updater.idle()


### run
main()

# concerts - афиша твоих концертов
# settings - настройки
# help - справка
# feedback - поделиться отзывом, предложением, критикой
# about - о боте и разработчике

# together - концерты вместе с друзьями
# stat - популярные исполнители
# start - начать с начала
