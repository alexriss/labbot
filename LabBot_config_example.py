# Numerical user ids of people who can interact with the bot
LIST_OF_USERS = [007, 008]

# Telegram bot informaiton, talk to the Botfather to get this.
BOT_ID = "<id>"
BOT_TOKEN = "<token>"

# Log file, column delimiter and date format (first column is the date-time information)
LOG_FILE = "/network/logs/log-%Y-%m-%d.log"
LOG_FILE_EVERY_DAYS = 1  # the log filename is changed every n days, 1 for daily logs
LOG_FILE_DELIMITER = "\t"
LOG_FILE_DELIMITER_COMMENT_SYMBOL = "#"
DATE_FMT_LOG = "%Y-%m-%d_%H:%M:%S"  # format of first column (date-time) in the log

READ_LOG_EVERY_SECONDS = 60  # read log and do sanity checks every n seconds
WARNING_NOLOG_MINUTES = (5)   # if there are no logs for this amount of minutes, send warning
WARNING_SEND_EVERY_MINUTES = (30)  # send warning every n number of minutes (if it still persists)

FLOAT_PRECISION_BOT = 4  # significant digits of floats for display
DATE_FMT_BOT = "%Y-%m-%d %H:%M:%S"
DATE_FMT_BOT_SHORT_HOURS = 6  # use short date format if less than n hours have elapsed
DATE_FMT_BOT_SHORT = ("%H:%M:%S")  # use short date format if less than DATE_FMT_BOT_SHORT_HOURS hours have elapsed

# if a typed command is below this length, if will be handled as a strict command
# this means that "n" will work, but not "nasdf"
# for longer commands "statusadasf" will be recognized
MESSAGE_COMMANDS_STRICT_MAXLENGTH = 3


# replace names from the file using these callable
def replace(x):
    return x.replace('TAFM', 'T_AFM').replace('TCRY', 'T_Cryo').replace('[', ' [')


LOG_NAMES_REPLACEMENT = replace

# indices that are used to understand notification queries
INDICES_LABELS = {
    0: ["afm", "pafm", "afmpressure", "afmp", "pressureafm"],
    1: [
        "prep",
        "pprep",
        "preppressure",
        "prerp",
        "pressureprep",
        "preparation",
        "ppreparation",
        "preparationpressure",
        "ppreparation",
        "pressurepreparation",
    ],
    2: [
        "rou",
        "prou",
        "roupressure",
        "pressurerou",
        "roughing",
        "proughing",
        "roughingpressure",
        "proughing",
        "pressureroughing",
    ],
    3: [
        "temp",
        "t",
        "tafm",
        "afmtemperature",
        "afmt",
        "temperatureafm",
        "afmtemp",
        "tempafm",
    ],
    4: [
        "tempcryo",
        "tc",
        "tcryo",
        "cryotemperature",
        "cryot",
        "temperaturecryo",
        "cryotemp",
        "cryo",
    ],
}

# error_name, index in LOG_values, and limits (first value is the normal warning value, second is for quiet hours)
ERROR_LIMITS_MAX = {
    "ERROR_pressure_afm": {
        "index": 0,
        "limits": [1e-9, 8e-8],
    },  # maximum AFM pressure for warning (in mbar)
    "ERROR_pressure_prep": {
        "index": 1,
        "limits": [1e-8, 8e-5],
    },  # maximum PREP pressure for warning (in mbar)
    "ERROR_pressure_roughing": {
        "index": 2,
        "limits": [1.2, 1.2],
    },  # maximum ROUGHING pressure for warning (in mbar)
    # maximum temperature for the AFM temperature diode reading
    "ERROR_temperature_afm": {"index": 3, "limits": [18.0, 20.0]},
    "ERROR_temperature_cryo": {"index": 4, "limits": [5.0, 6.0]},
}

# nonpositive values can encode error codes
ERROR_NONPOSITIVE_INDICES = [0, 1, 2, 3, 4]

# specific error codes
ERROR_NONPOSITIVE_VALUES = {
    "ERROR_negative_pressure_afm_overrange": {"index": 0, "value": -1, "value_replace": "overrange"},
    "ERROR_negative_pressure_afm_error": {"index": 0, "value": -2, "value_replace": "error"},
    "ERROR_negative_pressure_afm_off": {"index": 0, "value": -3, "value_replace": "off"},
    "ERROR_negative_pressure_afm_notfound": {"index": 0, "value": -4, "value_replace": "not found"},
    "ERROR_negative_pressure_afm_iderror": {"index": 0, "value": -5, "value_replace": "id error"},
    "ERROR_negative_pressure_prep_overrange": {"index": 1, "value": -1, "value_replace": "overrange"},
    "ERROR_negative_pressure_prep_error": {"index": 1, "value": -2, "value_replace": "error"},
    "ERROR_negative_pressure_prep_off": {"index": 1, "value": -3, "value_replace": "off"},
    "ERROR_negative_pressure_prep_notfound": {"index": 1, "value": -4, "value_replace": "not found"},
    "ERROR_negative_pressure_prep_iderror": {"index": 1, "value": -5, "value_replace": "id error"},
    "ERROR_negative_pressure_roughing_overrange": {"index": 2, "value": -1, "value_replace": "overrange"},
    "ERROR_negative_pressure_roughing_error": {"index": 2, "value": -2, "value_replace": "error"},
    "ERROR_negative_pressure_roughing_off": {"index": 2, "value": -3, "value_replace": "off"},
    "ERROR_negative_pressure_roughing_notfound": {"index": 2, "value": -4, "value_replace": "not found"},
    "ERROR_negative_pressure_roughing_iderror": {"index": 2, "value": -5, "value_replace": "id error"},
    "ERROR_negative_temperature_afm_notfound": {"index": 3, "value": -4, "value_replace": "not found"},
    "ERROR_negative_temperature_cryo_notfound": {"index": 4, "value": -4, "value_replace": "not found"},
}
ERROR_NONPOSITIVE_DEFAULT = "ERROR_negative"

# configuration will be saved to this file and loaded on startup
USER_CONFIG_FILE = ("config_state.pickle")


# no error messages during office hours
QUIET_TIMES = True
QUIET_TIMES_WEEKDAYS = [0, 1, 2, 3, 4]  # Mon to Fri
QUIET_TIMES_HOURS_START = 8.0
QUIET_TIMES_HOURS_END = 18.0

LOGGING_FILENAME = (
    "logs/log_%Y-%m.log"
)  # filename for logging of app information, errors and warnings
LOGGING_ERROR_EVERY_MINUTES = 15  # write warnings to log every n minutes

GRAPH_DEFAULT_DAYS = 0.5  # default range for graphs (i.e. this many days into the past)
GRAPH_EVERY_NTH_LINE = (
    30
)  # use every n-th line in the log file for plotting (this is for 1 day, it will be automatically adjusted for different ranges)
GRAPH_EVERY_NTH_LINE_MAX = (
    1000
)  # maximum number for GRAPH_EVERY_NTH_LINE after auto-adjustment
GRAPH_DAYS_MAX = 31  # maximum number of days to plot
GRAPH_LOG_INDICES = [0, 1]  # use logarothmic y-scale for these indices
# ignore negative values for these indices (errors can be encoded as negative values)
GRAPH_IGNORE_NONPOSITIVE_INDICES = [0, 1, 2, 3, 4, 5]

WARNING_MESSAGES = {
    "ERROR_log_read": u"\u26A0" + " *WARNING: *\nNo log available since ",
    "ERROR_pressure_afm": u"\u26A0" + " *WARNING: *\nAFM pressure is high.",
    "ERROR_pressure_prep": u"\u26A0" + " *WARNING: *\nPrep pressure is high.",
    "ERROR_pressure_roughing": u"\u26A0" + " *WARNING: *\nRoughing pressure is high.",
    "ERROR_temperature_afm": u"\u26A0" + " *WARNING: *\nAFM temperature is high.",
    "ERROR_temperature_cryo": u"\u26A0" + " *WARNING: *\nCryo temperature is high.",
    "ERROR_negative_pressure_afm_overrange": u"\u26A0" + " *WARNING: *\nAFM pressure overrange.",
    "ERROR_negative_pressure_afm_error": u"\u26A0" + " *WARNING: *\nAFM pressure sensor error.",
    "ERROR_negative_pressure_afm_off": u"\u26A0" + " *WARNING: *\nAFM pressure sensor off.",
    "ERROR_negative_pressure_afm_notfound": u"\u26A0" + " *WARNING: *\nAFM pressure sensor not found.",
    "ERROR_negative_pressure_afm_iderror": u"\u26A0" + " *WARNING: *\nAFM pressure sensor id error.",
    "ERROR_negative_pressure_prep_overrange": u"\u26A0" + " *WARNING: *\nPrep pressure overrange.",
    "ERROR_negative_pressure_prep_error": u"\u26A0" + " *WARNING: *\nPrep pressure sensor error.",
    "ERROR_negative_pressure_prep_off": u"\u26A0" + " *WARNING: *\nPrep pressure sensor off.",
    "ERROR_negative_pressure_prep_notfound": u"\u26A0" + " *WARNING: *\nPrep pressure sensor not found.",
    "ERROR_negative_pressure_prep_iderror": u"\u26A0" + " *WARNING: *\nPrep pressure sensor id error.",
    "ERROR_negative_pressure_roughing_overrange": u"\u26A0" + " *WARNING: *\nRoughing pressure overrange.",
    "ERROR_negative_pressure_roughing_error": u"\u26A0" + " *WARNING: *\nRoughing pressure sensor error.",
    "ERROR_negative_pressure_roughing_off": u"\u26A0" + " *WARNING: *\nRoughing pressure sensor off.",
    "ERROR_negative_pressure_roughing_notfound": u"\u26A0" + " *WARNING: *\nRoughing pressure sensor not found.",
    "ERROR_negative_pressure_roughing_iderror": u"\u26A0" + " *WARNING: *\nRoughing pressure sensor id error.",
    "ERROR_negative_temperature_afm_notfound": u"\u26A0" + " *WARNING: *\nAFM temperature not detected.",
    "ERROR_negative_temperature_cryo_notfound": u"\u26A0" + " *WARNING: *\nCryo temperature not detected.",
    "ERROR_negative": u"\u26A0" + " *WARNING: *\nNegative sensor values observed ({}).",
}

WARNING_NAMES = {
    "ERROR_log_read": "no-current-logs",
    "ERROR_pressure_afm": "AFM-pressure",
    "ERROR_pressure_prep": "Prep-pressure",
    "ERROR_pressure_roughing": "Roughing-pressure",
    "ERROR_temperature_afm": "AFM-temperature",
    "ERROR_temperature_cryo": "Cryo-temperature",
    "ERROR_negative_pressure_afm_overrange": "AFM-pressure-overrange",
    "ERROR_negative_pressure_afm_error": "AFM-pressure-sensor-error",
    "ERROR_negative_pressure_afm_off": "AFM-pressure-sensor-off",
    "ERROR_negative_pressure_afm_notfound": "AFM-pressure-sensor-notfound",
    "ERROR_negative_pressure_afm_iderror": "AFM-pressure-sensor-iderror",
    "ERROR_negative_pressure_prep_overrange": "Prep-pressure-overrange",
    "ERROR_negative_pressure_prep_error": "Prep-pressure-sensor-error",
    "ERROR_negative_pressure_prep_off": "Prep-pressure-sensor-off",
    "ERROR_negative_pressure_prep_notfound": "Prep-pressure-sensor-notfound",
    "ERROR_negative_pressure_prep_iderror": "Prep-pressure-sensor-iderror",
    "ERROR_negative_pressure_roughing_overrange": "Roughing-pressure-overrange",
    "ERROR_negative_pressure_roughing_error": "Roughing-pressure-sensor-error",
    "ERROR_negative_pressure_roughing_off": "Roughing-pressure-sensor-off",
    "ERROR_negative_pressure_roughing_notfound": "Roughing-pressure-sensor-notfound",
    "ERROR_negative_pressure_roughing_iderror": "Roughing-pressure-sensor-iderror",
    "ERROR_negative_temperature_afm_notfound": "AFM-temperature-notfound",
    "ERROR_negative_temperature_cryo_notfound": "Cryo-temperature-notfound",
    "ERROR_negative": "Negative-values-error",
}

WARNING_OFF_MESSAGES = {
    "ERROR_log_read": u"\u2713" + " *DE-WARNING: *\nLogging seems to work again.",
    "ERROR_pressure_afm": u"\u2713" + " *DE-WARNING: *\nAFM pressure seems ok again.",
    "ERROR_pressure_prep": u"\u2713" + " *DE-WARNING: *\nPrep pressure seems ok again.",
    "ERROR_pressure_roughing": u"\u2713" + " *DE-WARNING: *\nRoughing pressure seems ok again.",
    "ERROR_temperature_afm": u"\u2713" + " *DE-WARNING: *\nAFM temperature seems ok again.",
    "ERROR_temperature_cryo": u"\u2713" + " *DE-WARNING: *\nCryo temperature seems ok again.",
    "ERROR_negative_pressure_afm_overrange": u"\u2713" + " *DE-WARNING: *\nAFM pressure overrange ceased.",
    "ERROR_negative_pressure_afm_error": u"\u2713" + " *DE-WARNING: *\nAFM pressure sensor error ceased.",
    "ERROR_negative_pressure_afm_off": u"\u2713" + " *DE-WARNING: *\nAFM pressure sensor on again.",
    "ERROR_negative_pressure_afm_notfound": u"\u2713" + " *DE-WARNING: *\nAFM pressure sensor found again.",
    "ERROR_negative_pressure_afm_iderror": u"\u2713" + " *DE-WARNING: *\nAFM pressure sensor id error ceased.",
    "ERROR_negative_pressure_prep_overrange": u"\u2713" + " *DE-WARNING: *\nPrep pressure overrange ceased.",
    "ERROR_negative_pressure_prep_error": u"\u2713" + " *DE-WARNING: *\nPrep pressure sensor error ceased.",
    "ERROR_negative_pressure_prep_off": u"\u2713" + " *DE-WARNING: *\nPrep pressure sensor on again.",
    "ERROR_negative_pressure_prep_notfound": u"\u2713" + " *DE-WARNING: *\nPrep pressure sensor found again.",
    "ERROR_negative_pressure_prep_iderror": u"\u2713" + " *DE-WARNING: *\nPrep pressure sensor id error ceased.",
    "ERROR_negative_pressure_roughing_overrange": u"\u2713" + " *DE-WARNING: *\nRoughing pressure overrange ceased.",
    "ERROR_negative_pressure_roughing_error": u"\u2713" + " *DE-WARNING: *\nRoughing pressure sensor error ceased.",
    "ERROR_negative_pressure_roughing_off": u"\u2713" + " *DE-WARNING: *\nRoughing pressure sensor on again.",
    "ERROR_negative_pressure_roughing_notfound": u"\u2713" + " *DE-WARNING: *\nRoughing pressure sensor found again.",
    "ERROR_negative_pressure_roughing_iderror": u"\u2713" + " *DE-WARNING: *\nRoughing pressure sensor id error ceased.",
    "ERROR_negative_temperature_afm_notfound": u"\u2713" + " *DE-WARNING: *\nAFM temperature can be detected again.",
    "ERROR_negative_temperature_cryo_notfound": u"\u2713" + " *DE-WARNING: *\nCryo temperature can be detected again.",
    "ERROR_negative": u"\u2713" + " *DE-WARNING: *\nSensor values are positive again.",
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
