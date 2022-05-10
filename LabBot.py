# LabBot
# Telegram bot for monitoring lab sensors.
#
# This bot will check the data logs and send warnings to the users in LIST_OF_USERS in case of any problems.
# Such problems include pressures or temperatures getting too high. Also if there are no recent logs available,
# which can happen in case of a power outage.
#
# Furthermore, the bot can respond to request and send the actual pressure and temperature status.
# Also it can generate graphs with specific date ranges.
# A user notification system is available.
# Type "h" or "help" for more information about the bot.
#
# Alex Riss, 2018-2020, GPL
#
# TODO:
#   - list of active warnings and respective next warning time; give it out numbered, then specific warnings can be silenced
#   - better comments and documentation
#   - unit tests
#   - bakeout control and sending of webcam photos


from functools import wraps
import calendar
import copy
import datetime
import datemath
import io
import logging
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pickle
import random
import re
import socket
import sys
import threading
import traceback
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, MessageFilter, Filters
from telegram import ChatAction
from collections import deque

# import configuration
import LabBot_config as cfg


class LabBot:
    def __init__(self):
        self.__version__ = 0.25

        self.LOG_last_checked = None     # date and time of when the log was last checked
        self.LOG_data = {}               # data of one log line, keys are labels
        self.LOG_labels = []             # labels for log data
        self.LOG_labels_nice = {}        # labels for log data with string replacements (keys are the LOG_labels)
        # list of users with dictionary of errors, keys are the error strings and values contain extra error information
        self.ERRORS_checks = {}
        # dictionary of errors, keys are the error strings and values contain timestamp of last written log
        self.LOGGING_last_write = {}
        self.USER_config = {}            # dictionary of user id with config data

        self.MEASURE_requests = {}       # dictionary containing entities to measure on command, keys are the entity

        self.logging_filename = ""
        self.check_logging_file(force=True)

        # these class variables will be written and loaded from the configuration file
        self.config_vars = ['ERRORS_checks', 'USER_config']
        self.save_config = False  # whether to save the config

        if os.path.isfile(cfg.USER_CONFIG_FILE):
            self.config_load()

        # set default values for user config
        for user in cfg.LIST_OF_USERS:
            if user not in self.USER_config:
                self.USER_config[user] = {
                    'quiet_times': True,
                    'last_commands': deque(maxlen=cfg.NUM_SAVE_LAST_COMMANDS)
                }
            if 'last_commands' not in self.USER_config[user]:
                self.USER_config[user]['last_commands'] = deque(maxlen=cfg.NUM_SAVE_LAST_COMMANDS)
            while len(self.USER_config[user]['last_commands']) > cfg.NUM_SAVE_LAST_COMMANDS:  # in case the number is decreased in the config
                self.USER_config[user]['last_commands'].popleft()

        self.updater = Updater(token=cfg.BOT_TOKEN, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.bot = self.updater.bot

        self.setup_handlers()

        button_list = [
            telegram.InlineKeyboardButton("graph", callback_data='/graph'),
            telegram.InlineKeyboardButton("graph+", callback_data='/graph+'),
            telegram.InlineKeyboardButton("notify", callback_data='/n'),
            telegram.InlineKeyboardButton("warnings", callback_data='/warning'),
            telegram.InlineKeyboardButton("status", callback_data='/status'),
            telegram.InlineKeyboardButton("status+", callback_data='/status+'),
            telegram.InlineKeyboardButton("last", callback_data='/last'),
            telegram.InlineKeyboardButton("help", callback_data='/help')
            # telegram.InlineKeyboardButton("bakeout", callback_data='/bakeout'),
            # telegram.InlineKeyboardButton("photo", callback_data='/photo')
        ]
        self.reply_markup = telegram.InlineKeyboardMarkup(self.build_menu(button_list, n_cols=4, new_cols_at=[3]))

        logging.info('{} set up.'.format(cfg.BOT_ID))

    def get_version(self, markdown=False):
        """returns class version information"""
        if markdown:
            str_out = '*{}* ({})'
        else:
            str_out = '{} ({})'
        return str_out.format(self.__version__,
                              datetime.datetime.fromtimestamp(os.path.getmtime(sys.argv[0])).strftime(cfg.DATE_FMT_BOT))

    def send_action(action):
        """Sends `action` while processing func command."""
        def decorator(func):
            @wraps(func)
            def command_func(*args, **kwargs):
                self, update, context = args[0:3]
                if 'chat_id' not in kwargs.keys():
                    kwargs['chat_id'] = 0
                chat_id = self.get_chat_id(update, kwargs['chat_id'])
                if context:
                    bot = context.bot
                else:
                    bot = self.bot
                bot.send_chat_action(chat_id=chat_id, action=action)
                func(self, update, context, **kwargs)
            return command_func
        return decorator

    def restricted(func):
        @wraps(func)
        def wrapped(self, update, context, *args, **kwargs):
            if 'chat_id' not in kwargs.keys():
                kwargs['chat_id'] = 0
            chat_id = self.get_chat_id(update, kwargs['chat_id'])
            if hasattr(update, 'effective_user'):
                user_id = update.effective_user.id
            else:
                user_id = chat_id
            if user_id not in cfg.LIST_OF_USERS:
                print("Unauthorized access denied for {}.".format(user_id))
                logging.warning("Unauthorized access denied for {}.".format(user_id))
                return
            return func(self, update, context, *args, **kwargs)
        return wrapped

    def setup_handlers(self):
        """sets up the message handlers for the bot"""

        class FilterPressure(MessageFilter):
            def filter(self, message):
                if not message.text:
                    return False
                return (('pressure' in message.text.lower()) or ('status' in message.text.lower()))

        class FilterBakeout(MessageFilter):
            def filter(self, message):
                if not message.text:
                    return False
                return 'bakeout' in message.text.lower()

        class FilterPhoto(MessageFilter):
            def filter(self, message):
                if not message.text:
                    return False
                return 'photo' in message.text.lower()

        class FilterHelp(MessageFilter):
            def filter(self, message):
                if not message.text:
                    return False
                return (('help' in message.text.lower()) or 'h' == message.text.lower())

        class FilterGraph(MessageFilter):
            def filter(self, message):
                if not message.text:
                    return False
                return (('graph' in message.text.lower()) or 'g' == message.text.lower())

        class FilterLast(MessageFilter):
            def filter(self, message):
                if not message.text:
                    return False
                return (('last' in message.text.lower()) or 'l' == message.text.lower())

        self.commands = [  # will be used in the message_command_handler
            {'keywords': ['start', 'hello', 'hi'], 'func': self.hello_handler},
            {'keywords': ['temp', 'temperature', 't', 's', 'status',
                          'pressure', 'status', 'p'], 'func': self.status_sensors},
            {'keywords': ['graph', 'g'], 'func': self.status_graph},
            {'keywords': ['limit', 'limits'], 'func': self.limits_config},
            {'keywords': ['warning', 'warnings', 'w'], 'func': self.active_warnings},
            {'keywords': ['notify', 'n'], 'func': self.user_notifications_manage},
            {'keywords': ['silence'], 'func': self.silence_errors},
            {'keywords': ['v', 'version'], 'func': self.version_handler},
            {'keywords': ['d', 'time', 'datetime', 'date', 't'], 'func': self.datetime_handler},
            {'keywords': ['last', 'l', '.'], 'func': self.last_command},
        ]

        self.dispatcher.add_handler(CommandHandler(['start', 'hello', 'hi'], self.hello_handler))
        self.dispatcher.add_handler(CommandHandler('silence', self.silence_errors))  # uses args
        self.dispatcher.add_handler(CommandHandler(['help', 'h'], self.help_message))
        self.dispatcher.add_handler(CommandHandler(['v', 'version'], self.version_handler))
        self.dispatcher.add_handler(CommandHandler(['d', 'time', 'datetime', 'date'], self.datetime_handler))
        self.dispatcher.add_handler(CommandHandler(['messageall', 'ma'], self.send_message_users))  # uses args
        self.dispatcher.add_handler(CommandHandler(['notify', 'n'], self.user_notifications_manage))  # uses args
        self.dispatcher.add_handler(CommandHandler(['graph', 'g'], self.status_graph))  # uses args
        self.dispatcher.add_handler(CommandHandler(['warning', 'warnings', 'w'], self.active_warnings))
        self.dispatcher.add_handler(CommandHandler(['limit', 'limits'], self.limits_config))
        self.dispatcher.add_handler(CommandHandler(
            ['status', 'pressure', 'temperature', 'temp', 's', 'p'], self.status_sensors))  # uses args
        self.dispatcher.add_handler(CommandHandler(['bakeout'], self.status_bakeout))
        self.dispatcher.add_handler(CommandHandler(['measure'], self.measure_handler))  # uses args
        self.dispatcher.add_handler(CommandHandler(['photo', 'pic'], self.status_photo))
        self.dispatcher.add_handler(CommandHandler(['last', 'l'], self.last_command))

        self.dispatcher.add_handler(MessageHandler(Filters.command, self.unknown_command_handler))

        self.dispatcher.add_handler(MessageHandler(FilterPressure(), self.status_sensors))
        self.dispatcher.add_handler(MessageHandler(FilterBakeout(), self.status_bakeout))
        self.dispatcher.add_handler(MessageHandler(FilterPhoto(), self.status_photo))
        self.dispatcher.add_handler(MessageHandler(FilterHelp(), self.help_message))
        self.dispatcher.add_handler(MessageHandler(FilterGraph(), self.status_graph))
        self.dispatcher.add_handler(MessageHandler(FilterLast(), self.last_command))
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.message_command_handler))

        self.dispatcher.add_handler(CallbackQueryHandler(self.callback_handler))
        self.dispatcher.add_error_handler(self.error_callback)

    def error_callback(self, update, context):
        try:
            raise context.error
        except telegram.error.Unauthorized:
            if update and update.effective_message:
                logging.warning('Telegram error: Unauthorized user: {}'.format(update.effective_message.chat_id))
        except telegram.error.BadRequest:
            logging.warning('Telegram error: Bad request.')
            if update and update.effective_message:
                context.bot.send_message(chat_id=update.effective_message.chat_id, text=self.pick_random(
                    cfg.TEXTS_ERROR), parse_mode=telegram.ParseMode.MARKDOWN)
        except telegram.error.TimedOut:
            logging.warning('Telegram error: Network timeeout.')
            if update and update.effective_message:
                context.bot.send_message(chat_id=update.effective_message.chat_id, text=self.pick_random(
                    cfg.TEXTS_ERROR), parse_mode=telegram.ParseMode.MARKDOWN)
        except socket.timeout as e:
            logging.warning('Socket timeout: {}.'.format(e))
        except socket.error as e:
            logging.warning('Socket error: {}.'.format(e))
        except telegram.error.NetworkError:
            logging.warning('Telegram error: Network error.')
            if update and update.effective_message:
                context.bot.send_message(chat_id=update.effective_message.chat_id, text=self.pick_random(
                    cfg.TEXTS_ERROR), parse_mode=telegram.ParseMode.MARKDOWN)
        except telegram.error.ChatMigrated as e:
            logging.warning('Telegram error: Chat {} migrated to {}.'.format(update.effective_message.chat_id, e.new_chat_id))
        except telegram.error.TelegramError as e:
            # handle all other telegram related errors
            logging.warning('Telegram error: {}.'.format(e))
        except telegram.vendor.ptb_urllib3.urllib3.exceptions.ReadTimeoutError as e:
            logging.warning('Telegram error: {}.'.format(e))

    def callback_handler(self, update, context):
        """handles inline button callbacks"""
        querydata = update.callback_query.data
        if querydata == '/status':
            self.status_sensors(update, context)
        if querydata == '/status+':
            self.status_sensors(update, context, args=["grad"])
        elif querydata == '/graph':
            self.status_graph(update, context)
        elif querydata == '/graph+':
            self.status_graph(update, context, args=["fit"])
        elif querydata == '/bakeout':
            self.status_bakeout(update, context)
        elif querydata == '/photo':
            self.status_photo(update, context)
        elif querydata == '/help':
            self.help_message(update, context)
        elif querydata == '/n':
            self.user_notifications_manage(update, context, args=['list'])
        elif querydata == '/warning':
            self.active_warnings(update, context)
        elif querydata == '/last':
            self.last_command(update, context)

    @restricted
    @send_action(ChatAction.TYPING)
    def unknown_command_handler(self, update, context, chat_id=0):
        """respond to unknown command"""
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=self.pick_random(cfg.TEXTS_UNKNOWN_COMMAND),
                         parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)

    @restricted
    @send_action(ChatAction.TYPING)
    def datetime_handler(self, update, context, args=[], chat_id=0):
        """return current date and time"""
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=datetime.datetime.now().strftime(
            cfg.DATE_FMT_BOT), parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('Datetime sent to {}'.format(update.effective_message.chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def version_handler(self, update, context, args=[], chat_id=0):
        """send version information"""
        version = self.get_version(markdown=True)
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=version,
                         parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('Version {} sent to {}'.format(version, update.effective_message.chat_id))

    @restricted
    # @send_action(ChatAction.TYPING)
    def message_command_handler(self, update, context, chat_id=0):
        """checks for possible commands in the message (without the '/' prefix"""

        if not len(update.effective_message.text):
            return False
        args = update.effective_message.text.split()

        if len(args) > 1:  # first arg is the command
            args = args[1:]
        else:
            args = []
        for command in self.commands:  # defined above
            for c in command['keywords']:
                text = update.effective_message.text
                if len(c) <= cfg.MESSAGE_COMMANDS_STRICT_MAXLENGTH:  # be more strict for short commands
                    text = text.split()[0].lower()
                else:
                    text = text[0:len(c)].lower()
                if c == text:
                    command['func'](update, context, args=args)
                    return

        self.unknown_command_handler(update, context)

    def build_menu(self, buttons,
                   n_cols,
                   new_cols_at = [],
                   header_buttons=None,
                   footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def get_chat_id(self, update, chat_id):
        if not chat_id:
            if not update:
                raise ValueError('No chat_id and no update object is provided.')
            if update.effective_message:
                chat_id = update.effective_message.chat_id
            elif update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat_id
            else:
                raise ValueError('No chat_id and no update object is provided.')
        return chat_id

    def str2date(self, x):
        """convert string from log to datetime object"""
        return datetime.datetime.strptime(x, cfg.DATE_FMT_LOG)

    def escape_markdown(self, text):
        """Escape telegram markup symbols."""
        return re.sub(r'([\*_`\[])', r'\\\1', text)

    def pick_random(self, elements):
        """returns random element from elements"""
        return elements[random.randint(0, len(elements) - 1)]

    def get_column_name(self, query, default=False):
        """returns column label associated with query"""
        query = query.lower()
        for key, vals in cfg.COLUMNS_LABELS.items():
            for val in vals:
                if val.lower() == query:  # if val.lower() in query or key.lower() in query:
                    return key
        return default

    def replace_lowerthan(self, log_data):
        """replaces negative values with error codes; also replace nan values"""
        for c, val in log_data.items():
            if val in cfg.VALUES_REPLACE.keys():
                log_data[c] = cfg.VALUES_REPLACE[val]
            elif val != val and 'nan' in cfg.VALUES_REPLACE:  # nan
                log_data[c] = cfg.VALUES_REPLACE['nan']
        return log_data

    def date_format_bot(self, this_date):
        """returns a formatted date according to the config"""
        if datetime.datetime.now() - this_date < datetime.timedelta(hours=cfg.DATE_FMT_BOT_SHORT_HOURS):
            return this_date.strftime(cfg.DATE_FMT_BOT_SHORT)
        else:
            return this_date.strftime(cfg.DATE_FMT_BOT)

    def get_first_last_from_file(self, fname, maxLineLength=120, default=b""):
        """Reads header line and last few lines from a file, returns the bytes"""
        firstlast = default
        try:
            with open(fname, "rb") as fp:
                line0 = fp.readline()
                # get file length
                fp.seek(0, 2)
                size = fp.tell()
                bytelength = maxLineLength * 22
                bytelength = min(size, bytelength)
                fp.seek(-bytelength, 2)  # 2 means "from the end of the file"
                lines = fp.read(bytelength)
                firstlast = line0 + lines
        except OSError:
            logging.warning('Problem reading log file {}.'.format(fname))
        return firstlast

    def add_to_last_commands(self, user, command):
        """adds the last command to the user's list of last commands (no change if the last command did not change)"""
        if len(self.USER_config[user]["last_commands"]) == 0 or self.USER_config[user]["last_commands"][-1] != command:
            self.USER_config[user]["last_commands"].append(command)
            self.save_config = True

    def get_from_last_commands(self, user, num):
        """gets the n-th last commands from the user's list of last commands"""
        if len(self.USER_config[user]["last_commands"]) >= num:
            return self.USER_config[user]["last_commands"][-num]
        else:
            return None

    @restricted
    @send_action(ChatAction.TYPING)
    def hello_handler(self, update, context, args=[], chat_id=0):
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=self.pick_random(cfg.TEXTS_START),
                         parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('Hello {}.'.format(update.effective_message.chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def limits_config(self, update, context, args=[], chat_id=0):
        """lists all limits that are set in the config"""
        chat_id = self.get_chat_id(update, chat_id)
        str_out = '*Warning limits:*\n'
        for key, error in cfg.ERROR_LIMITS_MAX.items():
            str_out += '*{}:* {},  {}\n'.format(self.LOG_labels_nice[error['column']], error['limits'][0], error['limits'][1])

        str_quiet_start = '{:02d}:{:02d}'.format(*divmod(int(cfg.QUIET_TIMES_HOURS_START * 60), 60))
        str_quiet_end = '{:02d}:{:02d}'.format(*divmod(int(cfg.QUIET_TIMES_HOURS_END * 60), 60))
        str_quiet_days = ", ".join(calendar.day_abbr[n] for n in cfg.QUIET_TIMES_WEEKDAYS)
        str_out += '\n_The first value is the upper limit outside of quiet hours, second value is within quiet hours.'
        str_out += ' Quiet hours are from {} to {} on {}. These settings can be changed by your administrator._'.format(str_quiet_start, str_quiet_end, str_quiet_days)
        context.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('List of warning limits sent to {}.'.format(chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def measure_handler(self, update, context, args=[], chat_id=0):
        """send measure commands via a text file"""
        if not args:
            args = context.args
        if not args:
            args = []

        now = datetime.datetime.now()
        chat_id = self.get_chat_id(update, chat_id)

        if len(args) != 1 or args[0].lower() not in cfg.MEASURE_REQUESTS:
            str_out = "I don't know what to measure."
            logging.info("Measure request ({}) by {} unsuccessful.".format(args, chat_id))
            context.bot.send_message(chat_id=chat_id, text=str_out, reply_markup=self.reply_markup)
            return False

        entity = args[0].lower()
        m_dict = cfg.MEASURE_REQUESTS[entity]
        data = self.measure_getlast(entity)
        if data is not None and data.shape[0] > 0:
            date_last_measured = data.tail(1).index.to_pydatetime()[0]
        else:
            date_last_measured = now - datetime.timedelta(days=365)

        # create measure file
        measure_file = now.strftime(m_dict['measure_file'])
        with open(measure_file, 'a'):
            os.utime(measure_file)
        if entity not in self.MEASURE_requests:
            self.MEASURE_requests[entity] = {}
        self.MEASURE_requests[entity]['last_measured'] = date_last_measured
        self.MEASURE_requests[entity]['requested'] = now
        self.MEASURE_requests[entity]['active'] = True
        if 'chat_ids' not in self.MEASURE_requests[entity]:
            self.MEASURE_requests[entity]['chat_ids'] = set()
        self.MEASURE_requests[entity]['chat_ids'].add(chat_id)

        str_out = "Sent request to measure *{}*.".format(entity)
        logging.info("Measure request ({}) by {}.".format(entity, chat_id))
        context.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN)

    @restricted
    @send_action(ChatAction.TYPING)
    def measure_send_result(self, update, context, args=[], chat_id=0):
        """send result of the measurement to the user"""
        chat_id = self.get_chat_id(update, chat_id)
        self.bot.send_message(
            chat_id=chat_id, text=args[0],
            parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup
        )

    def measure_getlast(self, entity, num=1):
        """reads last log entries for a specific measure entity"""
        now = datetime.datetime.now()
        log_file = now.strftime(cfg.MEASURE_REQUESTS[entity]['log_file'])
        selected_lines = self.get_first_last_from_file(log_file)

        df = pd.DataFrame()
        try:
            df = pd.read_csv(io.BytesIO(selected_lines),
                             sep=cfg.LOG_FILE_DELIMITER,
                             comment=cfg.LOG_FILE_DELIMITER_COMMENT_SYMBOL,
                             parse_dates=True,
                             date_parser=self.str2date,
                             skiprows=[1],  # 0 are the column headers, 1 is truncated
                             index_col=0,
                             dtype=float,
                             on_bad_lines="skip")
        except pd.errors.EmptyDataError:
            logging.warning('No data found in log file {}.'.format(log_file))
            return None
        return df[-num:]

    @restricted
    @send_action(ChatAction.TYPING)
    def silence_errors(self, update, context, args=[], chat_id=0):
        """silence current warnings for the specified amount of hours"""
        if not args:
            args = context.args
        if not args:
            args = [0]

        now = datetime.datetime.now()
        chat_id = self.get_chat_id(update, chat_id)

        s_hours = args[0]
        try:
            hours = float(s_hours)
        except ValueError:
            hours = 0

        list_disabled = []
        for error in self.ERRORS_checks.keys():
            if chat_id in self.ERRORS_checks[error]:
                if hours == 0:  # re-enable all warnings
                    self.ERRORS_checks[error][chat_id]['sendNext'] = now - \
                        datetime.timedelta(minutes=cfg.WARNING_SEND_EVERY_MINUTES)
                    logging.info("Error {} enabled by {}.".format(error, chat_id))
                else:
                    self.ERRORS_checks[error][chat_id]['sendNext'] = now + datetime.timedelta(hours=hours)
                    list_disabled.append(error)
                    logging.info("Error {} disabled for {} hours by {}.".format(error, hours, chat_id))

        if hours == 0:
            str_out = 'All warning messages re-enabled.'
        elif len(list_disabled) == 0:
            str_out = 'There are no active warning messages to disable.'
        else:
            str_error_names = ", ".join([cfg.WARNING_NAMES[e] for e in list_disabled])
            str_out = 'Active warning messages ({}) disabled for {} hours.'.format(str_error_names, hours)
        context.bot.send_message(chat_id=chat_id, text=str_out, reply_markup=self.reply_markup)

    @restricted
    def send_message_users(self, update, context, args=[], chat_id=0):
        if not args:
            args = context.args
        if not args:
            args = []
        if len(args) > 0:
            chat_id_sender = self.get_chat_id(update, chat_id)
            name = update.effective_message.from_user.first_name
            str1 = "*Message from {}:*\n\n".format(name)
            str2 = " ".join(args)
            for chat_id in cfg.LIST_OF_USERS:
                context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                context.bot.send_message(chat_id=chat_id, text=str1 + str2, parse_mode=telegram.ParseMode.MARKDOWN)
            logging.info('{} messaged all with: {}.'.format(chat_id_sender, str2))

    def notification_to_string(self, notification):
        """returns string from notification dictionary"""
        comparator = ''
        if notification['comparison'] == 1:
            comparator = '>'
        else:
            comparator = '<'
        str_out = '{} {} {}'.format(self.LOG_labels_nice[notification['column']], comparator, notification['limit'])
        str_out = self.escape_markdown(str_out)
        if 'active' in notification.keys():
            if not notification['active']:
                str_out += ' _(inactive)_'
        return str_out

    def notification_list(self, user):
        """returns notification list"""
        if 'notifications' not in self.USER_config[user].keys():
            str_out = 'No notifications are set up.'
        elif len(self.USER_config[user]['notifications']) < 1:
            str_out = 'No notifications are set up.'
        else:
            str_out = '*Notifications:*\n'  # u"\U0001F4D1"
            for i, n in enumerate(self.USER_config[user]['notifications']):
                str_out += "*{:d}*: {}\n".format(i + 1, self.notification_to_string(n))

        return str_out

    def notification_change(self, user, args, action="act"):
        """deletes, activates, deactivates notifications. Action is one of "act", "deact", "del". """
        is_tochange = []

        if args[0] == 'all':
            is_tochange = range(len(self.USER_config[user]['notifications']))
        else:
            try:
                for a in args:
                    is_tochange.append(int(a) - 1)
            except ValueError:
                pass
        num_changed = 0
        for i in reversed(sorted(is_tochange)):  # we need the reversed and sorted when action is delete
            if i >= 0 and i < len(self.USER_config[user]['notifications']):
                if action == "act":
                    self.USER_config[user]['notifications'][i]['active'] = True
                elif action == "deact":
                    self.USER_config[user]['notifications'][i]['active'] = False
                elif action == "del":
                    del self.USER_config[user]['notifications'][i]
                else:
                    raise ValueError('Unknown action "{}" in function notification_change.'.format(action))
                num_changed += 1
        if num_changed > 0:
            self.save_config = True
        return num_changed

    @restricted
    @send_action(ChatAction.TYPING)
    def user_notifications_manage(self, update, context, args=[], chat_id=0):
        if not args:
            args = context.args
        if not args:
            args = []    
        chat_id = self.get_chat_id(update, chat_id)

        if len(args) == 0:
            context.bot.send_message(chat_id=chat_id, text='Please specify which notification you want to setup,'
                             '\ne.g. "/n temp < 8".\nAlso you can use "/n list" to list notifications'
                             ' and "/n del n" to delete a specific notification.\n\n{}'.format(
                                 self.notification_list(chat_id)), parse_mode=telegram.ParseMode.MARKDOWN)
            logging.info('Notification-setup for {} failed due to wrong format ({}).'.format(chat_id, " ".join(args)))
            return False

        if args[0] in ['list', 'l']:  # list notifications
            str_out = self.notification_list(chat_id)

            context.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN)
            logging.info('Notification list sent to {}.'.format(chat_id))
            return True

        # delete, activate, deactivate
        action_dicts = {
            "deact": {'keywords': ['deact', 'dea', 'inact', 'inactivate', 'deactivate'], 'str_name': 'deactivate', 'str_todo': 'to deactivate', 'str_done': 'deactivated'},
            "act": {'keywords': ['act', 'a', 'activate'], 'str_name': 'activate', 'str_todo': 'to activate', 'str_done': 'activated'},
            "del": {'keywords': ['del', 'delete', 'remove'], 'str_name': 'delete', 'str_todo': 'to delete', 'str_done': 'removed'},
        }
        for action_key, action_dict in action_dicts.items():
            if args[0] in action_dict['keywords']:
                if len(args) <= 1:
                    context.bot.send_message(
                        chat_id=chat_id, text='Please specify which notification to {}, e.g. "n {} 2"'.format(
                            action_dict['str_todo'], action_dict['keywords'][0]
                        ), parse_mode=telegram.ParseMode.MARKDOWN
                    )
                    logging.info(
                        'Notification-{} for {} failed due to wrong format ({}).'.format(
                            action_dict['str_name'], chat_id, " ".join(args)
                        )
                    )
                    return False
                num_changed = self.notification_change(chat_id, args[1:], action_key)

                str_plural = ''
                if num_changed != 1:
                    str_plural = 's'

                context.bot.send_message(chat_id=chat_id, text='{:d} notification{} {}.\n\n{}'.format(
                    num_changed, str_plural, action_dict['str_done'],
                    self.notification_list(chat_id)), parse_mode=telegram.ParseMode.MARKDOWN
                )
                logging.info('Notifications {} for user {}: {:d}.'.format(
                    action_dict['str_done'], chat_id, num_changed))
                return True

        if args[0] in ['add']:
            args = args[1:]

        # remove all special characters and put extra whitespace around '<' and '>', also replace ',' for '.'
        query_string = re.sub(r'[^\w\s<>+-.,]', '',
                              ' '.join(args)).replace('>', ' > ').replace('<', ' < ').replace(',', '.')
        query_items = query_string.split()
        if len(query_items) != 3:
            context.bot.send_message(chat_id=chat_id, text='Notification should contain three elements,\ne.g. "/n temp < 8".',
                             parse_mode=telegram.ParseMode.MARKDOWN)
            logging.info('Notification-setup for {} failed due to wrong format ({}).'.format(chat_id, " ".join(args)))
            return False

        column = self.get_column_name(query_items[0])
        if not column:
            str_out = ", ".join([val[0] for val in cfg.COLUMNS_LABELS.values()])
            context.bot.send_message(
                chat_id=chat_id,
                text='I do not recognize the first element. It should be one of:\n{}'.format(str_out),
                parse_mode=telegram.ParseMode.MARKDOWN
            )
            logging.info('Notification-setup for {} failed due to wrong format ({}).'.format(chat_id, " ".join(args)))
            return False

        comparison = 0
        if query_items[1] in ['>', 'g', 'gt', 'gr']:
            comparison = 1  # for >
        elif query_items[1] in ['<', 's', 'lt', 'l', 'k', 'kl']:
            comparison = -1
        if comparison == 0:  # the query_item was neither "<" nor ">"
            context.bot.send_message(
                chat_id=chat_id,
                text='The second element of the notification should be either "<" or ">",\n e.g. "temp < 8".',
                parse_mode=telegram.ParseMode.MARKDOWN)
            logging.info('Notification-setup for {} failed due to wrong format ({}).'.format(chat_id, " ".join(args)))
            return False

        try:
            limit = float(query_items[2].lower().replace('k', '').replace('mbar', ''))  # remove units
        except ValueError:
            context.bot.send_message(
                chat_id=chat_id,
                text='The third element of the notification should be a number,\n e.g. "temp < 8".',
                parse_mode=telegram.ParseMode.MARKDOWN)
            logging.info('Notification-setup for {} failed due to wrong format ({}).'.format(chat_id, " ".join(args)))
            return False

        n = {'column': column, 'comparison': comparison, 'limit': limit}

        if 'notifications' not in self.USER_config[chat_id].keys():
            self.USER_config[chat_id]['notifications'] = []
        self.USER_config[chat_id]['notifications'].append(n)
        str_out = self.notification_to_string(n)
        self.save_config = True
        context.bot.send_message(chat_id=chat_id, text='Notification set up: {}\n\n{}'.format(
            str_out, self.notification_list(chat_id)), parse_mode=telegram.ParseMode.MARKDOWN)
        logging.info('Notification set up for {}: {}.'.format(chat_id, str_out))

    @restricted
    @send_action(ChatAction.TYPING)
    def status_user_notification(self, update, context, chat_id=0, notification=None):
        """notifies of user-specific notifications"""
        chat_id = self.get_chat_id(update, chat_id)

        str1 = u"\u261D" + ' *User notification: *'
        str2 = self.notification_to_string(notification)

        if context:
            bot = context.box
        else:
            bot = self.bot
        bot.send_message(chat_id=chat_id, text=str1 + str2,
                         parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('User notification sent to {}: {}.'.format(chat_id, str2))

    @restricted
    @send_action(ChatAction.TYPING)
    def help_message(self, update, context, chat_id=0):
        """Prints a help message."""
        chat_id = self.get_chat_id(update, chat_id)
        str_out = 'Ask me for *status updates* using: "status" or "/status" or "s".\n'
        str_out += '"s 0.5" will display the slopes for the last 0.5 hours.\n\n'
        str_out += 'Pressure, temperature and logging warnings will be sent every {:d} minutes. '.format(
            cfg.WARNING_SEND_EVERY_MINUTES)
        str_out += 'Use "limits" to see warning limits.\n\n'
        str_out += '*Active warning messages* are shown using /w or "warnings".\n\n'
        str_out += 'The active *warnings can be silenced* for n hours using the command "/silence n".\n'
        str_out += 'n=0 will re-enable normal warnings.\n\n'
        str_out += '*Graphs* can be plotted using the "graph" keyword or "/graph" and "/g" commands. '
        str_out += 'Extra parameters are possible to specify _from_ and _to_ dates.\n'
        str_out += 'Try: "/g -3d" or "g -12h -10h"\n'
        str_out += 'Also: "/g 20" or "g 2.5d" will work as short notations.\n'
        str_out += 'The graph and status commands both support extra arguments'
        str_out += 'specifying the sensor data that should be plotted.\n'
        str_out += '"g afm prep tafm" or "g all".\n\n'
        str_out += 'You can even do some fits in the graph module: "g tafm fit -0.5 0.5 2" for fitting of the temperature data from 0.5 hours ago to 0.5 hours into the future with a 2nd order polynomial.\n'
        str_out += 'A shortcut is "g tafm fit 0.5" for the same fit but with an order 1 polynomial as default.\n\n'
        str_out += '*User notifications* can be set up using:\n'
        str_out += '/n afm < 1e-10\n'
        str_out += 'n afm lt 1e-10\n'
        str_out += 'n list\n'
        str_out += 'n t < 10\n'
        str_out += 'n list\n'
        str_out += 'n del 1  _(delete notification 1)_\n'
        str_out += 'n deact all  _(deactivate all notifications)_\n'
        str_out += 'n act 1 2 3   _(activate notifications 1,2, and 3)_\n\n'
        str_out += '*Last commands* (status and graph) can be executed using:\n'
        str_out += '"last" or "/l 2" or ". 3 4 5"\n'
        str_out += 'List all last commands with "last list" or "l l"'

        context.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN,
                         reply_markup=self.reply_markup)

    def _calculate_gradients(self, columns, gradient_dates):
        gradients = {}
        from_date = gradient_dates[0]
        if len(gradient_dates) >= 2:
            to_date = gradient_dates[1]
        else:
            to_date = datetime.datetime.now() + datetime.timedelta(hours=1)  # we want some extra time, just in case
        data = self.read_logs(from_date=from_date, to_date=to_date)  # read the necessary log files
        if data is None:
            return gradients

        data = data[(data.index > from_date) & (data.index < to_date)]
        if not data.shape[0]:
            return gradients

        x = pd.to_numeric(data.index) / 1e9  # convert to seconds
        x_start = x[0]
        x -= x_start
        for c in columns:
            if c not in data:
                continue
            xfit = x[:]
            yfit = data[c]
            if c in cfg.GRAPH_IGNORE_LOWERTHAN:
                limit = cfg.GRAPH_IGNORE_LOWERTHAN[c]
                idx = yfit > limit
                xfit = xfit[idx]
                yfit = yfit[idx]

            if len(xfit):
                fit = np.polyfit(xfit, yfit, 1)
                gradients[c] = fit[0] * 60

        return gradients

    @restricted
    @send_action(ChatAction.TYPING)
    def status_sensors(self, update, context, args=[], chat_id=0, error_str="", add_to_last=True):
        if not args:
            if context:
                args = context.args
        if not args:
            args = []
        chat_id = self.get_chat_id(update, chat_id)

        # save in last commands list
        if add_to_last:
            self.add_to_last_commands(chat_id, ["status", args])

        str_out = error_str
        if self.LOG_last_checked:
            str_out += "*{}*".format(self.date_format_bot(self.LOG_last_checked))
        if self.quiet_hours():
            str_out += ' _(quiet hours)_'
        if 'ERROR_log_read' in self.ERRORS_checks:
            str_out += ' ' + cfg.WARNING_SYMBOL

        query_string = ' '.join(args)
        query_string = re.sub(r'[^\w\s\.]', ' ', query_string.replace('-', ''))
        query_items = query_string.split()

        columns = []
        if 'all' in query_items:  # display data for all sensors
            columns = self.LOG_labels
            # add columns from measure requests as well
            for entity, cm_dict in cfg.MEASURE_REQUESTS.items():
                columns.append(cm_dict['column'])
        else:
            for q in query_items:
                c = self.get_column_name(q)
                if c:
                    columns.append(c)
        if not len(columns):
            columns = cfg.STATUS_DEFAULT_COLUMNS.copy()

        # see if we have numbers - these are times for gradient calculation
        gradient_dates = []
        gradients = {}
        for q in query_items:
            if re.match(r'[-+]?[0-9].\.?[0-9]*[YymMdDwHhSs]$', q) or re.match(r'[-+]?[0-9]*\.?[0-9]*$', q):
                gradient_dates.append(self._get_datetime_from_string(q))
        if not len(gradient_dates):
            if "g" in query_items or "grad" in query_items or "gradient" in query_items or 'fit' in query_items or 'f' in query_items or "slope" in query_items:
                gradient_dates.append(datetime.datetime.now() - datetime.timedelta(hours=cfg.STATUS_SLOPE_DEFAULT_FROM_HOURS))

        if len(gradient_dates):
            gradients = self._calculate_gradients(columns, gradient_dates)

        # check if there are any columns associated with errors
        columns_error = []
        error_lists = {}
        error_lists.update(cfg.ERROR_COLUMNS_MUSTHAVE)
        error_lists.update(cfg.ERROR_LIMITS_MAX)
        error_lists.update(cfg.ERROR_LOWERTHAN_VALUES)
        for error, error_dict in error_lists.items():
            if error in self.ERRORS_checks:
                c = error_dict['column']
                if c not in columns:
                    columns.append(c)
                columns_error.append(c)

        log_data_replaced = self.replace_lowerthan(self.LOG_data)
        for c in columns:
            if c in self.LOG_data:
                val = log_data_replaced[c]
                str_error = ''
                if c in columns_error:
                    str_error = " " + cfg.WARNING_SYMBOL
                grad_str = ""
                if c in gradients:
                    grad_str = "      _slope: {:.{prec}g} min⁻¹ _".format(gradients[c], prec=cfg.FLOAT_PRECISION_BOT_GRADIENT)
                if isinstance(val, str):
                    str_out += "\n*{}*: {}{}{}".format(self.LOG_labels_nice[c], val, grad_str, str_error)
                else:
                    str_out += "\n*{}*: {:.{prec}g}{}{}".format(self.LOG_labels_nice[c], val, grad_str, str_error, prec=cfg.FLOAT_PRECISION_BOT)
            else:
                # check the message requests - here we need to read the log file
                for entity, cm_dict in cfg.MEASURE_REQUESTS.items():
                    if c == cm_dict['column']:
                        data = self.measure_getlast(entity, 2)
                        if data is not None and data.shape[0] > 0:
                            date_last_measured = data.tail(1).index.to_pydatetime()[0]
                            # if date_last_measured <= m_dict['last_measured']:
                            #     continue  # no new values in the file yet
                            column_name = cfg.MEASURE_REQUESTS[entity]['column']
                            if column_name not in data:
                                logging.info(
                                    "Status for {}: Column {} not found in log file.".format(entity, column_name)
                                )
                                continue
                            value = data.tail(1)[column_name]
                            column_name_nice = cfg.LOG_NAMES_REPLACEMENT(column_name)
                            str_out += "\n*{}*: {}  _({})_".format(
                                column_name_nice,
                                self.replace_lowerthan(value).values[0],
                                self.date_format_bot(date_last_measured)
                            )
                            # change since last measured
                            if len(gradient_dates) > 0 and len(data) > 1:
                                value1 = data.iloc[-1][column_name]
                                value2 = data.iloc[-2][column_name]
                                if value1 >= 0 and value2 >=0:
                                    value_diff = value2 - value1
                                    hours_diff = (data.index[-1] - data.index[-2]).total_seconds() / 3600
                                    if hours_diff > 0:
                                        str_out += "      _slope: {:.{prec}g} h⁻¹ _".format(value_diff / hours_diff, prec=cfg.FLOAT_PRECISION_BOT_GRADIENT)


        self.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN,
                         reply_markup=self.reply_markup)
        logging.info('Status sent to {}'.format(chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def status_bakeout(self, update, context, chat_id=0, error_str=""):
        chat_id = self.get_chat_id(update, chat_id)
        context.bot.send_message(chat_id=chat_id, text='Sorry, Bakeout-Status is not implemented yet. ',
                         parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('Bakeout-status (not implemented) sent to {}'.format(chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def status_photo(self, update, context, chat_id=0, error_str=""):
        chat_id = self.get_chat_id(update, chat_id)
        context.bot.send_message(chat_id=chat_id, text='Sorry, this is not implemented yet. ',
                         parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
        logging.info('Photo (not implemented) sent to {}.'.format(chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def active_warnings(self, update, context, args=[], chat_id=0):
        self.status_error(update, context, chat_id, send_all=True)

    def status_error(self, update=None, context=None, chat_id=0, send_all=False):
        """sends error messages. If send_all is True, then a list of all errors will be sent"""
        now = datetime.datetime.now()
        str_out = ''
        if send_all:  # there was a user request
            chat_id_request = self.get_chat_id(update, chat_id)

        for chat_id in cfg.LIST_OF_USERS:
            if send_all:
                if chat_id != chat_id_request:
                    continue
            else:
                str_out = ''
            errors_sent = False
            for error in self.ERRORS_checks.keys():
                if chat_id not in self.ERRORS_checks[error]:
                    continue
                if not send_all and self.ERRORS_checks[error][chat_id]['sendNext']:
                    if now <= self.ERRORS_checks[error][chat_id]['sendNext']:
                        continue
                if send_all:
                    str_out += '\n'
                    pre = ''
                else:
                    str_out = ''
                    pre = cfg.WARNING_PRE
                if 'value' in self.ERRORS_checks[error][chat_id]:
                    str_out += pre + cfg.WARNING_MESSAGES[error].format(self.ERRORS_checks[error][chat_id]['value'])
                else:
                    str_out += pre + cfg.WARNING_MESSAGES[error]
                if error == 'ERROR_log_read':
                    if self.LOG_last_checked:
                        str_out += self.LOG_last_checked.strftime(cfg.DATE_FMT_BOT) + '.'
                    else:
                        str_out += 'unknown.'

                if not send_all:
                    self.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                    self.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN)
                    self.ERRORS_checks[error][chat_id]['sendNext'] = now + \
                        datetime.timedelta(minutes=cfg.WARNING_SEND_EVERY_MINUTES)
                    self.ERRORS_checks[error][chat_id]['timesSent'] += 1
                    logging.info('Warning message "{}" sent to {}.'.format(error, chat_id))
                    errors_sent = True
            if errors_sent:
                self.status_sensors(None, context, chat_id=chat_id, add_to_last=False)
            if send_all:
                if str_out:
                    str_out = '*Active warning messages:*' + str_out
                    self.bot.send_message(chat_id=chat_id_request, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
                else:
                    self.bot.send_message(chat_id=chat_id_request, text='No active warning messages.', parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
                logging.info('List of warning messages sent to {}.'.format(chat_id_request))

    def status_error_off(self, errors_off=[], errors_off_only_quiet=[]):
        """resets errors and sends de-warning message."""
        for error, error_off_only_quiet in zip(errors_off, errors_off_only_quiet):
            for chat_id in cfg.LIST_OF_USERS:
                dewarning_sent = False
                if chat_id not in self.ERRORS_checks[error]:
                    continue
                if self.ERRORS_checks[error][chat_id]['timesSent'] > 0:
                    str_out = cfg.WARNING_OFF_PRE + cfg.WARNING_OFF_MESSAGES[error]
                    if error_off_only_quiet:
                        str_out += cfg.WARNING_OFF_MESSAGE_ONLY_QUIET
                    self.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                    self.bot.send_message(chat_id=chat_id, text=str_out, parse_mode=telegram.ParseMode.MARKDOWN)
                    logging.info('De-warning message "{}" sent to {}.'.format(error, chat_id))

                if dewarning_sent:
                    self.status_sensors(None, None, chat_id=chat_id, add_to_last=False)

            self.error_remove(error)

    @restricted
    @send_action(ChatAction.TYPING)
    def status_graph_no_data(self, update, context, args=[], chat_id=0, from_date=None, to_date=None):
        """sends a message that no data is available"""
        d1 = ""
        d2 = ""
        if from_date:
            d1 = from_date.strftime("%Y-%m-%d %H:%M:%S")
        if to_date:
            d2 = to_date.strftime("%Y-%m-%d %H:%M:%S")
        context.bot.send_message(chat_id=chat_id, text='No data available between {} and {}.'.format(
            d1, d2), reply_markup=self.reply_markup)
        logging.info('Graph cannot be sent to {}: No data available between {} and {}.'.format(chat_id, d1, d2))

    def _get_datetime_from_string(self, arg, future=False):
        try:
            arg = str(float(arg)) +'h'  # "20" means "20h"
        except ValueError:
            pass
        if future:
            arg = re.sub(r"^([0-9]*\.?[0-9]+[YymMdDwHhSs])$", r"+\1", arg)  # "20h" means "+20h"
        else:
            arg = re.sub(r"^([0-9]*\.?[0-9]+[YymMdDwHhSs])$", r"-\1", arg)  # "20h" means "-20h"
        
        d = None
        try:
            # dm gives UTC timezone, so first we convert to local timezone and then
            # remove the timezon info (so we can compare with the logged entries)
            d = datemath.dm(arg, type='datetime').astimezone().replace(tzinfo=None)
        except datemath.helpers.DateMathException:
            logging.error('Error when converting {} to datetime.'.format(arg))
        except Exception:
            logging.error('Error when converting {} to datetime.'.format(arg))
            logging.error(traceback.format_exc())
        return d

    @restricted
    @send_action(ChatAction.UPLOAD_PHOTO)
    def status_graph(self, update, context, args=[], chat_id=0, error_str="", add_to_last=True):
        if not args:
            args = context.args
        if not args:
            args = []
        chat_id = self.get_chat_id(update, chat_id)
        context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

        # save in last commands list
        if add_to_last:
            self.add_to_last_commands(chat_id, ["graph", args])

        now = datetime.datetime.now()
        bio = io.BytesIO()
        bio.name = 'AFM_status_graph.png'

        # default values
        from_date = now - datetime.timedelta(days=cfg.GRAPH_DEFAULT_DAYS)
        to_date = now + datetime.timedelta(hours=1)  # we want some extra time, just in case
        from_date_interp = now - datetime.timedelta(hours=cfg.GRAPH_FIT_DEFAULT_FROM_HOURS)
        to_date_interp = now + datetime.timedelta(hours=cfg.GRAPH_FIT_DEFAULT_TO_HOURS)
        order_interp = cfg.GRAPH_FIT_DEFAULT_ORDER
        do_interp = False

        # on cell phones - and + often add spaces afterwards
        args = " ".join(args).replace('- ', '-').replace('+ ', '+').replace(',', '.').split()

        # parse args, get columns to plot
        columns_toplot = []
        if 'all' in args:
            columns_toplot = self.LOG_labels
            args.remove('all')
        else:
            args_to_delete = []
            for i, arg in enumerate(args):
                c = self.get_column_name(arg)
                if c:
                    columns_toplot.append(c)
                    args_to_delete.append(i)
            for i in args_to_delete[::-1]:
                del args[i]
        if not len(columns_toplot):
            columns_toplot = cfg.GRAPH_DEFAULT_COLUMNS

        # parse args, get fit information
        args_interp = []
        for keyword in ['fit', 'gradient', 'grad', 'slope', 'f', 'g']:
            if keyword in args:
                do_interp = True
                pos = args.index(keyword)
                args_interp = args[pos + 1: pos + 4]
                for i in range(pos, pos + len(args_interp) + 1)[::-1]:
                    del args[i]
                break

        # parse args, get time limits
        if len(args) >= 1:
            r = self._get_datetime_from_string(args[0])
            if r:
                from_date = r
        if len(args) >= 2:  # to date
            r = self._get_datetime_from_string(args[1])
            if r:
                to_date = r

        if len(args_interp) >= 1:  # interpolation from_date and to_date
            r = self._get_datetime_from_string(args_interp[0])
            if r:
                from_date_interp = r
        if len(args_interp) >= 2:  # interpolation from_date and to_date
            r = self._get_datetime_from_string(args_interp[1], future=True)
            if r:
                to_date_interp = r

        if len(args_interp) >= 3:   # interpolation order
            try:
                order_interp = int(args_interp[2])
            except ValueError:
                logging.error('Error when converting {} to interpolation order.'.format(args_interp[2]))
            except Exception:
                logging.error('Error when converting {} to interpolation order.'.format(args_interp[2]))

        # small extra sanity checks
        if from_date > to_date:
            from_date, to_date = to_date, from_date
        if from_date_interp > to_date_interp:
            from_date_interp, to_date_interp = to_date_interp, from_date_interp
        if order_interp < 1:
            order_interp = cfg.GRAPH_FIT_DEFAULT_ORDER

        data = self.read_logs(from_date=from_date, to_date=to_date)  # read the necessary log files
        if data is None:
            self.status_graph_no_data(update, context, args=args, chat_id=chat_id, from_date=from_date, to_date=to_date)
            return False
        # filter date range
        # data = data[from_date:to_date]
        # the slicing causes problems for nonmonotonous data,
        # which can happen when DST ends or when the log files are non-monotonous
        data = data[(data.index > from_date) & (data.index < to_date)]
        data_interp = data[(data.index > from_date_interp) & (data.index < to_date_interp)]

        if not (from_date_interp < now < to_date_interp and data_interp.shape[0] > 1):
            do_interp = False

        if not data.shape[0]:
            self.status_graph_no_data(update, context, args=args, chat_id=chat_id, from_date=from_date, to_date=to_date)
            return False

        fig, axs = plt.subplots(
            len(columns_toplot), 1, sharex=True,
            squeeze=False, figsize=(8, 0.5 + 2 * len(columns_toplot))
        )

        # get colors for columns
        colors = {}
        for i, c in enumerate(self.LOG_labels):
            color = plt.cm.tab20(np.linspace(0, 1, len(self.LOG_labels)))[i % len(self.LOG_labels)]
            colors[c] = matplotlib.colors.rgb2hex(color[0:3])
        # colors = ['#1b9e77', '#e41a1c', '#d95f02', '#386cb0', '#285ca0']
        total_count = 0
        for i, c in enumerate(columns_toplot):
            # filter non-positive values
            if c in self.LOG_data:
                axs[i, 0].set_ylabel(self.LOG_labels_nice[c])
            axs[i, 0].tick_params(direction='in')
            if c not in data:
                continue
            if c in cfg.GRAPH_IGNORE_LOWERTHAN:
                limit = cfg.GRAPH_IGNORE_LOWERTHAN[c]
                data[c][data[c] <= limit] = np.nan
                data_interp[c][data_interp[c] <= limit] = np.nan
            logy = False
            if c in cfg.GRAPH_LOG_COLUMNS:
                logy = True
            count = data[c].count()
            total_count += count
            if count:
                data.plot(y=c, ax=axs[i, 0], color=colors[c], ls='-', lw=2, ms=0, legend=None, logy=logy)
                axs[i, 0].grid(which="major", alpha=0.3)
                axs[i, 0].grid(which="minor", alpha=0.1)

            # interpolation
            if do_interp and data_interp[c].count():
                x = pd.to_numeric(data_interp.index)
                y = data_interp[c]
                x_start = x[0]
                x -= x_start

                yfit_func = np.poly1d(np.polyfit(x, y, order_interp))
                xfit = pd.to_numeric(pd.date_range(from_date_interp, to_date_interp, periods=100)) - x_start
                yfit = yfit_func(xfit)
                xplot = pd.to_datetime(xfit + x_start)

                if logy:  # can plot any values <= 0
                    yfit[yfit <= 0] = np.nan
                axs[i,0].plot(xplot, yfit, color=colors[c], ls='--', lw=1, ms=0, alpha=0.5, label=None)

        if not total_count:
            self.status_graph_no_data(update, context, args=args, chat_id=chat_id, from_date=from_date, to_date=to_date)
            return False

        axs[-1, 0].set_xlabel('')
        fig.autofmt_xdate()
        plt.tight_layout(pad=1.02, w_pad=0, h_pad=0)
        # fig.subplots_adjust(wspace=0, hspace=0)
        plt.savefig(bio, format='png', dpi=100)
        bio.seek(0)
        context.bot.send_photo(chat_id=chat_id, photo=bio, reply_markup=self.reply_markup)
        plt.close()
        logging.info('Graph sent to {}.'.format(chat_id))

    @restricted
    @send_action(ChatAction.TYPING)
    def last_command(self, update, context, args=[], chat_id=0, error_str=""):
        """list all last commands or redo (n-th) last command"""
        if not args:
            args = context.args
        if not args:
            args = []
        chat_id = self.get_chat_id(update, chat_id)

        str_out = ""
        if len(args) and args[0] in ["list", "l"]:
            len_last = len(self.USER_config[chat_id]["last_commands"])
            for i, c in enumerate(self.USER_config[chat_id]["last_commands"]):
                str_out += "*{:d}*: {} {}\n".format(len_last - i, c[0], " ".join(c[1]))
            if str_out == "":
                str_out += "_None._"
            str_out = "*Last commands:*\n" + str_out
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=str_out,
                parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)
            logging.info('List of last commands sent to {}.'.format(chat_id))
            return

        ns = []
        for arg in args:
            try:
                ns.append(int(arg))
            except ValueError:
                pass
        if len(ns) == 0:
            ns.append(1)

        num_sent = 0
        logging.info('Sending last {} commands to {}.'.format(ns, chat_id))
        for n in ns:
            res = self.get_from_last_commands(chat_id, n)
            if res is not None:
                c, c_args = res
                if c == "status":
                    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                    self.status_sensors(update, context, args=c_args, chat_id=chat_id, error_str=error_str)
                    num_sent += 1
                elif c == "graph":
                    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
                    self.status_graph(update, context, args=c_args, chat_id=chat_id, error_str=error_str)
                    num_sent += 1
        if num_sent == 0:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text="Last commands not found.",
                parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=self.reply_markup)

    def read_logs(self, from_date, to_date):
        """reads logs for the days between from_date and to_date.
        If the number of columns is too big, it will be reduced using rolling averaging."""

        if from_date > to_date:
            from_date, to_date = to_date, from_date

        diff_seconds = np.abs((to_date - from_date).total_seconds())
        day_seconds = datetime.timedelta(days=1).total_seconds()
        num_days = diff_seconds / day_seconds   # get fraction of days

        if num_days > cfg.GRAPH_DAYS_MAX:
            from_date = to_date - datetime.timedelta(days=cfg.GRAPH_DAYS_MAX)
            num_days = cfg.GRAPH_DAYS_MAX

        datas = []
        # we need to adjust the to_date to get all logs
        to_date_adjusted = to_date + datetime.timedelta(days=cfg.LOG_FILE_EVERY_DAYS)
        this_date = from_date
        while this_date <= to_date_adjusted:
            log_file = this_date.strftime(cfg.LOG_FILE)
            try:
                # we can use skiprows here, but I found that it doesn't really speed up things; so we do the rolling mean in the next line
                df = pd.read_csv(log_file,
                                 sep=cfg.LOG_FILE_DELIMITER,
                                 comment=cfg.LOG_FILE_DELIMITER_COMMENT_SYMBOL,
                                 parse_dates=True,
                                 date_parser=self.str2date,
                                 index_col=0,
                                 dtype=float,
                                 on_bad_lines="skip")  # TODO: check if ignoring bad lines does not cause any other errors
                datas.append(df)
            except FileNotFoundError:
                pass
            this_date += datetime.timedelta(days=cfg.LOG_FILE_EVERY_DAYS)

        if len(datas) > 0:
            data = pd.concat(datas, sort=False)
            if data.shape[0] > cfg.GRAPH_MAX_POINTS:
                n = int(np.ceil(cfg.GRAPH_MAX_POINTS / data.shape[0]))
                return data.rolling(n).mean().iloc[::n, :]
            else:
                return data
        else:
            return None

    def read_log(self, maxLineLength=120):
        """parses log file on the server"""

        # set timer for next function call (in case there are any excetions below)
        self.timer_readlog = threading.Timer(cfg.READ_LOG_EVERY_SECONDS, self.read_log).start()

        self.log_file = (datetime.datetime.now() - datetime.timedelta(seconds=10)).strftime(cfg.LOG_FILE)

        selected_lines = self.get_first_last_from_file(self.log_file, maxLineLength=maxLineLength, default=b"")
        df = None
        try:
            df = pd.read_csv(io.BytesIO(selected_lines),
                             sep=cfg.LOG_FILE_DELIMITER,
                             comment=cfg.LOG_FILE_DELIMITER_COMMENT_SYMBOL,
                             parse_dates=True,
                             date_parser=self.str2date,
                             skiprows=[1],  # 0 are the column headers, 1 is truncated
                             index_col=0,
                             dtype=float,
                             on_bad_lines="skip")
            log_labels = df.columns.tolist()
            log_labels_nice = list(map(cfg.LOG_NAMES_REPLACEMENT, log_labels))
        except pd.errors.EmptyDataError:
            logging.warning('No data found in log file {}.'.format(self.log_file))
        finally:
            if isinstance(df, pd.DataFrame) and df.shape[0] > 0:
                self.LOG_labels = log_labels
                self.LOG_labels_nice = {l: l_nice for (l, l_nice) in zip(log_labels, log_labels_nice)}
                self.LOG_last_checked = df.tail(1).index.to_pydatetime()[0]

                # make a dictionary out of the dataframe
                self.LOG_data = df.tail(1).to_dict(orient='records')[0]
            else:
                logging.warning('Problem extracting fields and field labels from log file {}.'.format(self.log_file))

        self.check_sanity()
        self.check_user_notifications()
        self.check_measure_requests()
        self.check_logging_file()

    def error_add(self, error, value="", min_count=0):
        """adds error to error list for all users"""
        now = datetime.datetime.now()
        if error not in self.ERRORS_checks.keys():
            self.ERRORS_checks[error] = {}
        for user in cfg.LIST_OF_USERS:
            if user not in self.ERRORS_checks[error].keys():
                self.ERRORS_checks[error][user] = {
                    'sendNext': now + (min_count - 1) * datetime.timedelta(minutes=cfg.READ_LOG_EVERY_SECONDS),
                    'timesSent': 0,
                    'value': value,
                }

        write_log = False
        if error not in self.LOGGING_last_write.keys():
            write_log = True
        elif now - self.LOGGING_last_write[error] > datetime.timedelta(minutes=cfg.LOGGING_ERROR_EVERY_MINUTES):
            write_log = True

        if write_log:
            logging.info('Sanity checks found: {} - {}.'.format(error, value))
            self.LOGGING_last_write[error] = now

    def error_remove(self, error):
        """removes an error from the error list for all users"""
        self.ERRORS_checks.pop(error, None)

    def quiet_hours(self):
        """returns whether we are in quiet hours (as defined in the config section)"""
        now = datetime.datetime.now()
        quiet_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + \
            datetime.timedelta(hours=cfg.QUIET_TIMES_HOURS_START)
        quiet_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + \
            datetime.timedelta(hours=cfg.QUIET_TIMES_HOURS_END)
        if now > quiet_start and now < quiet_end and now.weekday() in cfg.QUIET_TIMES_WEEKDAYS:
            return True
        else:
            return False

    def check_sanity(self):
        """checks whether the logging works and if the pressures are ok."""

        error_checks_old = copy.deepcopy(self.ERRORS_checks)
        now = datetime.datetime.now()

        # index for limits defined in config, higher limits are defined for quiet hours
        i_quiet = 0
        quiet_hours = self.quiet_hours()
        if quiet_hours:
            i_quiet = 1

        # check for warnings that are not active anymore
        errors_off = []
        errors_off_only_quiet = []   # boolean values, same length as errors_off
        errors_unknown = []
        for error in self.ERRORS_checks.keys():
            if error == 'ERROR_log_read':
                if self.LOG_last_checked:
                    if now - self.LOG_last_checked < datetime.timedelta(minutes=cfg.WARNING_NOLOG_MINUTES):
                        errors_off.append(error)
                        errors_off_only_quiet.append(False)
            elif error in cfg.ERROR_COLUMNS_MUSTHAVE.keys():
                e_dict = cfg.ERROR_COLUMNS_MUSTHAVE[error]
                if e_dict['column'] in self.LOG_data:
                    errors_off.append(error)
                    errors_off_only_quiet.append(False)
            elif error in cfg.ERROR_LIMITS_MAX.keys():
                if len(self.LOG_data) > 0:  # otherwise we will get an error for not being able to read the log file
                    e_dict = cfg.ERROR_LIMITS_MAX[error]
                    if e_dict['column'] in self.LOG_data:
                        if self.LOG_data[e_dict['column']] < e_dict['limits'][i_quiet]:
                            errors_off.append(error)
                            if self.LOG_data[e_dict['column']] < e_dict['limits'][0]:
                                errors_off_only_quiet.append(False)
                            else:
                                errors_off_only_quiet.append(True)
            elif error in cfg.ERROR_LOWERTHAN_VALUES.keys():
                c = cfg.ERROR_LOWERTHAN_VALUES[error]['column']
                if c in self.LOG_data:
                    if c in cfg.ERROR_LOWERTHAN:
                        if self.LOG_data[c] > cfg.ERROR_LOWERTHAN[c]:
                            errors_off.append(error)
                            errors_off_only_quiet.append(False)
                    else:
                        if self.LOG_data[c] != cfg.ERROR_LOWERTHAN_VALUES[error]['value']:
                            errors_off.append(error)
                            errors_off_only_quiet.append(False)
            elif error == cfg.ERROR_LOWERTHAN_DEFAULT:
                found_lowerthan = False
                for c in cfg.ERROR_LOWERTHAN:
                    if c in self.LOG_data:
                        if self.LOG_data[c] <= cfg.ERROR_LOWERTHAN[c]:
                            found_lowerthan = True
                if not found_lowerthan:
                    errors_off.append(error)
                    errors_off_only_quiet.append(False)
            elif error == cfg.ERROR_UNKNOWN_VALUES:
                if not any(np.isnan(val) for val in self.LOG_data.values()):
                    errors_off.append(error)
                    errors_off_only_quiet.append(False)
            else:
                errors_unknown.append(error)

        # delete unknown errors, they have probably been removed from the config
        for error in errors_unknown:
            self.error_remove(error)

        # check for new warnings
        if not self.LOG_last_checked:
            self.error_add('ERROR_log_read', self.LOG_last_checked)
        elif now - self.LOG_last_checked > datetime.timedelta(minutes=cfg.WARNING_NOLOG_MINUTES):
            self.error_add('ERROR_log_read', self.LOG_last_checked)

        for error, e_dict in cfg.ERROR_COLUMNS_MUSTHAVE.items():
            if e_dict['column'] not in self.LOG_data:
                self.error_add(error)

        if len(self.LOG_data) > 0:  # otherwise we will get an error for not being able to read the log file
            for error, e_dict in cfg.ERROR_LIMITS_MAX.items():
                if e_dict['column'] in self.LOG_data:
                    if self.LOG_data[e_dict['column']] > e_dict['limits'][i_quiet]:
                        min_count = 0
                        if 'min_count' in e_dict:
                            min_count = e_dict['min_count']
                        self.error_add(error, self.LOG_data[e_dict['column']], min_count=min_count)

            negative_error_default = False
            negative_error_columns = []
            for c in cfg.ERROR_LOWERTHAN:
                if c in self.LOG_data:
                    if (self.LOG_data[c] <= 0):
                        found_error_code = False
                        for error, e_dict in cfg.ERROR_LOWERTHAN_VALUES.items():
                            if e_dict['column'] == c and e_dict['value'] == self.LOG_data[c]:
                                self.error_add(error, self.LOG_data[c])
                                found_error_code = True
                        if not found_error_code:
                            negative_error_columns.append(c)
                            negative_error_default = True
            if negative_error_default:
                columns_nice = [self.LOG_labels_nice[c] for c in negative_error_columns]
                str_columns = ", ".join(columns_nice)
                self.error_add(cfg.ERROR_LOWERTHAN_DEFAULT, str_columns)

            if any(np.isnan(val) for val in self.LOG_data.values()):
                columns_nice = [self.LOG_labels_nice[c] for c in self.LOG_data if np.isnan(self.LOG_data[c])]
                str_columns = ", ".join(columns_nice)
                self.error_add(cfg.ERROR_UNKNOWN_VALUES, str_columns)

        # send warnings
        self.status_error_off(errors_off, errors_off_only_quiet)
        self.status_error()

        # save config if there were any changes
        if self.save_config or self.ERRORS_checks != error_checks_old:
            self.config_save()

    def check_user_notifications(self):
        """checks for notification alarms that have been set up by the user"""
        if not len(self.LOG_data) > 0:
            return False
        for user in cfg.LIST_OF_USERS:
            if 'notifications' not in self.USER_config[user].keys():
                continue
            n_inactivate = []
            for i, n in enumerate(self.USER_config[user]['notifications']):
                if 'active' in n.keys():
                    if not n['active']:
                        continue
                sign = n['comparison']
                if n['column'] in self.LOG_data:
                    if type(self.LOG_data[n['column']]) in [int, float]:
                        if sign * self.LOG_data[n['column']] > sign * n['limit']:
                            self.status_user_notification(None, None, chat_id=user, notification=n)
                            n_inactivate.append(i)
            # inactivate notification
            for i in n_inactivate:  # if we want to delete them, we need to use reversed(n_inactivate)
                self.USER_config[user]['notifications'][i]['active'] = False
            if len(n_inactivate) > 0:
                self.save_config = True

    def check_measure_requests(self):
        """checks if measure requests have received responses"""
        now = datetime.datetime.now()
        for entity, m_dict in self.MEASURE_requests.items():
            if not m_dict['active']:
                continue
            data = self.measure_getlast(entity)
            if data is not None and data.shape[0] > 0:
                date_measured = data.tail(1).index.to_pydatetime()[0]
                if date_measured > m_dict['last_measured']:
                    column_name = cfg.MEASURE_REQUESTS[entity]['column']
                    if column_name in data:
                        value = data.tail(1)[column_name]
                        column_name_nice = cfg.LOG_NAMES_REPLACEMENT(column_name)
                        chat_ids = self.MEASURE_requests[entity]['chat_ids']
                        self.MEASURE_requests[entity]['chat_ids'] = set()
                        self.MEASURE_requests[entity]['active'] = False
                        self.MEASURE_requests[entity]['last_measured'] = date_measured
                        self.MEASURE_requests[entity]['value'] = value
                        str_out = "*{}*: {}  _({})_".format(
                            column_name_nice,
                            self.replace_lowerthan(value).values[0],
                            self.date_format_bot(date_measured)
                        )
                        for chat_id in chat_ids:
                            logging.info("Measure request ({}) by {} successful: {}".format(
                                entity, chat_id,
                                self.replace_lowerthan(value).values[0])
                            )
                            self.measure_send_result(self.bot, None, args=[str_out], chat_id=chat_id)
                        continue
                    else:
                        logging.info(
                            "Measure request for {}: Column {} not found in log file.".format(entity, column_name)
                        )
            if now - m_dict['requested'] > datetime.timedelta(minutes=cfg.MEASURE_REQUESTS[entity]['timeout']):
                self.MEASURE_requests[entity]['active'] = False
                str_out = "Request to measure *{}* timed out.".format(entity)
                for chat_id in m_dict['chat_ids']:
                    logging.info("Measure request ({}) by {} timed out.".format(entity, chat_id))
                    self.measure_send_result(self.bot, None, args=[str_out], chat_id=chat_id)

    def check_logging_file(self, force=False):
        """checks whether the filehandle for logging should be updated"""
        now = datetime.datetime.now()
        fname = now.strftime(cfg.LOGGING_FILENAME)
        if force or fname != self.logging_filename:
            logging.basicConfig(level=logging.INFO)
            os.makedirs(os.path.dirname(fname), exist_ok=True)  # create subdirectory if it doesnt exist
            fileh = logging.FileHandler(fname, 'a')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fileh.setFormatter(formatter)
            log = logging.getLogger()  # root logger
            for hdlr in log.handlers[:]:  # remove all old handlers
                log.removeHandler(hdlr)
            log.addHandler(fileh)
            fileh.setLevel(logging.getLevelName('INFO'))
            self.logging_filename = fname

    def config_save(self):
        """saves config"""
        c = {n: getattr(self, n) for n in self.config_vars}
        pickle.dump(c, open(cfg.USER_CONFIG_FILE, "wb"))

    def config_load(self):
        """saves config"""
        c = pickle.load(open(cfg.USER_CONFIG_FILE, "rb"))
        for key, val in c.items():
            setattr(self, key, val)

    def shutdown(self):
        self.updater.stop()
        self.updater.is_idle = False

    def start_bot(self):
        """starts the telegram bot"""
        self.read_log()
        self.updater.start_polling()

    def stop_bot(self):
        """stops the telegram bot"""
        threading.Thread(target=self.shutdown).start()
        self.timer_readlog.stop()
        logging.info('AFM bot stopped')


if __name__ == "__main__":
    b = LabBot()
    b.start_bot()
    print('Bot started.')
    print('Version: {}'.format(b.get_version()))
