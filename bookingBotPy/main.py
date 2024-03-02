import telebot
from telebot import types
import requests
import json
import config


class User:
    def __init__(self, date=None, room=None, hours=None, accessFlag=0, dateStr=None):
        self.date = date
        self.room = room
        self.hours = hours
        self.accessFlag = accessFlag
        self.dateStr = dateStr

    def setDate(self, date):
        self.date = date

    def setRoom(self, room):
        self.room = room

    def setHours(self, hours):
        self.hours = hours

    def setAccessFlag(self, flag):
        self.accessFlag = flag

    def setDateStr(self, dateStr):
        self.dateStr = dateStr


bot = telebot.TeleBot(config.BOT_TOKEN)
users = {}


@bot.message_handler(commands=['start'])
def start_message(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reg_button = types.KeyboardButton(text="Отправить номер телефона",
                                      request_contact=True)
    keyboard.add(reg_button)
    bot.send_message(message.chat.id, 'Добро пожаловать в SCI-FI Booking bot!\n\
Здесь вы можете забронировать комнату в "нейм организации" по адресу "адрес" на удобное для вас время.\nБронирование доступно на 7 дней, начиная с текущего.',
                     reply_markup=keyboard)
    bot.send_message(message.chat.id, 'Для дальнейшей работы, мы должны узнать твой номер телефона.')
    users.update({message.chat.id: User()})


@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    code = postChatId(message, message.contact.phone_number)  # отправляем телефон и chat id
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Выбрать дату'))
    keyboard.add(types.KeyboardButton('Информация об организации'))
    if code == 459:
        bot.send_message(message.chat.id, 'Ваш номер телефона уже записан!', reply_markup=keyboard)
    elif code == 200:
        bot.send_message(message.chat.id, 'Отлично!', reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'Что-то пошло не так, ошибка ' + str(code))
        return


def postChatId(message, phone):
    try:
        res = requests.get(f'{config.URL_SERVER}/bot/postPhone?phone={phone}&chatId={message.chat.id}')
        if (message.contact.last_name == None):
            lastname = ""
        else:
            lastname = message.contact.last_name
        print(message.contact.phone_number, message.contact.first_name, message.contact.last_name, "Post chat id:", res)
        data = json.loads(res.text)
        if data == -1:
            return 459
        return res.status_code
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, 'Неполадки с сервером, попробуйте повторить бронирование позже.')
        return 500


def chooseDate(message):
    keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 'Введите желаемую дату в формате ДД.ММ.ГГГГ', reply_markup=keyboard)
    bot.register_next_step_handler(message, chooseRoom)


def chooseRoom(message):
    if (message.text == '/go'):
        goHandler(message)
        return
    global users
    users.get(message.chat.id).setDate(message.text.strip())
    bot.send_message(message.chat.id, f'Вот какие комнаты у нас имеются:\n\n\
ROOM #1\n{config.DISC_ROOM1}\n\n\
ROOM #2\n{config.DISC_ROOM2}\n\n\
ROOM #3\n{config.DISC_ROOM3}\n\n\
ROOM #4\n{config.DISC_ROOM4}\n\n\
ROOM #5\n{config.DISC_ROOM5}')
    bot.send_message(message.chat.id, ('Введите интересующий номер комнаты, чтобы узнать, на какие часы она свободна.'))
    bot.register_next_step_handler(message, setRoom)


def setRoom(message):
    try:
        room = int(message.text.strip())
        if (room < 1 or room > 5):
            raise ValueError('Another num')
        global users
        users.get(message.chat.id).setRoom(room)
    except ValueError as e:
        print(e)
        bot.send_message(message.from_user.id, 'Введите число от 1 до 5')
        bot.register_next_step_handler(message, setRoom)
        return
    getDate(message)


def getDate(message):
    try:
        global users
        res = requests.get(
            f'{config.URL_SERVER}/bot/getDate?dateStr={users.get(message.chat.id).date}&room={users.get(message.chat.id).room}')
        data = json.loads(res.text)  # объект со всеми парами ключ-значение

        if res.status_code != 200:
            bot.reply_to(message, 'что то не так, ошибка ' + str(res.status_code) + '\nПопробуйте еще раз.')
            bot.register_next_step_handler(message, getDate)
            return
        if (data["codeAnswer"] != 0):
            bot.send_message(message.chat.id,
                             'Ой, что-то не так с датой, возможно, это время прошло, или оно наступит не скоро.')
            chooseDate(message)
        else:
            users.get(message.chat.id).setDateStr(data["dateStr"])
            showHours(message)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, 'Неполадки с сервером, попробуйте повторить бронирование позже.')


def showHours(message):
    kbrd = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Забронировать', callback_data='reservation')
    btn2 = types.InlineKeyboardButton('Назад', callback_data='back')
    kbrd.add(btn1)
    kbrd.add(btn2)

    bot.send_message(message.chat.id, f'Вот, что свободно на эту дату\n{users.get(message.chat.id).dateStr}.\n.\nНа одну бронь можно выбирать только \
    один временной промежуток', reply_markup=kbrd)


@bot.callback_query_handler(func=lambda c: c.data == 'reservation')
def process_callback_button1(callback_query: types.CallbackQuery):
    bot.send_message(callback_query.from_user.id, 'Хорошо, введите желаемый временной проежуток в формате час-час.')
    bot.answer_callback_query(callback_query.id, "Answer is Yes")
    bot.register_next_step_handler(callback_query.message, setHours)


@bot.callback_query_handler(func=lambda c: c.data == 'back')
def process_callback_button2(callback_query: types.CallbackQuery):
    bot.answer_callback_query(callback_query.id, "Answer is Yes")
    chooseDate(callback_query.message)


def setHours(message):
    hours = message.text
    global users
    users.get(message.chat.id).setHours(hours)
    users.get(message.chat.id).setAccessFlag(1)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Подтверждаю'))
    keyboard.add(types.KeyboardButton('Назад'))

    date = users.get(message.chat.id).date
    room = users.get(message.chat.id).room
    hours = users.get(message.chat.id).hours

    bot.send_message(message.from_user.id, f'Отлично! Проверьте корректность введенных данных\n\
 Дата: {date}\n\
 Комната: {room}\n\
 Время: {hours}\n\
Для подтверждения нажмите "Подтверждаю".', reply_markup=keyboard)


def postReservation(message):
    global users
    date = users.get(message.chat.id).date
    room = users.get(message.chat.id).room
    hours = users.get(message.chat.id).hours
    try:
        res = requests.post(f'{config.URL_SERVER}/bot/postReservation',
                            json={'dateStr': f'{date}', 'room': f'{room}', 'hours': f'{hours}',
                                  'userId': f'{message.chat.id}'})
        data = json.loads(res.text)
        keyboard = types.ReplyKeyboardRemove()
        if res.status_code != 200:
            bot.send_message(message.from_user.id, 'Что-то не так, ошибка ' + str(res.status_code))
        print('data["codeAnswer"] ', data["codeAnswer"])
        if data["codeAnswer"] == 0:
            bot.send_message(message.from_user.id, f'Ура! Бронирование успешно. Ваш ID брони: {data["bookId"]}.\n\
    Он понадобится уже на месте.', reply_markup=keyboard)
            users.pop(message.chat.id)
        else:
            bot.send_message(message.from_user.id, 'Ошибка, проверьте введенные данные.', reply_markup=keyboard)
            getDate(message)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, 'Неполадки с сервером, попробуйте повторить бронирование позже.')


@bot.message_handler(commands=['go'])
def goHandler(message):
    try:
        res = requests.get(f'{config.URL_SERVER}/bot/checkHasPhone?chatId={message.chat.id}')
        print(res.text)
        if res.text == "-1":
            start_message(message)
            return
        global users
        if not message.chat.id in users:
            print('new user session')
        else:
            print('old user session')
            users.pop(message.chat.id)
        users.update({message.chat.id: User()})

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton('Выбрать дату'))
        keyboard.add(types.KeyboardButton('Информация об организации'))
        bot.send_message(message.chat.id, 'Добро пожаловать в SCI-FI Booking bot!\n\
    Здесь вы можете забронировать комнату в "нейм организации" по адресу "адрес" на удобное для вас время.\nБронирование доступно на 7 дней, начиная с текущего.',
                         reply_markup=keyboard)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, 'Неполадки с сервером, попробуйте повторить бронирование позже.')


@bot.message_handler(content_types=['text'])
def textResponse(message):
    global users
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Выбрать дату'))
    if message.text == 'Выбрать дату':
        if users.get(message.chat.id) is not None:
            chooseDate(message)
    elif message.text == 'Подтверждаю' and users.get(message.chat.id) is not None and users.get(
            message.chat.id).accessFlag == 1:
        users.get(message.chat.id).setAccessFlag(0)
        postReservation(message)
    elif message.text == 'Информация об организации':
        bot.send_message(message.chat.id, config.ORG_INFO, reply_markup=keyboard)
    elif message.text == 'Назад' and users.get(message.chat.id) is not None and users.get(
            message.chat.id).accessFlag == 1:
        chooseDate(message)
    else:
        bot.send_message(message.chat.id, 'Я такого не знаю')


bot.polling(none_stop=True)
