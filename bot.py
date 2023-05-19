# -*- coding: utf-8 -*-

import logging
import threading
from datetime import datetime
import time
from random import uniform
import json
import re

import telebot
from telebot import types
import monobank
import pause

from config import bot_token, mono_bank_api_key
from markups import AdminKeyboard, ClientKeyboard, ManagersKeyboard, PartnersKeyboard
from db import Database
from utils import top_up_balance_on_website, services_dict, get_info_about_balance_kahowka

bot = telebot.TeleBot(bot_token, parse_mode="HTML")
db = Database('bot_data.db')
client_keyboard = ClientKeyboard()
managers_keyboard = ManagersKeyboard()
partners_keyboard = PartnersKeyboard()
admin_keyboard = AdminKeyboard()
mono = monobank.Client(token=mono_bank_api_key)
mono_bank_user_info = mono.get_client_info()
logging.basicConfig(filename='logs.log', filemode='a+', format='%(asctime)s - %(levelname)s - %(message)s')
MANAGER_ID = 5802538682

try:
    payments = json.load(open("payments_in_process.json", 'r', encoding="utf-8"))
except FileNotFoundError:
    payments = {
        "in_process_balance": {},
        "in_process_web_balance": {},
        "in_process_balance_manager": {},
        "in_process_balance_partner": {}
    }
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


try:
    data = json.load(open("bot_data.json", 'r', encoding="utf-8"))
except FileNotFoundError:
    data = {
        "payments_work": True
    }
    json.dump(data, open("bot_data.json", "w", encoding="utf-8"), indent=4)


try:
    partners_data = json.load(open("partners.json", 'r', encoding="utf-8"))
except FileNotFoundError:
    partners_data = {
        "partners_transactions_amount": {}
    }
    json.dump(partners_data, open("partners.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_monobank(message):
    if message.text == "🚫 Отмена":
        start_client(message)
        return
    try:
        amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_monobank)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                client_id = account['sendId']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Monobank" расположенную ниже, Вас перенаправит в приложение , где будут заполнены все поля . Не изменяйте эти поля , особенно сумму .\n\n🔸 Если поля не заполнились автоматически, обновите приложение Monobank в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                     reply_markup=client_keyboard.monobank_link_keyboard(client_id, amount_str))
    payments['in_process_balance'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_privat24(message):
    if message.text == "🚫 Отмена":
        start_client(message)
        return
    try:
        amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_privat24)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Приват24" расположенную ниже, Вас перенаправит в приложение , где будут заполнены поля "Номер карты" и "Сумма" . Не изменяйте эти поля , особенно сумму.\n\n🔸 Если поля не заполнились автоматически, обновите приложение Приват24 в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                     reply_markup=client_keyboard.privat24_link_keyboard(number_card, amount_str))
    payments['in_process_balance'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_another_card(message):
    if message.text == "🚫 Отмена":
        start_client(message)
        return
    try:
        amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_another_card)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'📋 <b>Инструкция по оплате:</b>\nПереведите на карту <code>{number_card}</code> сумму в размере <b>{amount_str} грн.</b>\n\n❗️ <u>Переводите именно эту сумму, ни копейки больше, ни копейки меньше! Иначе система не сможет автоматически найти Ваш платеж и Вам придётся обращаться в нашу техническую поддержку для решения вопроса.</u>',
                     reply_markup=client_keyboard.another_card_link_keyboard())
    payments['in_process_balance'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def number_for_top_up_from_balance(message, service):
    if message.text == "🚫 Отмена":
        user_type = db.check_user_type(message.from_user.id)
        if user_type == "client":
            start_client(message)
        elif user_type == "partner":
            start_partner(message)
        else:
            start_manager(message)
        return
    re_pattern_1_phone = r"(?:(?:8|\+7)[\- ]?)?(?:\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}"
    re_pattern_2_phone = r"\d+"
    if service == "7telecom" or service == "mirtelecom_mobile" or service == "mtc" or service == "biline" or service == "miranda" or service == "megafon" or service == "tele2":
        number_personal_account = ''.join(re.findall(re_pattern_2_phone, message.text))
        if service == "7telecom":
            if number_personal_account.startswith("79900") or number_personal_account.startswith("9900") or \
                    number_personal_account.startswith("79902") or number_personal_account.startswith("9902"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))
        elif service == "mirtelecom_mobile":
            if number_personal_account.startswith("79901") or number_personal_account.startswith("9901"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))
        elif service == "biline":
            if number_personal_account.startswith("7906") or number_personal_account.startswith("906") or \
                    number_personal_account.startswith("7966") or number_personal_account.startswith("966"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))
        elif service == "miranda":
            if number_personal_account.startswith("7979") or number_personal_account.startswith("979") or \
                    number_personal_account.startswith("7979") or number_personal_account.startswith("966"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))                                           
        elif service == "mtc":
            if number_personal_account.startswith("7985") or number_personal_account.startswith("985"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))
        elif service == "megafon":
            if number_personal_account.startswith("7925") or number_personal_account.startswith("925"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))
        elif service == "tele2":
            if number_personal_account.startswith("7911") or number_personal_account.startswith("911"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                           number_personal_account,
                                                                                                           service))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_from_balance(
                                                   msg_obj, service))
    elif service == "msk":
        number_personal_account = ''.join(re.findall(re_pattern_2_phone, message.text))
        if number_personal_account.startswith("7959") or number_personal_account.startswith("959") or \
                number_personal_account.startswith("38072"):
            if number_personal_account.startswith("7959"):
                number_personal_account = number_personal_account[4:]
            if number_personal_account.startswith("959"):
                number_personal_account = number_personal_account[3:]
            if number_personal_account.startswith("38072"):
                number_personal_account = number_personal_account[5:]
            bot.send_message(chat_id=message.from_user.id,
                             text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                             reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
            bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                       number_personal_account,
                                                                                                       service))
        else:
            bot.send_message(chat_id=message.from_user.id, text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
            bot.send_message(chat_id=message.from_user.id,
                             text="📱 Введите номер телефона в формате +7959XXXXXXX:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(message,
                                           lambda msg_obj: number_for_top_up_from_balance(
                                               msg_obj, service))
    elif service == "qiwi":
        if re.findall(re_pattern_1_phone, message.text):
            number_personal_account = ''.join(re.findall(re_pattern_2_phone, message.text))
            if number_personal_account.startswith("7"):
                number_personal_account = number_personal_account[1:]
            bot.send_message(chat_id=message.from_user.id,
                             text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                             reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
            bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                       number_personal_account,
                                                                                                       service))
        else:
            bot.send_message(chat_id=message.from_user.id, text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
            bot.send_message(chat_id=message.from_user.id,
                             text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(message,
                                           lambda msg_obj: number_for_top_up_from_balance(
                                               msg_obj, service))
    else:
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                                   message.text,
                                                                                                   service))


def ask_price_for_top_up_phone_balance(message, number_personal_account, service):
    if message.text == "🚫 Отмена":
        user_type = db.check_user_type(message.from_user.id)
        if user_type == "client":
            start_client(message)
        elif user_type == "partner":
            start_partner(message)
        else:
            start_manager(message)
        return
    try:

        partner_number = re.findall(r'\(.*?\)', services_dict[service])[-1]
        partner_number = partner_number[partner_number.find("(") + 1:partner_number.find(")")]
        if 10.0 <= float(message.text) <= 99.99:
            amount = float(message.text) * float(db.get_text_from_db("bankRate1")) + float(uniform(0.1, 0.99))
        elif 100.0 <= float(message.text) <= 299.99:
            amount = float(message.text) * float(db.get_text_from_db("bankRate2")) + float(uniform(0.1, 0.99))
        elif 300.0 <= float(message.text) <= 2000.0:
            amount = float(message.text) * float(db.get_text_from_db("bankRate3")) + float(uniform(0.1, 0.99))
        elif int(message.text) > 2000:
            bot.send_message(message.from_user.id,
                             text="⚠️ Некорректная сумма. Допускаются сумма не больше 2000 рублей.")
            bot.send_message(chat_id=message.from_user.id,
                             text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                             reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
            bot.register_next_step_handler(message,
                                           lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                              number_personal_account,
                                                                                              service))
            return
        amount = amount + (db.get_calculation_percent(partner_number)[0] / 100) * amount
    except Exception as ex:
        logging.exception("message")
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message,
                                       lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                          number_personal_account,
                                                                                          service))
        return
    user_info = db.get_user_info(message.from_user.id)
    amount_str = "{:.2f}".format(amount)
    balance = user_info[4]
    if float(amount_str) > balance:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Недостаточно средств на балансе аккаунта.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message,
                                       lambda msg_obj: ask_price_for_top_up_phone_balance(msg_obj,
                                                                                          number_personal_account,
                                                                                          service))
        return
    else:
        bot.send_message(message.from_user.id,
                         text="Баланс будет пополнен в течение нескольких минут. Ждите.")
        try:
            balance_top_upped = top_up_balance_on_website(number_personal_account, message.text, service)
        except:
            db.insert_user_transaction(message.from_user.id, number_personal_account, 1, partner_number, message.text,
                                       "Неудача")
            bot.send_message(message.from_user.id,
                             text="Баланс не был пополнен. Неполадки на стороне бота. Попробуйте позже.")
            user_type = db.check_user_type(message.from_user.id)
            if user_type == "client":
                bot.send_message(chat_id=message.from_user.id,
                                 text="📤 Выберите действие:",
                                 reply_markup=client_keyboard.main_menu_reply_keyboard())
            elif user_type == "manager":
                bot.send_message(chat_id=message.from_user.id,
                                 text="📤 Выберите действие:",
                                 reply_markup=managers_keyboard.main_menu_reply_keyboard())
            elif user_type == "partner":
                bot.send_message(chat_id=message.from_user.id,
                                 text="📤 Выберите действие:",
                                 reply_markup=partners_keyboard.main_menu_reply_keyboard())
            return
        if balance_top_upped:
            db.insert_user_transaction(message.from_user.id, number_personal_account, 1, partner_number, message.text,
                                       "Успех")
            db.update_user_balance_differ(message.from_user.id, amount_str)
            bot.send_message(message.from_user.id,
                             text=f"Баланс пополнен. Проверьте баланс.")
            user_type = db.check_user_type(message.from_user.id)
            if user_type == "client":
                bot.send_message(chat_id=message.from_user.id,
                                 text="📤 Выберите действие:",
                                 reply_markup=client_keyboard.main_menu_reply_keyboard())
            elif user_type == "manager":
                bot.send_message(chat_id=message.from_user.id,
                                 text="📤 Выберите действие:",
                                 reply_markup=managers_keyboard.main_menu_reply_keyboard())
            elif user_type == "partner":
                bot.send_message(chat_id=message.from_user.id,
                                 text="📤 Выберите действие:",
                                 reply_markup=partners_keyboard.main_menu_reply_keyboard())
        else:
            if service == "msk":
                try:
                    service = "msk_2"
                    balance_top_upped = top_up_balance_on_website(number_personal_account, message.text, service)
                except:
                    db.insert_user_transaction(message.from_user.id, number_personal_account, 1, partner_number,
                                               message.text,
                                               "Неудача")
                    bot.send_message(message.from_user.id,
                                     text=f"Баланс не был пополнен. Неполадки на стороне бота. Попробуйте позже.")
                    user_type = db.check_user_type(message.from_user.id)
                    if user_type == "client":
                        bot.send_message(chat_id=message.from_user.id,
                                         text="📤 Выберите действие:",
                                         reply_markup=client_keyboard.main_menu_reply_keyboard())
                    elif user_type == "manager":
                        bot.send_message(chat_id=message.from_user.id,
                                         text="📤 Выберите действие:",
                                         reply_markup=managers_keyboard.main_menu_reply_keyboard())
                    elif user_type == "partner":
                        bot.send_message(chat_id=message.from_user.id,
                                         text="📤 Выберите действие:",
                                         reply_markup=partners_keyboard.main_menu_reply_keyboard())
                    return
                if balance_top_upped:
                    db.insert_user_transaction(message.from_user.id, number_personal_account, 1, partner_number,
                                               message.text,
                                               "Успех")
                    bot.send_message(message.from_user.id,
                                     text=f"Баланс пополнен. Проверьте баланс.")
                    bot.send_message(chat_id=message.from_user.id,
                                     text="📤 Выберите действие:",
                                     reply_markup=client_keyboard.main_menu_reply_keyboard())
                else:
                    db.insert_user_transaction(message.from_user.id, number_personal_account, 1, partner_number,
                                               message.text,
                                               "Неудача")
                    bot.send_message(message.from_user.id,
                                     text=f"Баланс не был пополнен. Неполадки на стороне бота. Попробуйте позже.")
                    user_type = db.check_user_type(message.from_user.id)
                    if user_type == "client":
                        bot.send_message(chat_id=message.from_user.id,
                                         text="📤 Выберите действие:",
                                         reply_markup=client_keyboard.main_menu_reply_keyboard())
                    elif user_type == "manager":
                        bot.send_message(chat_id=message.from_user.id,
                                         text="📤 Выберите действие:",
                                         reply_markup=managers_keyboard.main_menu_reply_keyboard())
                    elif user_type == "partner":
                        bot.send_message(chat_id=message.from_user.id,
                                         text="📤 Выберите действие:",
                                         reply_markup=partners_keyboard.main_menu_reply_keyboard())
            else:
                db.insert_user_transaction(message.from_user.id, number_personal_account, 1, partner_number,
                                           message.text,
                                           "Неудача")
                bot.send_message(message.from_user.id,
                                 text=f"Баланс не был пополнен. Неверно введены данные.")
                user_type = db.check_user_type(message.from_user.id)
                if user_type == "client":
                    bot.send_message(chat_id=message.from_user.id,
                                     text="📤 Выберите действие:",
                                     reply_markup=client_keyboard.main_menu_reply_keyboard())
                elif user_type == "manager":
                    bot.send_message(chat_id=message.from_user.id,
                                     text="📤 Выберите действие:",
                                     reply_markup=managers_keyboard.main_menu_reply_keyboard())
                elif user_type == "partner":
                    bot.send_message(chat_id=message.from_user.id,
                                     text="📤 Выберите действие:",
                                     reply_markup=partners_keyboard.main_menu_reply_keyboard())


def number_for_top_up_one_time(message, bank, service):
    if message.text == "🚫 Отмена":
        start_client(message)
        return
    re_pattern_1_phone = r"(?:(?:8|\+7)[\- ]?)?(?:\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}"
    re_pattern_2_phone = r"\d+"
    if service == "7telecom" or service == "mirtelecom_mobile" or service == "mtc" or service == "biline" or service == "miranda" or service == "megafon" or service == "tele2":
        number_personal_account = ''.join(re.findall(re_pattern_2_phone, message.text))
        if service == "7telecom":
            if number_personal_account.startswith("79900") or number_personal_account.startswith("9900") or \
                    number_personal_account.startswith("79902") or number_personal_account.startswith("9902"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                            number_personal_account,
                                                                                                            service,
                                                                                                            bank))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_one_time(
                                                   msg_obj, bank, service))
        elif service == "mirtelecom_mobile":
            if number_personal_account.startswith("79901") or number_personal_account.startswith("9901"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                            number_personal_account,
                                                                                                            service,
                                                                                                            bank))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_one_time(
                                                   msg_obj, bank, service))
        elif service == "biline":
            if number_personal_account.startswith("7906") or number_personal_account.startswith("906") or \
                    number_personal_account.startswith("7966") or number_personal_account.startswith("966"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                            number_personal_account,
                                                                                                            service,
                                                                                                            bank))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_one_time(
                                                   msg_obj, bank, service))
            
        elif service == "miranda":
            if number_personal_account.startswith("7979") or number_personal_account.startswith("979") or \
                    number_personal_account.startswith("7979") or number_personal_account.startswith("979"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                            number_personal_account,
                                                                                                            service,
                                                                                                            bank))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_one_time(
                                                   msg_obj, bank, service))                                           
                                                   
        elif service == "mtc":
            if number_personal_account.startswith("7985") or number_personal_account.startswith("985"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                            number_personal_account,
                                                                                                            service,
                                                                                                            bank))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_one_time(
                                                   msg_obj, bank, service))
        elif service == "megafon":
            if number_personal_account.startswith("7925") or number_personal_account.startswith("925"):
                if number_personal_account.startswith("7985") or number_personal_account.startswith("985"):
                    if number_personal_account.startswith("7"):
                        number_personal_account = number_personal_account[1:]
                    bot.send_message(chat_id=message.from_user.id,
                                     text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                     reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                    bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                                number_personal_account,
                                                                                                                service,
                                                                                                                bank))
                else:
                    bot.send_message(chat_id=message.from_user.id,
                                     text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                    bot.send_message(chat_id=message.from_user.id,
                                     text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                     reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                    bot.register_next_step_handler(message,
                                                   lambda msg_obj: number_for_top_up_one_time(
                                                       msg_obj, bank, service))
        elif service == "tele2":
            if number_personal_account.startswith("7911") or number_personal_account.startswith("911"):
                if number_personal_account.startswith("7"):
                    number_personal_account = number_personal_account[1:]
                bot.send_message(chat_id=message.from_user.id,
                                 text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                                 reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
                bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                            number_personal_account,
                                                                                                            service,
                                                                                                            bank))
            else:
                bot.send_message(chat_id=message.from_user.id,
                                 text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
                bot.send_message(chat_id=message.from_user.id,
                                 text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                                 reply_markup=client_keyboard.get_cancel_last_number_keyboard())
                bot.register_next_step_handler(message,
                                               lambda msg_obj: number_for_top_up_one_time(
                                                   msg_obj, bank, service))
    elif service == "msk":
        number_personal_account = ''.join(re.findall(re_pattern_2_phone, message.text))
        if number_personal_account.startswith("7959") or number_personal_account.startswith("959") or \
                number_personal_account.startswith("38072"):
            if number_personal_account.startswith("7959"):
                number_personal_account = number_personal_account[4:]
            if number_personal_account.startswith("959"):
                number_personal_account = number_personal_account[3:]
            if number_personal_account.startswith("38072"):
                number_personal_account = number_personal_account[5:]
            bot.send_message(chat_id=message.from_user.id,
                             text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                             reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
            bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                        number_personal_account,
                                                                                                        service,
                                                                                                        bank))
        else:
            bot.send_message(chat_id=message.from_user.id, text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
            bot.send_message(chat_id=message.from_user.id,
                             text="📱 Введите номер телефона в формате +7959XXXXXXX:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(message,
                                           lambda msg_obj: number_for_top_up_one_time(
                                               msg_obj, bank, service))
    elif service == "qiwi":
        if re.findall(re_pattern_1_phone, message.text):
            number_personal_account = ''.join(re.findall(re_pattern_2_phone, message.text))
            if number_personal_account.startswith("7"):
                number_personal_account = number_personal_account[1:]
            bot.send_message(chat_id=message.from_user.id,
                             text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                             reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
            bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                        number_personal_account,
                                                                                                        service,
                                                                                                        bank))
        else:
            bot.send_message(chat_id=message.from_user.id, text="⚠️ <i>Введённый номер не соответсвует оператору</i>.")
            bot.send_message(chat_id=message.from_user.id,
                             text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(message,
                                           lambda msg_obj: number_for_top_up_one_time(
                                               msg_obj, bank, service))
    else:
        if service == "kahowka":
            get_info_about_balance_kahowka(message.text, bot, message.from_user.id)
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                                    message.text,
                                                                                                    service,
                                                                                                    bank))


def top_up_balance_from_top_up_one_time(message, number_personal_account, service, bank):
    if message.text == "🚫 Отмена":
        start_client(message)
        return
    try:
        partner_number = re.findall(r'\(.*?\)', services_dict[service])[-1]
        partner_number = partner_number[partner_number.find("(") + 1:partner_number.find(")")]
        if 10.0 <= float(message.text) <= 99.99:
            amount = float(message.text) * float(db.get_text_from_db("bankRate1")) + float(uniform(0.1, 0.99))
        elif 100.0 <= float(message.text) <= 299.99:
            amount = float(message.text) * float(db.get_text_from_db("bankRate2")) + float(uniform(0.1, 0.99))
        elif 300.0 <= float(message.text) <= 2000.0:
            amount = float(message.text) * float(db.get_text_from_db("bankRate3")) + float(uniform(0.1, 0.99))
        elif int(message.text) > 2000:
            bot.send_message(message.from_user.id,
                             text="⚠️ Некорректная сумма. Допускаются сумма не больше 2000 рублей.")
            bot.send_message(chat_id=message.from_user.id,
                             text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                             reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
            bot.register_next_step_handler(message,
                                           lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                               number_personal_account,
                                                                                               service, bank))
            return
        amount = amount + (db.get_calculation_percent(partner_number)[0] / 100) * amount
        amount_str = "{:.2f}".format(amount)
        amount_for_website = message.text
    except Exception as ex:
        logging.exception("message")
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в рублях):",
                         reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message,
                                       lambda msg_obj: top_up_balance_from_top_up_one_time(msg_obj,
                                                                                           number_personal_account,
                                                                                           service, bank))
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                client_id = account['sendId']
                break
    if bank == "monobank":
        bot.send_message(chat_id=message.from_user.id,
                         text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Monobank" расположенную ниже, Вас перенаправит в приложение , где будут заполнены все поля . Не изменяйте эти поля , особенно сумму .\n\n🔸 Если поля не заполнились автоматически, обновите приложение Monobank в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                         reply_markup=client_keyboard.monobank_link_keyboard(client_id, amount_str))
    elif bank == "privat24":
        bot.send_message(chat_id=message.from_user.id,
                         text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Приват24" расположенную ниже, Вас перенаправит в приложение , где будут заполнены поля "Номер карты" и "Сумма" . Не изменяйте эти поля , особенно сумму.\n\n🔸 Если поля не заполнились автоматически, обновите приложение Приват24 в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                         reply_markup=client_keyboard.privat24_link_keyboard(number_card, amount_str))
    elif bank == "another_card":
        bot.send_message(chat_id=message.from_user.id,
                         text=f'📋 <b>Инструкция по оплате:</b>\nПереведите на карту <code>{number_card}</code> сумму в размере <b>{amount_str} грн.</b>\n\n❗️ <u>Переводите именно эту сумму, ни копейки больше, ни копейки меньше! Иначе система не сможет автоматически найти Ваш платеж и Вам придётся обращаться в нашу техническую поддержку для решения вопроса.</u>',
                         reply_markup=client_keyboard.another_card_link_keyboard())
    payments['in_process_web_balance'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str, amount_for_website,
                                                                     number_personal_account, service, message.text]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


@bot.message_handler(func=lambda message: message.text == "/start")
def start_client(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'client' and user_type != 'blocked':
        user_info = db.get_user_info(message.from_user.id)
        if not user_info:
            if message.from_user.first_name and message.from_user.last_name:
                full_name = message.from_user.first_name + " " + message.from_user.last_name
            elif message.from_user.first_name:
                full_name = message.from_user.first_name
            elif message.from_user.last_name:
                full_name = message.from_user.last_name
            else:
                full_name = ""

            db.insert_user_info(message.from_user.id, full_name, message.from_user.username)
            bot.send_message(chat_id=message.from_user.id,
                             text="🎉 Добро пожаловать, в этом боте Вы можете пополнить счёт мобильного телефона оператора +7Телеком и МирТелеком. В качестве оплаты бот принимает гривны.\n\nТак же здесь Вы можете получить информацию о том как подключить дополнительный интернет , звонки или же СМС. Просто выберите соответсвующий пункт в меню.",
                             reply_markup=client_keyboard.first_start_inline_keyboard())
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        else:
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "🛒 Список услуг")
def services(message):
    if db.check_user_type(message.from_user.id) != 'blocked':
        text = db.get_text_from_db("servicesText").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=text)
        bot.send_message(chat_id=message.from_user.id,
                         text="📤 Выберите действие:",
                         reply_markup=client_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "📲 Пополнить")
def services_list(message):
    if data["payments_work"]:
        user_type = db.check_user_type(message.from_user.id)
        if user_type != 'blocked':
            bot.send_message(chat_id=message.from_user.id,
                             text="💻 Выберите категорию",
                             reply_markup=client_keyboard.categories_inline_keyboard())
    else:
        bot.send_message(chat_id=message.from_user.id,
                         text="Технические неполадки, попробуйте позже",
                         reply_markup=client_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "💰 Баланс аккаунта")
def account_balance_client(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'client' and user_type != 'blocked':
        user_info = db.get_user_info(message.from_user.id)
        bot.send_message(chat_id=message.from_user.id,
                         text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n💵 Баланс: <code>{user_info[4]}</code> грн.\n💳 Сумма пополнений: <code>{user_info[5]}</code> грн.",
                         reply_markup=client_keyboard.top_up_balance_keyboard())
        bot.send_message(chat_id=message.from_user.id,
                         text="📤 Выберите действие:",
                         reply_markup=client_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "💬 Чат/отзывы")
def reviews(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type != 'blocked':
        text = db.get_text_from_db("reviewsText").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=f"<b>{text}</b>",
                         reply_markup=client_keyboard.reviews_link_keyboard())
        if user_type == "client":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        elif user_type == "manager":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        elif user_type == "partner":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "exchange")
def exchange(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type != 'blocked':
        text = db.get_text_from_db("botExchange").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=f"<b>{text}</b>",
                         reply_markup=client_keyboard.get_in_touch_with_support_exchange())
        if user_type == "client":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        elif user_type == "manager":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        elif user_type == "partner":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "⁉️ Написать оператору")
def help_message_handler(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type != 'blocked':
        text = db.get_text_from_db("botSupportOperator").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=f"<b>{text}</b>",
                         reply_markup=client_keyboard.get_in_touch_with_support_keyboard())
        if user_type == "client":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        elif user_type == "manager":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        elif user_type == "partner":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "📔 Правила")
def rules(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type != 'blocked':
        text = db.get_text_from_db("termsText").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=text)
        if user_type == "client":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        elif user_type == "manager":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        elif user_type == "partner":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "Инструкция")
def rules(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type != 'blocked':
        text = db.get_text_from_db("instructionText").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=text,
                         reply_markup=client_keyboard.instruction_link_keyboard())
        if user_type == "client":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        elif user_type == "manager":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        elif user_type == "partner":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "Полезная информация")
def useful_information(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type != 'blocked':
        text = db.get_text_from_db("usefulInformationText").replace(r"\n", "\n")
        bot.send_message(chat_id=message.from_user.id,
                         text=text,
                         reply_markup=client_keyboard.useful_information_link_keyboard())
        if user_type == "client":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=client_keyboard.main_menu_reply_keyboard())
        elif user_type == "manager":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        elif user_type == "partner":
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "back_to_main_menu")
def back_to_main_menu(callback):
    bot.send_message(chat_id=callback.from_user.id,
                     text="📤 Выберите действие:",
                     reply_markup=client_keyboard.main_menu_reply_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "back_to_categories")
def back_to_categories(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="💻 Выберите категорию:",
                          reply_markup=client_keyboard.categories_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "mobile_services")
def mobile_services(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="💻 Выберите сервис:",
                          reply_markup=client_keyboard.mobile_services_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "internet_services")
def internet_services(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="💻 Выберите сервис:",
                          reply_markup=client_keyboard.internet_services_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "virtual_money_services")
def virtual_money_services(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="💰 Выберите кошелёк:",
                          reply_markup=client_keyboard.virtual_money_services_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "game_services")
def game_services(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="🕹 Выберите игру:",
                          reply_markup=client_keyboard.game_services_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "xsolla_games")
def game_services(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="🕹 Выберите игру:",
                          reply_markup=client_keyboard.xsolla_games_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_balance")
def top_up_balance(callback):
    bot.send_message(chat_id=callback.from_user.id,
                     text="Выберите способ оплаты:",
                     reply_markup=client_keyboard.all_payments_methods_account_balance_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_monobank")
def top_up_monobank(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_monobank)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_privat24")
def top_up_privat24(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_privat24)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_another_card")
def top_up_another_card(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=client_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_another_card)


@bot.callback_query_handler(func=lambda callback: callback.data.startswith("top_up_one_time"))
def top_up_one_time_monobank(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bank_chosen = callback.data.split("|")[1]
    service = callback.data.split("|")[2]
    if service == "7telecom" or service == "mirtelecom_mobile" or service == "mtc" or service == "biline" or service == "miranda" or service == "megafon" or service == "tele2":
        bot.send_message(chat_id=callback.from_user.id,
                         text="📱 Введите номер телефона в формате +7XXXXXXXXXX:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "msk":
        bot.send_message(chat_id=callback.from_user.id,
                         text="📱 Введите номер телефона в формате +7959XXXXXXX:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "mirtelecom_internet":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите номер лицевого счета:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "tricolor_night":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите ID приемника или номера договора:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "kahowka":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите <b>шестизначный ID</b> лицевого счета :",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "qiwi":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите номер телефона +7XXXXXXXXXX:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "yoomoney":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите номер счета(кошелька) в ЮMoney:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "warface":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите логин (Ваш е-mail):",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "steam":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите имя аккаунта (Login) в Steam:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "wot":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите E-mail:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "vk_buy_votes":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите id, короткое имя или логин:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "legend_dragons":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите ник персонажа:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "jade_dynasty":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите игровой аккаунт:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "perfect_world":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите Ваш аккаунт:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "bums":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите платежный ID:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "revelation":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите Ваш платежный ID:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    elif service == "steam_20_euros":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите свой e-mail:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))
    else:
        bot.send_message(chat_id=callback.from_user.id,
                         text="Введите Ник игрока:",
                         reply_markup=client_keyboard.get_cancel_last_number_keyboard())
        bot.register_next_step_handler(callback.message,
                                       lambda msg_obj: number_for_top_up_one_time(
                                           msg_obj, bank_chosen, service))


@bot.callback_query_handler(func=lambda callback: callback.data.startswith("balance_top_up_one_time"))
def top_up_one_time_balance(callback):
    service = callback.data.split("|")[1]
    user_info = db.get_user_info(callback.from_user.id)
    balance = user_info[4]
    if balance > 8.0:
        bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        if service == "7telecom" or service == "mirtelecom_mobile" or service == "mtc" or service == "biline" or service == "miranda" or service == "megafon" or service == "tele2":
            bot.send_message(chat_id=callback.from_user.id,
                             text="📱 Введите номер телефона в формате <b>+7XXXXXXXXXX</b>:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "msk":
            bot.send_message(chat_id=callback.from_user.id,
                             text="📱 Введите номер телефона в формате +7959XXXXXXX:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "mirtelecom_internet":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите номер лицевого счета:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "tricolor_night":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите ID приемника или номера договора:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "kahowka":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите ID:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "qiwi":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите номер телефона +7XXXXXXXXXX:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "yoomoney":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите номер счета(кошелька) в ЮMoney:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "warface":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите логин (Ваш е-mail):",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "steam":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите имя аккаунта (Login) в Steam:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "wot":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите E-mail:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "vk_buy_votes":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите id, короткое имя или логин:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "legend_dragons":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите ник персонажа:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "jade_dynasty":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите игровой аккаунт:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "perfect_world":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите Ваш аккаунт:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "bums":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите платежный ID:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "revelation":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите Ваш платежный ID:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        elif service == "steam_20_euros":
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите свой e-mail:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
        else:
            bot.send_message(chat_id=callback.from_user.id,
                             text="Введите Ник игрока:",
                             reply_markup=client_keyboard.get_cancel_last_number_keyboard())
            bot.register_next_step_handler(callback.message,
                                           lambda msg_obj: number_for_top_up_from_balance(msg_obj, service))
    else:
        bot.answer_callback_query(callback.id,
                                  text="У Вас недостаточно средств на балансе аккаунта. Минимальная сумма пополнения 10 рублей.",
                                  show_alert=True)


@bot.callback_query_handler(func=lambda callback: callback.data == "cancel_payment")
def cancel_payment(callback):
    payments['in_process_balance_manager'][str(callback.from_user.id)] = []
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="❌ Ваш заказ отменён.",
                     reply_markup=None)
    bot.send_message(chat_id=callback.from_user.id,
                     text="📤 Выберите действие:",
                     reply_markup=client_keyboard.main_menu_reply_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data in services_dict)
def top_up_one_time(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    service = callback.data
    user_info = db.get_user_info(callback.from_user.id)
    balance = user_info[4]
    user_type = db.check_user_type(callback.from_user.id)
    if user_type == "client":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Выберите способ оплаты:",
                         reply_markup=client_keyboard.all_payments_methods_keyboard(balance, service))
    elif user_type == "manager":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Выберите способ оплаты:",
                         reply_markup=managers_keyboard.all_payments_methods_keyboard(balance, service))
    elif user_type == "partner":
        bot.send_message(chat_id=callback.from_user.id,
                         text="Выберите способ оплаты:",
                         reply_markup=partners_keyboard.all_payments_methods_keyboard(balance, service))


##########################################################################################################


@bot.message_handler(func=lambda message: message.text == "/manager")
def start_manager(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'manager' and user_type != 'blocked':
        user_info = db.get_user_info(message.from_user.id)
        if not user_info:
            if message.from_user.first_name and message.from_user.last_name:
                full_name = message.from_user.first_name + " " + message.from_user.last_name
            elif message.from_user.first_name:
                full_name = message.from_user.first_name
            elif message.from_user.last_name:
                full_name = message.from_user.last_name
            else:
                full_name = ""

            db.insert_user_info(message.from_user.id, full_name, message.from_user.username)
            bot.send_message(chat_id=message.from_user.id,
                             text="🎉 Добро пожаловать, в этом боте Вы можете пополнить счёт мобильного телефона оператора +7Телеком и МирТелеком. В качестве оплаты бот принимает гривны.\n\nТак же здесь Вы можете получить информацию о том как подключить дополнительный интернет , звонки или же СМС. Просто выберите соответсвующий пункт в меню.",
                             reply_markup=managers_keyboard.first_start_inline_keyboard())
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())
        else:
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=managers_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "💰 Баланс аккаунта менеджера")
def account_balance_manager(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'manager' and user_type != 'blocked':
        user_info = db.get_user_info(message.from_user.id)
        bot.send_message(chat_id=message.from_user.id,
                         text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n💵 Баланс: <code>{user_info[4]}</code> грн.\n💳 Сумма пополнений: <code>{user_info[5]}</code> грн.",
                         reply_markup=managers_keyboard.top_up_balance_keyboard())
        bot.send_message(chat_id=message.from_user.id,
                         text="📤 Выберите действие:",
                         reply_markup=managers_keyboard.main_menu_reply_keyboard())


def top_up_account_balance_monobank_manager(message):
    if message.text == "🚫 Отмена":
        start_manager(message)
        return
    try:
        amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=managers_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_monobank_manager)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                client_id = account['sendId']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Monobank" расположенную ниже, Вас перенаправит в приложение , где будут заполнены все поля . Не изменяйте эти поля , особенно сумму .\n\n🔸 Если поля не заполнились автоматически, обновите приложение Monobank в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                     reply_markup=managers_keyboard.monobank_link_keyboard(client_id, amount_str))
    payments['in_process_balance_manager'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_privat24_manager(message):
    if message.text == "🚫 Отмена":
        start_manager(message)
        return
    try:
        amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=managers_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_privat24_manager)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Приват24" расположенную ниже, Вас перенаправит в приложение , где будут заполнены поля "Номер карты" и "Сумма" . Не изменяйте эти поля , особенно сумму.\n\n🔸 Если поля не заполнились автоматически, обновите приложение Приват24 в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                     reply_markup=managers_keyboard.privat24_link_keyboard(number_card, amount_str))
    payments['in_process_balance_manager'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_another_card_manager(message):
    if message.text == "🚫 Отмена":
        start_manager(message)
        return
    try:
        amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=managers_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_another_card_manager)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'📋 <b>Инструкция по оплате:</b>\nПереведите на карту <code>{number_card}</code> сумму в размере <b>{amount_str} грн.</b>\n\n❗️ <u>Переводите именно эту сумму, ни копейки больше, ни копейки меньше! Иначе система не сможет автоматически найти Ваш платеж и Вам придётся обращаться в нашу техническую поддержку для решения вопроса.</u>',
                     reply_markup=managers_keyboard.another_card_link_keyboard())
    payments['in_process_balance_manager'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_balance_manager")
def top_up_balance_manager(callback):
    bot.send_message(chat_id=callback.from_user.id,
                     text="Выберите способ оплаты:",
                     reply_markup=managers_keyboard.all_payments_methods_account_balance_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_monobank_manager")
def top_up_monobank_manager(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=managers_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_monobank_manager)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_privat24_manager")
def top_up_privat24_manager(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=managers_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_privat24_manager)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_another_card_manager")
def top_up_another_card_manager(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=managers_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_another_card_manager)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_one_time_balance")
def top_up_phone_balance_from_balance_manager(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    user_info = db.get_user_info(callback.from_user.id)
    balance = user_info[4]
    if balance > 8.0:
        if user_info[6]:
            bot.send_message(chat_id=callback.from_user.id,
                             text="📱 Введите номер телефона в формате <b>+7990XXXXXXX</b>:")
            bot.register_next_step_handler(callback.message, number_for_top_up_from_balance)
        else:
            bot.send_message(chat_id=callback.from_user.id,
                             text="📱 Введите номер телефона в формате <b>+7990XXXXXXX</b>:")
            bot.register_next_step_handler(callback.message, number_for_top_up_from_balance)
    else:
        bot.send_message(chat_id=callback.from_user.id,
                         text="У Вас недостаточно средств на балансе аккаунта. Минимальная сумма пополнения 10 рублей.")
        bot.send_message(chat_id=callback.from_user.id,
                         text="📤 Выберите действие:",
                         reply_markup=managers_keyboard.main_menu_reply_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "cancel_payment_manager")
def cancel_payment_manager(callback):
    payments['in_process_balance_manager'][str(callback.from_user.id)] = []
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="❌ Ваш заказ отменён.",
                     reply_markup=None)
    bot.send_message(chat_id=callback.from_user.id,
                     text="📤 Выберите действие:",
                     reply_markup=managers_keyboard.main_menu_reply_keyboard())


##################################################################################################


@bot.message_handler(func=lambda message: message.text.startswith("/sendsms"))
def send_message_to_user_handler(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        chat_id = message.text.split(" ")[1]
        bot.send_message(chat_id=message.from_user.id, text="Отправьте сообщение для отправке пользователю: ")
        bot.register_next_step_handler(message, lambda msg: send_message_to_user(msg, chat_id))


def send_message_to_user(message, chat_id):
    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="💬 Связаться с поддержкой", url=db.get_text_from_db("botSupportLink")))
        bot.send_message(chat_id=chat_id, text=message.text, reply_markup=keyboard)
        bot.send_message(chat_id=message.from_user.id, text="Сообщение отправлено пользователю.")
    except:
        bot.send_message(chat_id=message.from_user.id, text="Сообщение не было отправлено пользователю. Ошибка.")


@bot.message_handler(func=lambda message: message.text == "/admin")
def start_admin(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        user_info = db.get_user_info(message.from_user.id)
        if not user_info:
            if message.from_user.first_name and message.from_user.last_name:
                full_name = message.from_user.first_name + " " + message.from_user.last_name
            elif message.from_user.first_name:
                full_name = message.from_user.first_name
            elif message.from_user.last_name:
                full_name = message.from_user.last_name
            else:
                full_name = ""

            db.insert_user_info(message.from_user.id, full_name, message.from_user.username)
            bot.send_message(chat_id=message.from_user.id,
                             text="🎉 Добро пожаловать, в этом боте Вы можете пополнить счёт мобильного телефона оператора +7Телеком и МирТелеком. В качестве оплаты бот принимает гривны.\n\nТак же здесь Вы можете получить информацию о том как подключить дополнительный интернет , звонки или же СМС. Просто выберите соответсвующий пункт в меню.",
                             reply_markup=admin_keyboard.first_start_inline_keyboard())
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
        else:
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Сменить номер карты")
def change_number_card_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите новый номер карты в таком формате <code>4441 1144 5374 7287</code>:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, change_card_number)


def change_card_number(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    db.update_text_db("numberCard", message.text)
    bot.send_message(chat_id=message.from_user.id,
                     text="Номер карты был изменён.",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Сменить данные для входа PayBerry")
def change_login_details_payberry_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите новые логин и пароль для PayBerry в формате:\n9900499475\n892345",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, change_login_details_payberry)


def change_login_details_payberry(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    db.update_text_db("loginDetailsPayBerry", message.text)
    bot.send_message(chat_id=message.from_user.id,
                     text="Данные для входа в PayBerry были изменёны.",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Блокировка пользователя по ID")
def block_user_by_id_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите Телеграм ID для блокировки пользователя:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, block_user_by_id)


def block_user_by_id(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    user_type_changed = db.update_user_type(int(message.text), "blocked")
    if user_type_changed:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Пользователь <b>{message.text}</b> был заблокирован.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
    else:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Данного пользователя <b>{message.text}</b> нету в базе данных.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Разблокировать пользователя по ID")
def unblock_user_by_id_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите Телеграм ID для разблокировки пользователя:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, unblock_user_by_id)


def unblock_user_by_id(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    user_type_changed = db.update_user_type(int(message.text), "client")
    if user_type_changed:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Пользователь <b>{message.text}</b> был разблокирован.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
    else:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Данного пользователя <b>{message.text}</b> нету в базе данных.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Добавление менеджера по ID")
def manager_set_by_id_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите Телеграм ID для назначения менеджера:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, manager_set_by_id)


def manager_set_by_id(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    user_type_changed = db.update_user_type(int(message.text), "manager")
    if user_type_changed:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Пользователь <b>{message.text}</b> был назначен менеджером.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
    else:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Данного пользователя <b>{message.text}</b> нету в базе данных.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Удаление менеджера по ID")
def unset_manager_by_id_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите Телеграм ID для удаления менеджера:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, unset_manager_by_id)


def unset_manager_by_id(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    user_type_changed = db.update_user_type(int(message.text), "client")
    if user_type_changed:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Пользователь <b>{message.text}</b> стал клиентом, более не менеджер.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
    else:
        bot.send_message(chat_id=message.from_user.id,
                         text=f"Данного пользователя <b>{message.text}</b> нету в базе данных.",
                         reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Изменить Курс1")
def change_bank_rate_1_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите новый курс для <b>Курс1</b>:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, change_bank_rate_1)


def change_bank_rate_1(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    db.update_text_db("bankRate1", message.text)
    bot.send_message(chat_id=message.from_user.id,
                     text="<b>Курс1</b> был изменён.",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Изменить Курс2")
def change_bank_rate_2_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите новый курс для <b>Курс2</b>:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, change_bank_rate_2)


def change_bank_rate_2(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    db.update_text_db("bankRate2", message.text)
    bot.send_message(chat_id=message.from_user.id,
                     text="<b>Курс2</b> был изменён.",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Изменить Курс3")
def change_bank_rate_3_func(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id,
                         text="Введите новый курс для <b>Курс3</b>:",
                         reply_markup=admin_keyboard.get_cancel_keyboard())
        bot.register_next_step_handler(message, change_bank_rate_3)


def change_bank_rate_3(message):
    if message.text == "🚫 Отмена":
        start_admin(message)
        return
    db.update_text_db("bankRate3", message.text)
    bot.send_message(chat_id=message.from_user.id,
                     text="<b>Курс3</b> был изменён.",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))


@bot.message_handler(func=lambda message: message.text == "Рассылка по группам пользователей")
def send_message_by_groups(message):
    if db.check_user_type(message.from_user.id) == 'admin':
        bot.send_message(chat_id=message.from_user.id, text="Выберите группу пользователей:",
                         reply_markup=admin_keyboard.send_message_by_group_inline_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "client")
def send_message_to_clients(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.id)
    bot.send_message(chat_id=callback.from_user.id, text="Введите текст для рассылки:")
    bot.register_next_step_handler(callback.message, lambda msg: send_message_to_group(msg, 'client'))


@bot.callback_query_handler(func=lambda callback: callback.data == "manager")
def send_message_to_managers(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.id)
    bot.send_message(chat_id=callback.from_user.id, text="Введите текст для рассылки:")
    bot.register_next_step_handler(callback.message, lambda msg: send_message_to_group(msg, 'manager'))


@bot.callback_query_handler(func=lambda callback: callback.data == "partner")
def send_message_to_partners(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.id)
    bot.send_message(chat_id=callback.from_user.id, text="Введите текст для рассылки:")
    bot.register_next_step_handler(callback.message, lambda msg: send_message_to_group(msg, 'partner'))


def send_message_to_group(message, group):
    bot.send_message(chat_id=message.from_user.id, text="Процесс рассылки начался, это может занять некоторое время...")
    users = db.get_users_by_group(group)
    not_sent = 0
    for user in users:
        try:
            bot.send_message(chat_id=user[1], text=message.text)
        except:
            not_sent += 1
            continue
    bot.send_message(chat_id=message.from_user.id, text=f"Рассылка по группе пользователей завершена.\n"
                                                        f"Бот не смог отправить сообщение {not_sent} пользователям.")
    start_admin(message)


@bot.message_handler(func=lambda message: message.text == "Отключить пополнения")
def bot_off(message):
    data["bot_on"] = False
    json.dump(data, open("bot_data.json", "w", encoding="utf-8"), indent=4)
    bot.send_message(chat_id=message.from_user.id,
                     text="<b>Платежи в боте отключены.</b>",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
    start_admin(message)


@bot.message_handler(func=lambda message: message.text == "Включить пополнения")
def bot_on(message):
    data["bot_on"] = True
    json.dump(data, open("bot_data.json", "w", encoding="utf-8"), indent=4)
    bot.send_message(chat_id=message.from_user.id,
                     text="<b>Платежи в боте включены.</b>",
                     reply_markup=admin_keyboard.main_menu_reply_keyboard(data["payments_work"]))
    start_admin(message)


#######################################################################################################################


@bot.message_handler(func=lambda message: message.text == "/partner")
def start_partner(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'partner' and user_type != 'blocked':
        if str(message.from_user.id) not in partners_data['partners_transactions_amount']:
            partners_data['partners_transactions_amount'][str(message.from_user.id)] = [0.0, int(time.time())]
            json.dump(partners_data, open("partners.json", "w", encoding="utf-8"), indent=4)
        user_info = db.get_user_info(message.from_user.id)
        if not user_info:
            if message.from_user.first_name and message.from_user.last_name:
                full_name = message.from_user.first_name + " " + message.from_user.last_name
            elif message.from_user.first_name:
                full_name = message.from_user.first_name
            elif message.from_user.last_name:
                full_name = message.from_user.last_name
            else:
                full_name = ""

            db.insert_user_info(message.from_user.id, full_name, message.from_user.username)
            bot.send_message(chat_id=message.from_user.id,
                             text="🎉 Добро пожаловать, в этом боте Вы можете пополнить счёт мобильного телефона оператора +7Телеком и МирТелеком. В качестве оплаты бот принимает гривны.\n\nТак же здесь Вы можете получить информацию о том как подключить дополнительный интернет , звонки или же СМС. Просто выберите соответсвующий пункт в меню.",
                             reply_markup=partners_keyboard.first_start_inline_keyboard())
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())
        else:
            bot.send_message(chat_id=message.from_user.id,
                             text="📤 Выберите действие:",
                             reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "💰 Баланс аккаунта партнёра")
def account_balance_partner(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'partner' and user_type != 'blocked':
        user_info = db.get_user_info(message.from_user.id)
        if partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 100000.0:
            current_discount = 10
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 50000.0:
            current_discount = 7
            possible_discount = 10
            needs_to_top_up = 100000.0 - partners_data['partners_transactions_amount'][str(message.from_user.id)][0]
            needs_to_top_up = round(needs_to_top_up, 2)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 30000.0:
            current_discount = 6
            possible_discount = 7
            needs_to_top_up = 50000.0 - partners_data['partners_transactions_amount'][str(message.from_user.id)][0]
            needs_to_top_up = round(needs_to_top_up, 2)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 15000.0:
            current_discount = 5
            possible_discount = 6
            needs_to_top_up = 30000.0 - partners_data['partners_transactions_amount'][str(message.from_user.id)][0]
            needs_to_top_up = round(needs_to_top_up, 2)
        else:
            current_discount = 0
            possible_discount = 5
            needs_to_top_up = 15000.0 - partners_data['partners_transactions_amount'][str(message.from_user.id)][0]
            needs_to_top_up = round(needs_to_top_up, 2)
        if current_discount == 10:
            bot.send_message(chat_id=message.from_user.id,
                             text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n"
                                  f"💵 Баланс: <code>{user_info[4]}</code> грн.\n"
                                  f"За последние 30 дней\n"
                                  f"Общая сумма пополнения {partners_data['partners_transactions_amount'][str(message.from_user.id)][0]} грн.\n"
                                  f"Имеете дополнительную скидку {current_discount}%\n",
                             reply_markup=partners_keyboard.top_up_balance_keyboard())
        else:
            bot.send_message(chat_id=message.from_user.id,
                             text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n"
                                  f"💵 Баланс: <code>{user_info[4]}</code> грн.\n"
                                  f"За последние 30 дней\n"
                                  f"Общая сумма пополнения {partners_data['partners_transactions_amount'][str(message.from_user.id)][0]} грн.\n"
                                  f"Имеете дополнительную скидку {current_discount}%\n"
                                  f"Для достижения скидки {possible_discount}% необходимо пополнить {needs_to_top_up} грн.",
                             reply_markup=partners_keyboard.top_up_balance_keyboard())
        bot.send_message(chat_id=message.from_user.id,
                         text="📤 Выберите действие:",
                         reply_markup=partners_keyboard.main_menu_reply_keyboard())


def top_up_account_balance_monobank_partner(message):
    if message.text == "🚫 Отмена":
        start_partner(message)
        return
    try:
        if partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 100000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (10 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 50000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (7 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 30000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (6 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 15000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (5 / 100) * float(message.text)
        else:
            amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=partners_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_monobank_partner)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                client_id = account['sendId']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Monobank" расположенную ниже, Вас перенаправит в приложение , где будут заполнены все поля . Не изменяйте эти поля , особенно сумму .\n\n🔸 Если поля не заполнились автоматически, обновите приложение Monobank в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                     reply_markup=partners_keyboard.monobank_link_keyboard(client_id, amount_str))
    payments['in_process_balance_partner'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_privat24_partner(message):
    if message.text == "🚫 Отмена":
        start_partner(message)
        return
    try:
        if partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 100000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (10 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 50000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (7 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 30000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (6 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 15000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (5 / 100) * float(message.text)
        else:
            amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=partners_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_privat24_partner)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'‼️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ\n\n🔸 После нажатия на кнопку "Оплатить в Приват24" расположенную ниже, Вас перенаправит в приложение , где будут заполнены поля "Номер карты" и "Сумма" . Не изменяйте эти поля , особенно сумму.\n\n🔸 Если поля не заполнились автоматически, обновите приложение Приват24 в Play Market или App Store.\n\n🔸 Если ничего не выходит , то сделайте перевод самостоятельно. Скопируйте или введите вручную номер карты и сумму.  Не округляйте сумму, она должна быть точной что-бы бот её нашёл!\n\nНомер карты: <code>{number_card}</code>\nСумма к оплате: <code>{amount_str}</code>',
                     reply_markup=partners_keyboard.privat24_link_keyboard(number_card, amount_str))
    payments['in_process_balance_partner'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


def top_up_account_balance_another_card_partner(message):
    if message.text == "🚫 Отмена":
        start_partner(message)
        return
    try:
        if partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 100000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (10 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 50000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (7 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 30000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (6 / 100) * float(message.text)
        elif partners_data['partners_transactions_amount'][str(message.from_user.id)][0] > 15000.0:
            amount = float(message.text) + float(uniform(0.1, 0.99)) - (5 / 100) * float(message.text)
        else:
            amount = float(message.text) + float(uniform(0.1, 0.99))
        amount_str = "{:.2f}".format(amount)
    except:
        bot.send_message(message.from_user.id, text="⚠️ Некорректная сумма. Допускаются только цифры.")
        bot.send_message(chat_id=message.from_user.id,
                         text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                         reply_markup=partners_keyboard.top_up_balance_keyboard_with_options())
        bot.register_next_step_handler(message, top_up_account_balance_another_card_partner)
        return
    asked_top_up_time = int(time.time())
    number_card = db.get_text_from_db("numberCard")
    for account in mono_bank_user_info["accounts"]:
        if len(account["maskedPan"]) >= 1:
            if account["maskedPan"][0].startswith("444111") and account["maskedPan"][0].endswith("7287"):
                account_id = account['id']
                break
    bot.send_message(chat_id=message.from_user.id,
                     text=f'📋 <b>Инструкция по оплате:</b>\nПереведите на карту <code>{number_card}</code> сумму в размере <b>{amount_str} грн.</b>\n\n❗️ <u>Переводите именно эту сумму, ни копейки больше, ни копейки меньше! Иначе система не сможет автоматически найти Ваш платеж и Вам придётся обращаться в нашу техническую поддержку для решения вопроса.</u>',
                     reply_markup=partners_keyboard.another_card_link_keyboard())
    payments['in_process_balance_partner'][str(message.from_user.id)] = [account_id, asked_top_up_time, amount_str]
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_balance_partner")
def top_up_balance_partner(callback):
    bot.send_message(chat_id=callback.from_user.id,
                     text="Выберите способ оплаты:",
                     reply_markup=partners_keyboard.all_payments_methods_account_balance_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_monobank_partner")
def top_up_monobank_partner(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=partners_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_monobank_partner)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_privat24_partner")
def top_up_privat24_partner(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=partners_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_privat24_partner)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_another_card_partner")
def top_up_another_card_partner(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="💰 Выберите сумму для пополнения или введите свою (в гривнах):",
                     reply_markup=partners_keyboard.top_up_balance_keyboard_with_options())
    bot.register_next_step_handler(callback.message, top_up_account_balance_another_card_partner)


@bot.callback_query_handler(func=lambda callback: callback.data == "top_up_one_time_balance")
def top_up_phone_balance_from_balance_partner(callback):
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    user_info = db.get_user_info(callback.from_user.id)
    balance = user_info[4]
    if balance > 8.0:
        if user_info[6]:
            bot.send_message(chat_id=callback.from_user.id,
                             text="📱 Введите номер телефона в формате <b>+7990XXXXXXX</b>:")
            bot.register_next_step_handler(callback.message, number_for_top_up_from_balance)
        else:
            bot.send_message(chat_id=callback.from_user.id,
                             text="📱 Введите номер телефона в формате <b>+7990XXXXXXX</b>:")
            bot.register_next_step_handler(callback.message, number_for_top_up_from_balance)
    else:
        bot.send_message(chat_id=callback.from_user.id,
                         text="У Вас недостаточно средств на балансе аккаунта. Минимальная сумма пополнения 10 рублей.")
        bot.send_message(chat_id=callback.from_user.id,
                         text="📤 Выберите действие:",
                         reply_markup=partners_keyboard.main_menu_reply_keyboard())


@bot.callback_query_handler(func=lambda callback: callback.data == "cancel_payment_partner")
def cancel_payment_partner(callback):
    payments['in_process_balance_partner'][str(callback.from_user.id)] = []
    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
    bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    bot.send_message(chat_id=callback.from_user.id,
                     text="❌ Ваш заказ отменён.",
                     reply_markup=None)
    bot.send_message(chat_id=callback.from_user.id,
                     text="📤 Выберите действие:",
                     reply_markup=partners_keyboard.main_menu_reply_keyboard())


#######################################################################################################################


def check_new_payments_handler():
    while True:
        in_process_balance = payments['in_process_balance'].copy()
        for user_id in in_process_balance:
            if in_process_balance[user_id]:
                account_id = in_process_balance[user_id][0]
                asked_top_up_time = in_process_balance[user_id][1]
                asked_top_up_time_datetime = datetime.fromtimestamp(asked_top_up_time)
                amount = in_process_balance[user_id][2]
                final_time = asked_top_up_time + 900
                if int(time.time()) <= final_time:
                    current_time_now = datetime.now()
                    try:
                        all_payments = mono.get_statements(account_id, asked_top_up_time_datetime, current_time_now)
                    except:
                        continue
                    for payment in all_payments:
                        amount_for_dif = amount.replace(".", "")
                        if str(payment['amount']) == amount_for_dif:
                            db.update_user_balance(user_id, amount)
                            db.insert_account_balance_transaction(user_id, amount)
                            try:
                                bot.send_message(chat_id=user_id,
                                                text="<b>Ваш платёж одобрен!</b>",
                                                reply_markup=None)
                            except:
                                continue

                            user_type = db.check_user_type(user_id)
                            if user_type == 'client' and user_type != 'blocked':
                                user_info = db.get_user_info(user_id)
                                try:
                                    bot.send_message(chat_id=user_id,
                                                    text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n💵 Баланс: <code>{user_info[4]}</code> грн.\n💳 Сумма пополнений: <code>{user_info[5]}</code> грн.",
                                                    reply_markup=client_keyboard.top_up_balance_keyboard())
                                    bot.send_message(chat_id=user_id,
                                                    text="📤 Выберите действие:",
                                                    reply_markup=client_keyboard.main_menu_reply_keyboard())
                                except:
                                    continue
                            payments['in_process_balance'][user_id] = []
                            json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
                            continue
                    time.sleep(10)
                else:
                    try:
                        bot.send_message(chat_id=user_id,
                                        text="❌ Ваш заказ отменён системой так как время на оплату вышло. Если Вы оплатили и видите это сообщение , нажмите на кнопку ниже для связи с поддержкой.",
                                        reply_markup=client_keyboard.get_in_touch_with_support_keyboard())
                        bot.send_message(chat_id=user_id,
                                        text="📤 Выберите действие:",
                                        reply_markup=client_keyboard.main_menu_reply_keyboard())
                    except:
                        continue
                    payments['in_process_balance'][user_id] = []
                    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)

        in_process_web_balance = payments['in_process_web_balance'].copy()
        for user_id in in_process_web_balance:
            if in_process_web_balance[user_id]:
                account_id = in_process_web_balance[user_id][0]
                asked_top_up_time = in_process_web_balance[user_id][1]
                asked_top_up_time_datetime = datetime.fromtimestamp(asked_top_up_time)
                amount = in_process_web_balance[user_id][2]
                amount_for_website = in_process_web_balance[user_id][3]
                number_personal_account = in_process_web_balance[user_id][4]
                service = in_process_web_balance[user_id][5]
                message_text = in_process_web_balance[user_id][6]
                final_time = asked_top_up_time + 900

                partner_number = services_dict[service][
                                 services_dict[service].find("(") + 1:services_dict[service].find(")")]
                if int(time.time()) <= final_time:
                    current_time_now = datetime.now()
                    try:
                        all_payments = mono.get_statements(account_id, asked_top_up_time_datetime, current_time_now)
                    except:
                        continue
                    for payment in all_payments:
                        amount_for_dif = amount.replace(".", "")
                        if str(payment['amount']) == amount_for_dif:
                            try:
                                bot.send_message(chat_id=user_id,
                                                text="<b>Ваш платёж одобрен!</b>",
                                                reply_markup=None)
                                bot.send_message(user_id,
                                                text=f"Баланс будет пополнен в течение нескольких минут. Ждите.")
                            except:
                                continue
                            db.update_user_transactions(user_id, amount)
                            try:
                                balance_top_upped = top_up_balance_on_website(number_personal_account, amount_for_website,
                                                                              service)
                            except:
                                db.insert_user_transaction(user_id, number_personal_account, 1, partner_number,
                                                           message_text,
                                                           "Ошибка провайдера")
                                db.update_user_balance(user_id, amount)
                                try:
                                    bot.send_message(user_id,
                                                    text=f"Баланс не был пополнен. Неполадки на стороне бота. Попробуйте позже. Деньги были переведены на Ваш баланс аккуанта для дальнейших пополнений.")
                                except:
                                    continue
                                user_type = db.check_user_type(user_id)
                                try:
                                    if user_type == "client":
                                        bot.send_message(chat_id=user_id,
                                                        text="📤 Выберите действие:",
                                                        reply_markup=client_keyboard.main_menu_reply_keyboard())
                                    elif user_type == "manager":
                                        bot.send_message(chat_id=user_id,
                                                        text="📤 Выберите действие:",
                                                        reply_markup=managers_keyboard.main_menu_reply_keyboard())
                                    elif user_type == "partner":
                                        bot.send_message(chat_id=user_id,
                                                        text="📤 Выберите действие:",
                                                        reply_markup=partners_keyboard.main_menu_reply_keyboard())
                                except:
                                    continue
                                payments['in_process_web_balance'][user_id] = []
                                json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
                                continue
                            if balance_top_upped:
                                try:
                                    bot.send_message(user_id,
                                                    text=f"Баланс пополнен. Проверьте баланс.")
                                    bot.send_message(chat_id=user_id,
                                                    text="📤 Выберите действие:",
                                                    reply_markup=client_keyboard.main_menu_reply_keyboard())
                                except:
                                    continue
                                db.insert_user_transaction(user_id, number_personal_account, 1, partner_number,
                                                           message_text,
                                                           "Успешно")
                                payments['in_process_web_balance'][user_id] = []
                                json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
                                continue
                            else:
                                if service == "msk":
                                    try:
                                        service = "msk_2"
                                        balance_top_upped = top_up_balance_on_website(number_personal_account,
                                                                                      amount_for_website,
                                                                                      service)
                                    except:
                                        db.insert_user_transaction(user_id, number_personal_account, 1,
                                                                   partner_number,
                                                                   message_text,
                                                                   "Ошибка провайдера")
                                        db.update_user_balance(user_id, amount)
                                        try:
                                            bot.send_message(user_id,
                                                            text=f"Баланс не был пополнен. Неполадки на стороне бота. Попробуйте позже. Деньги были переведены на Ваш баланс аккуанта для дальнейших пополнений.")
                                        except:
                                            continue
                                        user_type = db.check_user_type(user_id)
                                        try:
                                            if user_type == "client":
                                                bot.send_message(chat_id=user_id,
                                                                text="📤 Выберите действие:",
                                                                reply_markup=client_keyboard.main_menu_reply_keyboard())
                                            elif user_type == "manager":
                                                bot.send_message(chat_id=user_id,
                                                                text="📤 Выберите действие:",
                                                                reply_markup=managers_keyboard.main_menu_reply_keyboard())
                                            elif user_type == "partner":
                                                bot.send_message(chat_id=user_id,
                                                                text="📤 Выберите действие:",
                                                                reply_markup=partners_keyboard.main_menu_reply_keyboard())
                                        except:
                                            continue
                                        del payments['in_process_web_balance'][user_id]
                                        json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"),
                                                  indent=4)
                                        continue
                                    if balance_top_upped:
                                        db.insert_user_transaction(user_id, number_personal_account, 1,
                                                                   partner_number,
                                                                   message_text,
                                                                   "Успешно")
                                        try:
                                            bot.send_message(user_id,
                                                            text=f"Баланс пополнен. Проверьте баланс.")
                                            bot.send_message(chat_id=user_id, text="📤 Выберите действие:",
                                                            reply_markup=client_keyboard.main_menu_reply_keyboard())
                                        except:
                                            continue
                                    else:
                                        db.insert_user_transaction(user_id, number_personal_account, 1,
                                                                   partner_number,
                                                                   message_text,
                                                                   "Ошибка провайдера")
                                        db.update_user_balance(user_id, amount)
                                        try:
                                            bot.send_message(user_id,
                                                            text=f"Баланс не был пополнен. Неверно введены данные. Деньги были переведены на Ваш баланс аккуанта для дальнейших пополнений.")
                                        except:
                                            continue
                                        user_type = db.check_user_type(user_id)
                                        try:
                                            if user_type == "client":
                                                    bot.send_message(chat_id=user_id,
                                                                    text="📤 Выберите действие:",
                                                                    reply_markup=client_keyboard.main_menu_reply_keyboard())
                                            elif user_type == "manager":
                                                bot.send_message(chat_id=user_id,
                                                                text="📤 Выберите действие:",
                                                                reply_markup=managers_keyboard.main_menu_reply_keyboard())
                                            elif user_type == "partner":
                                                bot.send_message(chat_id=user_id,
                                                                text="📤 Выберите действие:",
                                                                reply_markup=partners_keyboard.main_menu_reply_keyboard())
                                        except:
                                            continue
                                        del payments['in_process_web_balance'][user_id]
                                        json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"),
                                                  indent=4)
                                else:
                                    db.insert_user_transaction(user_id, number_personal_account, 1,
                                                               partner_number,
                                                               message_text,
                                                               "Ошибка провайдера")
                                    db.update_user_balance(user_id, amount)
                                    try:
                                        bot.send_message(user_id,
                                                        text=f"Баланс номера не был пополнен. Неверно введены данные. Деньги были переведены на Ваш баланс аккуанта для дальнейших пополнений.")
                                        bot.send_message(chat_id=user_id,
                                                        text="📤 Выберите действие:",
                                                        reply_markup=client_keyboard.main_menu_reply_keyboard())
                                    except:
                                        continue
                                    del payments['in_process_web_balance'][user_id]
                                    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"),
                                              indent=4)
                    time.sleep(10)
                else:
                    db.insert_user_transaction(user_id, number_personal_account, 1,
                                               partner_number,
                                               message_text,
                                               "Ошибка перевода от клиента")
                    try:
                        bot.send_message(chat_id=user_id,
                                        text="❌ Ваш заказ отменён системой так как время на оплату вышло. Если Вы оплатили и видите это сообщение , нажмите на кнопку ниже для связи с поддержкой.",
                                        reply_markup=client_keyboard.get_in_touch_with_support_keyboard())
                        bot.send_message(chat_id=user_id,
                                        text="📤 Выберите действие:",
                                        reply_markup=client_keyboard.main_menu_reply_keyboard())
                    except:
                        continue
                    payments['in_process_web_balance'][user_id] = []
                    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)

        in_process_balance_manager = payments['in_process_balance_manager'].copy()
        for user_id in in_process_balance_manager:
            if in_process_balance_manager[user_id]:
                account_id = in_process_balance_manager[user_id][0]
                asked_top_up_time = in_process_balance_manager[user_id][1]
                asked_top_up_time_datetime = datetime.fromtimestamp(asked_top_up_time)
                amount = in_process_balance_manager[user_id][2]
                final_time = asked_top_up_time + 900
                if int(time.time()) <= final_time:
                    current_time_now = datetime.now()
                    try:
                        all_payments = mono.get_statements(account_id, asked_top_up_time_datetime, current_time_now)
                    except:
                        continue
                    for payment in all_payments:
                        amount_for_dif = amount.replace(".", "")
                        if str(payment['amount']) == amount_for_dif:
                            db.update_user_balance(user_id, amount)
                            db.insert_account_balance_transaction(user_id, amount)
                            try:
                                bot.send_message(chat_id=user_id,
                                                text="<b>Ваш платёж одобрен!</b>",
                                                reply_markup=None)
                            except:
                                continue
                            user_type = db.check_user_type(user_id)
                            if user_type == 'manager' and user_type != 'blocked':
                                user_info = db.get_user_info(user_id)
                                try:
                                    bot.send_message(chat_id=user_id,
                                                    text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n💵 Баланс: <code>{user_info[4]}</code> грн.\n💳 Сумма пополнений: <code>{user_info[5]}</code> грн.",
                                                    reply_markup=managers_keyboard.top_up_balance_keyboard())
                                    bot.send_message(chat_id=user_id,
                                                    text="📤 Выберите действие:",
                                                    reply_markup=managers_keyboard.main_menu_reply_keyboard())
                                except:
                                    continue
                            payments['in_process_balance_manager'][user_id] = []
                            json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
                            continue
                    time.sleep(10)
                else:
                    try:
                        bot.send_message(chat_id=user_id,
                                        text="❌ Ваш заказ отменён системой так как время на оплату вышло. Если Вы оплатили и видите это сообщение , нажмите на кнопку ниже для связи с поддержкой.",
                                        reply_markup=client_keyboard.get_in_touch_with_support_keyboard())
                        bot.send_message(chat_id=user_id,
                                        text="📤 Выберите действие:",
                                        reply_markup=managers_keyboard.main_menu_reply_keyboard())
                    except:
                        continue
                    payments['in_process_balance_manager'][user_id] = []
                    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)

        in_process_balance_partner = payments['in_process_balance_partner'].copy()
        for user_id in in_process_balance_partner:
            if in_process_balance_partner[user_id]:
                account_id = in_process_balance_partner[user_id][0]
                asked_top_up_time = in_process_balance_partner[user_id][1]
                asked_top_up_time_datetime = datetime.fromtimestamp(asked_top_up_time)
                amount = in_process_balance_partner[user_id][2]
                final_time = asked_top_up_time + 900
                if int(time.time()) <= final_time:
                    current_time_now = datetime.now()
                    try:
                        all_payments = mono.get_statements(account_id, asked_top_up_time_datetime, current_time_now)
                    except:
                        continue
                    for payment in all_payments:
                        amount_for_dif = amount.replace(".", "")
                        if str(payment['amount']) == amount_for_dif:
                            if partners_data['partners_transactions_amount'][str(user_id)][0] > 100000.0:
                                amount = float(amount) + (10 / 100) * float(amount)
                            elif partners_data['partners_transactions_amount'][str(user_id)][0] > 50000.0:
                                amount = float(amount) + (7 / 100) * float(amount)
                            elif partners_data['partners_transactions_amount'][str(user_id)][0] > 30000.0:
                                amount = float(amount) + (6 / 100) * float(amount)
                            elif partners_data['partners_transactions_amount'][str(user_id)][0] > 15000.0:
                                amount = float(amount) + (5 / 100) * float(amount)

                            db.update_user_balance(user_id, amount)
                            db.insert_account_balance_transaction(user_id, amount)

                            partners_data['partners_transactions_amount'][user_id][0] += round(float(amount), 2)
                            json.dump(partners_data, open("partners.json", "w", encoding="utf-8"), indent=4)
                            try:
                                bot.send_message(chat_id=user_id,
                                                text="<b>Ваш платёж одобрен!</b>",
                                                reply_markup=None)
                            except:
                                continue
                            user_type = db.check_user_type(user_id)
                            if user_type == 'partner' and user_type != 'blocked':
                                user_info = db.get_user_info(user_id)
                                if partners_data['partners_transactions_amount'][str(user_id)][
                                    0] > 100000.0:
                                    current_discount = 10
                                elif partners_data['partners_transactions_amount'][str(user_id)][
                                    0] > 50000.0:
                                    current_discount = 7
                                    possible_discount = 10
                                    needs_to_top_up = 100000.0 - partners_data['partners_transactions_amount'][
                                        str(user_id)][0]
                                    needs_to_top_up = round(needs_to_top_up, 2)
                                elif partners_data['partners_transactions_amount'][str(user_id)][
                                    0] > 30000.0:
                                    current_discount = 6
                                    possible_discount = 7
                                    needs_to_top_up = 50000.0 - partners_data['partners_transactions_amount'][
                                        str(user_id)][0]
                                    needs_to_top_up = round(needs_to_top_up, 2)
                                elif partners_data['partners_transactions_amount'][str(user_id)][
                                    0] > 15000.0:
                                    current_discount = 5
                                    possible_discount = 6
                                    needs_to_top_up = 30000.0 - partners_data['partners_transactions_amount'][
                                        str(user_id)][0]
                                    needs_to_top_up = round(needs_to_top_up, 2)
                                else:
                                    current_discount = 0
                                    possible_discount = 5
                                    needs_to_top_up = 15000.0 - partners_data['partners_transactions_amount'][
                                        str(user_id)][0]
                                    needs_to_top_up = round(needs_to_top_up, 2)
                                if current_discount == 10:
                                    try:
                                        bot.send_message(chat_id=user_id,
                                                        text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n"
                                                            f"💵 Баланс: <code>{user_info[4]}</code> грн.\n"
                                                            f"За последние 30 дней\n"
                                                            f"Общая сумма пополнения {partners_data['partners_transactions_amount'][str(user_id)][0]} грн.\n"
                                                            f"Имеете дополнительную скидку {current_discount}%\n",
                                                        reply_markup=partners_keyboard.top_up_balance_keyboard())
                                    except:
                                        continue
                                else:
                                    try:
                                        bot.send_message(chat_id=user_id,
                                                        text=f"👨‍💻 ID: <code>{user_info[1]}</code>\n"
                                                            f"💵 Баланс: <code>{user_info[4]}</code> грн.\n"
                                                            f"За последние 30 дней\n"
                                                            f"Общая сумма пополнения {partners_data['partners_transactions_amount'][str(user_id)][0]} грн.\n"
                                                            f"Имеете дополнительную скидку {current_discount}%\n"
                                                            f"Для достижения скидки {possible_discount}% необходимо пополнить {needs_to_top_up} грн.",
                                                        reply_markup=partners_keyboard.top_up_balance_keyboard())
                                    except:
                                        continue
                                try:
                                    bot.send_message(chat_id=user_id,
                                                    text="📤 Выберите действие:",
                                                    reply_markup=partners_keyboard.main_menu_reply_keyboard())
                                except:
                                    continue
                            payments['in_process_balance_partner'][user_id] = []
                            json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)
                            continue
                    time.sleep(10)
                else:
                    try:
                        bot.send_message(chat_id=user_id,
                                        text="❌ Ваш заказ отменён системой так как время на оплату вышло. Если Вы оплатили и видите это сообщение , нажмите на кнопку ниже для связи с поддержкой.",
                                        reply_markup=client_keyboard.get_in_touch_with_support_keyboard())
                        bot.send_message(chat_id=user_id,
                                        text="📤 Выберите действие:",
                                        reply_markup=partners_keyboard.main_menu_reply_keyboard())
                    except:
                        continue
                    payments['in_process_balance_partner'][user_id] = []
                    json.dump(payments, open("payments_in_process.json", "w", encoding="utf-8"), indent=4)

        for partner_data in partners_data['partners_transactions_amount']:
            if partners_data['partners_transactions_amount'][partner_data][1] + 2592000 <= int(time.time()):
                partners_data['partners_transactions_amount'][partner_data][0] = 0.0
                json.dump(partners_data, open("partners.json", "w", encoding="utf-8"), indent=4)

        pause.seconds(10)


@bot.message_handler(func=lambda message: message.text != "/start" and message.text != "🛒 Список услуг"
                                          and message.text != "📲 Пополнить" and message.text != "💰 Баланс аккаунта"
                                          and message.text != "💬 Чат/отзывы"
                                          and message.text != "⁉️ Написать оператору"
                                          and message.text != "📔 Правила" and message.text != "Инструкция"
                                          and message.text != "Полезная информация" and message.text != "/manager"
                                          and message.text != "💰 Баланс аккаунта менеджера"
                                          and message.text != "/admin" and message.text != "Сменить номер карты"
                                          and message.text != "Сменить данные для входа PayBerry"
                                          and message.text != "Блокировка пользователя по ID"
                                          and message.text != "Разблокировать пользователя по ID"
                                          and message.text != "Добавление менеджера по ID"
                                          and message.text != "Удаление менеджера по ID"
                                          and message.text != "Изменить Курс1" and message.text != "Изменить Курс2"
                                          and message.text != "Изменить Курс3"
                                          and message.text != "Отключить пополнения"
                                          and message.text != "Включить пополнения"
                                          and message.text != "/partner"
                                          and message.text != "💰 Баланс аккаунта партнёра"
                                          and message.text != "Рассылка по группам пользователей")
def catch_any_message(message):
    user_type = db.check_user_type(message.from_user.id)
    if user_type == 'client' and user_type != 'blocked':
        bot.forward_message(chat_id=MANAGER_ID, from_chat_id=message.chat.id,
                            message_id=message.id)
        bot.send_message(chat_id=MANAGER_ID, text=f"ID пользователя отправителя: <code>{message.from_user.id}</code> ⬆️")


if __name__ == "__main__":
    threading.Thread(target=check_new_payments_handler).start()
    bot.infinity_polling(timeout=900, long_polling_timeout=5)
