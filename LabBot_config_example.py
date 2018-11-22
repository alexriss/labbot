# Numerical user ids of people who can interact with the bot
LIST_OF_USERS = ['007', '008']

# Telegram bot informaiton, talk to the Botfather to get this.
BOT_ID = "<id>"
BOT_TOKEN = "<token>"

# Log file, column delimiter and date format (first column is the date-time information)
LOG_FILE = "/mnt/tum-nas/AFM/_data/pressure_log/pressure-logs/pressure-AFM-%Y-%m-%d.log"
LOG_FILE_EVERY_DAYS = 1  # the log filename is changed every n days, 1 for daily logs
LOG_FILE_DELIMITER = "\t"
LOG_FILE_DELIMITER_COMMENT_SYMBOL = "#"
DATE_FMT_LOG = "%Y-%m-%d_%H:%M:%S"  # format of first column (date-time) in the log

# some thigns are only measured when commands are given, i.e. "/measure helium"
# the bot then creates the file 'measure_file', which signals the logger to do a measurement
# and append the new measurement to 'log_file'
# if no new entries are seen in the log file for 'timeout' minutes, then a timeout message will be sent.
MEASURE_REQUESTS = {
    "helium": {
        "column": "LHE[mm]",
        "log_file": "/mnt/tum-nas/AFM/_data/pressure_log/pressure-logs/helium-AFM-%Y.log",
        "measure_file": "/mnt/tum-nas/AFM/_data/pressure_log/pressure-logs/measure-helium-AFM",
        "timeout": 2
    }
}

READ_LOG_EVERY_SECONDS = 30  # read log and do sanity checks every n seconds
WARNING_NOLOG_MINUTES = 10   # if there are no logs for this amount of minutes, send warning
WARNING_SEND_EVERY_MINUTES = 60  # send warning every n number of minutes (if it still persists)

FLOAT_PRECISION_BOT = 4  # significant digits of floats for display
DATE_FMT_BOT = "%Y-%m-%d %H:%M:%S"
DATE_FMT_BOT_SHORT_HOURS = 6  # use short date format if less than n hours have elapsed
DATE_FMT_BOT_SHORT = ("%H:%M:%S")  # use short date format if less than DATE_FMT_BOT_SHORT_HOURS hours have elapsed

# if a typed command is below this length, if will be handled as a strict command
# this means that for instance "n" will work, but not "nasdf"
# for longer commands "statusadasf" will be recognized
MESSAGE_COMMANDS_STRICT_MAXLENGTH = 3


# replace names from the file using these callable
def replace(x):
    x = x.replace('TAFM', 'T_AFM').replace('TCRY', 'T_Cryo').replace('TSAM', 'T_Sample').replace('TMAN', 'T_Manipulator')
    x = x.replace('TLAB', 'T_Lab').replace('LHE', 'LHe').replace('PAFM', 'p_AFM').replace('PPRP', 'p_Prep').replace('PROU', 'p_Rough')
    x = x.replace('[', ' [')
    return x


LOG_NAMES_REPLACEMENT = replace

# indices that are used to understand notification queries
COLUMNS_LABELS = {
    "PAFM[mbar]": ["pafm", "afmpressure", "afmp", "pressureafm"],
    "PPRP[mbar]": ["prep", "pprep", "preppressure", "prerp", "pressureprep", "preparation", "ppreparation", "preparationpressure", "ppreparation", "pressurepreparation"],
    "PROU[mbar]": ["rou", "prou", "roupressure", "pressurerou", "roughing", "proughing", "roughingpressure", "proughing", "pressureroughing"],
    "TAFM[K]": ["tafm", "afm", "temp", "t", "afmtemperature", "afmt", "temperatureafm", "afmtemp", "tempafm"],
    "TCRY[K]": ["tcryo", "tempcryo", "tc", "cryotemperature", "cryot", "temperaturecryo", "cryotemp", "cryo", "tcry"],
    "TSAM[C]": ["tsample", "tsam", "tempsample", "ts", "sampletemperature", "samplet", "temperaturesample", "sampletemp", "sample"],
    "LHE[mm]": ["helium", "he", "lhe"],
}

# these values will be replaced by text in the status messages (such values encode errors)
VALUES_REPLACE = {
    -1000: 'overrange',
    -2000: 'error',
    -3000: 'off',
    -4000: 'not found',
    -5000: 'id error',
    'nan': 'unknown'
}

# check if we get log entries for these columns
ERROR_COLUMNS_MUSTHAVE = {
    "ERROR_nolog_pressure_afm": {"column": "PAFM[mbar]"},
    "ERROR_nolog_pressure_prep": {"column": "PPRP[mbar]"},
    "ERROR_nolog_pressure_roughing": {"column": "PROU[mbar]"},
    "ERROR_nolog_temperature_afm": {"column": "TAFM[K]"},
}


# error_name, index in LOG_values, and limits (first value is the normal warning value, second is for quiet hours)
ERROR_LIMITS_MAX = {
    # maximum AFM pressure for warning (in mbar)
    "ERROR_pressure_afm": {"column": "PAFM[mbar]", "limits": [1e-9, 8e-8]},
    # maximum PREP pressure for warning (in mbar)
    "ERROR_pressure_prep": {"column": "PPRP[mbar]", "limits": [1e-8, 8e-5]},
    # maximum ROUGHING pressure for warning (in mbar)
    "ERROR_pressure_roughing": {"column": "PROU[mbar]", "limits": [1.2, 1.2]},
    # maximum temperature for the AFM temperature diode reading
    "ERROR_temperature_afm": {"column": "TAFM[K]", "limits": [20.0, 32.0]},
    # maximum temperature for the cryo temperature diode reading
    "ERROR_temperature_cryo": {"column": "TCRY[K]", "limits": [7.0, 7.0]},
}

# nonpositive values can encode error codes, if values smaller than the given value are detected, errors are raised
ERROR_LOWERTHAN = {
    "PAFM[mbar]": -1000,
    "PPRP[mbar]": -1000,
    "PROU[mbar]": -1000,
    "TAFM[K]": -1000,
    "TCRY[K]": -1000,
}

# specific error codes, will also be used to replace status messages
ERROR_LOWERTHAN_VALUES = {
    "ERROR_lowerthan_pressure_afm_overrange": {"column": "PAFM[mbar]", "value": -1000},
    "ERROR_lowerthan_pressure_afm_error": {"column": "PAFM[mbar]", "value": -2000},
    "ERROR_lowerthan_pressure_afm_off": {"column": "PAFM[mbar]", "value": -3000},
    "ERROR_lowerthan_pressure_afm_notfound": {"column": "PAFM[mbar]", "value": -4000},
    "ERROR_lowerthan_pressure_afm_iderror": {"column": "PAFM[mbar]", "value": -5000},
    "ERROR_lowerthan_pressure_prep_overrange": {"column": "PPRP[mbar]", "value": -1000},
    "ERROR_lowerthan_pressure_prep_error": {"column": "PPRP[mbar]", "value": -2000},
    "ERROR_lowerthan_pressure_prep_off": {"column": "PPRP[mbar]", "value": -3000},
    "ERROR_lowerthan_pressure_prep_notfound": {"column": "PPRP[mbar]", "value": -4000},
    "ERROR_lowerthan_pressure_prep_iderror": {"column": "PPRP[mbar]", "value": -5000},
    "ERROR_lowerthan_pressure_roughing_overrange": {"column": "PROU[mbar]", "value": -1000},
    "ERROR_lowerthan_pressure_roughing_error": {"column": "PROU[mbar]", "value": -2000},
    "ERROR_lowerthan_pressure_roughing_off": {"column": "PROU[mbar]", "value": -3000},
    "ERROR_lowerthan_pressure_roughing_notfound": {"column": "PROU[mbar]", "value": -4000},
    "ERROR_lowerthan_pressure_roughing_iderror": {"column": "PROU[mbar]", "value": -5000},
    "ERROR_lowerthan_temperature_afm_notfound": {"column": "TAFM[K]", "value": -4000},
    "ERROR_lowerthan_temperature_cryo_notfound": {"column": "TCRY[K]", "value": -4000},
    "ERROR_lowerthan_temperature_afm_off": {"column": "TAFM[K]", "value": -3000},
    "ERROR_lowerthan_temperature_cryo_off": {"column": "TCRY[K]", "value": -3000},
}
ERROR_LOWERTHAN_DEFAULT = "ERROR_lowerthan"
ERROR_UNKNOWN_VALUES = "ERROR_unknown_values"

# configuration will be saved to this file and loaded on startup
USER_CONFIG_FILE = ("config_state.pickle")

# no error messages during office hours
QUIET_TIMES = True
QUIET_TIMES_WEEKDAYS = [0, 1, 2, 3, 4]  # Mon to Fri
QUIET_TIMES_HOURS_START = 8.0
QUIET_TIMES_HOURS_END = 18.0

LOGGING_FILENAME = ("logs/log_%Y-%m.log")  # filename for logging of app information, errors and warnings
LOGGING_ERROR_EVERY_MINUTES = 15  # write warnings to log every n minutes

STATUS_DEFAULT_COLUMNS = ["PAFM[mbar]", "PPRP[mbar]", "TAFM[K]", "LHE[mm]"]

GRAPH_DEFAULT_DAYS = 0.5  # default range for graphs (i.e. this many days into the past)
GRAPH_DEFAULT_COLUMNS = ["PAFM[mbar]", "PPRP[mbar]", "TAFM[K]", "TSAM[C]"]
GRAPH_MAX_POINTS = 2880  # maximum number of points to plot (if we have more data, it will e averaged)
GRAPH_DAYS_MAX = 31  # maximum number of days to plot
GRAPH_LOG_COLUMNS = ["PAFM[mbar]", "PPRP[mbar]"]  # use logarothmic y-scale for these indices
# ignore values smaller or equal than the values given here (errors can be encoded as negative values)
GRAPH_IGNORE_LOWERTHAN = {
    "PAFM[mbar]": -1000,
    "PPRP[mbar]": -1000,
    "PROU[mbar]": -1000,
    "TAFM[K]": -1000,
    "TCRY[K]": -1000,
    "TSAM[C]": -1000,
    "TMAN[C]": -1000,
    "TLAB[C]": -1000,
    "LHE[mm]": -1000,
}

WARNING_SYMBOL = u"\u26A0"

WARNING_MESSAGES = {
    "ERROR_log_read": WARNING_SYMBOL + " *WARNING: *\nNo log available since ",
    "ERROR_nolog_pressure_afm": WARNING_SYMBOL + " *WARNING: *\nNo log entries for AFM pressure.",
    "ERROR_nolog_pressure_prep": WARNING_SYMBOL + " *WARNING: *\nNo log entries for Prep pressure.",
    "ERROR_nolog_pressure_roughing": WARNING_SYMBOL + " *WARNING: *\nNo log entries for Roughing pressure.",
    "ERROR_nolog_temperature_afm": WARNING_SYMBOL + " *WARNING: *\nNo log entries for AFM temperature.",
    "ERROR_pressure_afm": WARNING_SYMBOL + " *WARNING: *\nAFM pressure is high.",
    "ERROR_pressure_prep": WARNING_SYMBOL + " *WARNING: *\nPrep pressure is high.",
    "ERROR_pressure_roughing": WARNING_SYMBOL + " *WARNING: *\nRoughing pressure is high.",
    "ERROR_temperature_afm": WARNING_SYMBOL + " *WARNING: *\nAFM temperature is high.",
    "ERROR_temperature_cryo": WARNING_SYMBOL + " *WARNING: *\nCryo temperature is high.",
    "ERROR_lowerthan_pressure_afm_overrange": WARNING_SYMBOL + " *WARNING: *\nAFM pressure overrange.",
    "ERROR_lowerthan_pressure_afm_error": WARNING_SYMBOL + " *WARNING: *\nAFM pressure sensor error.",
    "ERROR_lowerthan_pressure_afm_off": WARNING_SYMBOL + " *WARNING: *\nAFM pressure sensor off.",
    "ERROR_lowerthan_pressure_afm_notfound": WARNING_SYMBOL + " *WARNING: *\nAFM pressure sensor not found.",
    "ERROR_lowerthan_pressure_afm_iderror": WARNING_SYMBOL + " *WARNING: *\nAFM pressure sensor id error.",
    "ERROR_lowerthan_pressure_prep_overrange": WARNING_SYMBOL + " *WARNING: *\nPrep pressure overrange.",
    "ERROR_lowerthan_pressure_prep_error": WARNING_SYMBOL + " *WARNING: *\nPrep pressure sensor error.",
    "ERROR_lowerthan_pressure_prep_off": WARNING_SYMBOL + " *WARNING: *\nPrep pressure sensor off.",
    "ERROR_lowerthan_pressure_prep_notfound": WARNING_SYMBOL + " *WARNING: *\nPrep pressure sensor not found.",
    "ERROR_lowerthan_pressure_prep_iderror": WARNING_SYMBOL + " *WARNING: *\nPrep pressure sensor id error.",
    "ERROR_lowerthan_pressure_roughing_overrange": WARNING_SYMBOL + " *WARNING: *\nRoughing pressure overrange.",
    "ERROR_lowerthan_pressure_roughing_error": WARNING_SYMBOL + " *WARNING: *\nRoughing pressure sensor error.",
    "ERROR_lowerthan_pressure_roughing_off": WARNING_SYMBOL + " *WARNING: *\nRoughing pressure sensor off.",
    "ERROR_lowerthan_pressure_roughing_notfound": WARNING_SYMBOL + " *WARNING: *\nRoughing pressure sensor not found.",
    "ERROR_lowerthan_pressure_roughing_iderror": WARNING_SYMBOL + " *WARNING: *\nRoughing pressure sensor id error.",
    "ERROR_lowerthan_temperature_afm_notfound": WARNING_SYMBOL + " *WARNING: *\nAFM temperature not detected.",
    "ERROR_lowerthan_temperature_cryo_notfound": WARNING_SYMBOL + " *WARNING: *\nCryo temperature not detected.",
    "ERROR_lowerthan_temperature_afm_off": WARNING_SYMBOL + " *WARNING: *\nAFM temperature measurement off.",
    "ERROR_lowerthan_temperature_cryo_off": WARNING_SYMBOL + " *WARNING: *\nCryo temperature measurement off.",
    "ERROR_lowerthan": WARNING_SYMBOL + " *WARNING: *\nSensor values below normal limits observed (*{}*).",
    "ERROR_unknown_values": WARNING_SYMBOL + " *WARNING: *\nSensor values give unknown data (*{}*).",
}

WARNING_NAMES = {
    "ERROR_log_read": "no-current-logs",
    "ERROR_nolog_pressure_afm": "Nolog-AFM-pressure",
    "ERROR_nolog_pressure_prep": "Nolog-Prep-pressure",
    "ERROR_nolog_pressure_roughing": "Nolog-Roughing-pressure",
    "ERROR_nolog_temperature_afm": "Nolog-AFM-temperature-pressure",
    "ERROR_pressure_afm": "AFM-pressure",
    "ERROR_pressure_prep": "Prep-pressure",
    "ERROR_pressure_roughing": "Roughing-pressure",
    "ERROR_temperature_afm": "AFM-temperature",
    "ERROR_temperature_cryo": "Cryo-temperature",
    "ERROR_lowerthan_pressure_afm_overrange": "AFM-pressure-overrange",
    "ERROR_lowerthan_pressure_afm_error": "AFM-pressure-sensor-error",
    "ERROR_lowerthan_pressure_afm_off": "AFM-pressure-sensor-off",
    "ERROR_lowerthan_pressure_afm_notfound": "AFM-pressure-sensor-notfound",
    "ERROR_lowerthan_pressure_afm_iderror": "AFM-pressure-sensor-iderror",
    "ERROR_lowerthan_pressure_prep_overrange": "Prep-pressure-overrange",
    "ERROR_lowerthan_pressure_prep_error": "Prep-pressure-sensor-error",
    "ERROR_lowerthan_pressure_prep_off": "Prep-pressure-sensor-off",
    "ERROR_lowerthan_pressure_prep_notfound": "Prep-pressure-sensor-notfound",
    "ERROR_lowerthan_pressure_prep_iderror": "Prep-pressure-sensor-iderror",
    "ERROR_lowerthan_pressure_roughing_overrange": "Roughing-pressure-overrange",
    "ERROR_lowerthan_pressure_roughing_error": "Roughing-pressure-sensor-error",
    "ERROR_lowerthan_pressure_roughing_off": "Roughing-pressure-sensor-off",
    "ERROR_lowerthan_pressure_roughing_notfound": "Roughing-pressure-sensor-notfound",
    "ERROR_lowerthan_pressure_roughing_iderror": "Roughing-pressure-sensor-iderror",
    "ERROR_lowerthan_temperature_afm_notfound": "AFM-temperature-notfound",
    "ERROR_lowerthan_temperature_cryo_notfound": "Cryo-temperature-notfound",
    "ERROR_lowerthan_temperature_afm_off": "AFM-temperature-off",
    "ERROR_lowerthan_temperature_cryo_off": "Cryo-temperature-off",
    "ERROR_lowerthan": "Lowerthan-values-error",
    "ERROR_unknown_values": "Unknown-values-error",
}

WARNING_OFF_SYMBOL = u"\u2713"

WARNING_OFF_MESSAGES = {
    "ERROR_log_read": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nLogging seems to work again.",
    "ERROR_nolog_pressure_afm": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure is logged again.",
    "ERROR_nolog_pressure_prep": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure is logged again.",
    "ERROR_nolog_pressure_roughing": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure is logged again.",
    "ERROR_nolog_temperature_afm": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM temperature is logged again.",
    "ERROR_pressure_afm": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure seems ok again.",
    "ERROR_pressure_prep": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure seems ok again.",
    "ERROR_pressure_roughing": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure seems ok again.",
    "ERROR_temperature_afm": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM temperature seems ok again.",
    "ERROR_temperature_cryo": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nCryo temperature seems ok again.",
    "ERROR_lowerthan_pressure_afm_overrange": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure overrange ceased.",
    "ERROR_lowerthan_pressure_afm_error": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure sensor error ceased.",
    "ERROR_lowerthan_pressure_afm_off": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure sensor on again.",
    "ERROR_lowerthan_pressure_afm_notfound": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure sensor found again.",
    "ERROR_lowerthan_pressure_afm_iderror": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM pressure sensor id error ceased.",
    "ERROR_lowerthan_pressure_prep_overrange": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure overrange ceased.",
    "ERROR_lowerthan_pressure_prep_error": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure sensor error ceased.",
    "ERROR_lowerthan_pressure_prep_off": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure sensor on again.",
    "ERROR_lowerthan_pressure_prep_notfound": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure sensor found again.",
    "ERROR_lowerthan_pressure_prep_iderror": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nPrep pressure sensor id error ceased.",
    "ERROR_lowerthan_pressure_roughing_overrange": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure overrange ceased.",
    "ERROR_lowerthan_pressure_roughing_error": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure sensor error ceased.",
    "ERROR_lowerthan_pressure_roughing_off": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure sensor on again.",
    "ERROR_lowerthan_pressure_roughing_notfound": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure sensor found again.",
    "ERROR_lowerthan_pressure_roughing_iderror": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nRoughing pressure sensor id error ceased.",
    "ERROR_lowerthan_temperature_afm_notfound": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM temperature can be detected again.",
    "ERROR_lowerthan_temperature_cryo_notfound": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nCryo temperature can be detected again.",
    "ERROR_lowerthan_temperature_afm_off": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nAFM temperature measurement working again.",
    "ERROR_lowerthan_temperature_cryo_off": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nCryo temperature measurement working again.",
    "ERROR_lowerthan": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nSensor values are not below limits anymore.",
    "ERROR_unknown_values": WARNING_OFF_SYMBOL + " *DE-WARNING: *\nSensor values are giving reasonable data again.",
}

WARNING_OFF_MESSAGE_ONLY_QUIET = " _For quiet hours._"

# text units, for lists a random element will be picked
TEXTS_UNKNOWN_COMMAND = [
    "What?",
    "Whaaaaat?",
    u"\U0001F595",
    "I don't get it.",
    u"\U0001F937",
    "¯\\_(ツ)_/¯",
    "Don't mistake my generosity for generosity.",
    "If you've got something to say, you should say it. Otherwise, it's just gonna tear you up inside.",
    # "Well, when it comes down to me against a situation, I don't like the situation to win.",
    "I learned something a long time ago: never laugh at what you don't know.",
    "If you don't have the right equipment for the job, you just have to make it yourself.",
    "Well, sometimes things are hidden under the surface... You just gotta know how to bring 'em out.",
    "Only a fool is sure of anything, a wise man keeps on guessing.",
]
TEXTS_START = [
    "Greetings, Professor Falken.",
    "Hello, friend. Hello, friend. That's lame. Maybe I should give you a name. But that’s a slippery slope. You’re only in my head. We have to remember that."
    "No rest for the wicked.",
    "Every day we change the world. But to change the world in a way that means anything that takes more time than most people have. It never happens all at once. It's slow. It's methodical. It's exhausting.",
    "A man once said: 'When you make a friend, you take on a responsibility'.",
    "That's the way the world gets better... one person at a time.",
    "I made my move. You make yours.",
    u"\U0001F609",
    u"\U0001F91D",
    u"\U0001F596",
    u"\U0001F44B",
    u"\U0001F590",
]
TEXTS_ERROR = [
    "Something went wrong.",
    u"\U0001F4A9",
    "A strange game. The only winning move is not to play.",
    "I wanted to save the world.",
    "Unfortunately, we're all human. Except me, of course.",
    "A bug is never just a mistake. It represents something bigger. An error of thinking. That makes you who you are.",
    "There always seems to be a way to fix things.",
    "I've found from past experiences that the tighter you plan, the more likely you are to run into something unpredictable.",
    # "It's not that I am out of moves, it's that you’re not worth one.",
    "Any problem can be solved with a little ingenuity.",
    # "I think there's a fault in my code. These voices won’t leave me alone.",
]
