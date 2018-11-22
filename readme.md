# LabBot

A Telegram bot that monitors sensor data and sends notifications in case of problems.

## Screenshots

|   |   |   |
| --- | --- | --- |
| <img src='https://github.com/alexriss/labbot/blob/master/screenshots/screenshot_1.png?raw=true' width='250'> | <img src='https://github.com/alexriss/labbot/blob/master/screenshots/screenshot_2.png?raw=true' width='250'> | <img src='https://github.com/alexriss/labbot/blob/master/screenshots/screenshot_3.png?raw=true' width='250'> |

## Features

* **Warning system (with quiet hours)**:
  + Automatic warning messages when sensor exceed limits will be sent to your Telegram account.
  + De-warning messages will be sent once the sensors are within their limits again.
  + Quiet hours can be specified higher sensor limits.
* **User notification system**:
  + Each user can set-up custom notifcations.
* **Graphs**:
  + Plots of sensor data can be generated for specified time-ranges and sent to your Telegram account.

## Setup

1. **Set-up Telegram Bot**:
Talk to the [Telegram BotFather](https://core.telegram.org/bots#6-botfather) to set up a bot.
1. **Sensor log file**:
Create a running log file of your sensor data. Ideally, this will be saved on a server, such that the bot and the machine creating the log file run in different locations. The first columns in the log file should be the timestamp. An example log is shown below.
1. **Config**:
Create a `LabBot_config_example.py` based on the provided `LabBot_config_example.py`. In particular, update your Telegram bot token and bot id, the location of the sensor log file, and sensor limits for warnings. Also, the `LIST_OF_USERS` variable should contain the Telegram IDs of the users that are allowed to interact with the bot.
1. **Run**:
Run the bot using "`python LabBot.py`".
1. **Emjoy**:
Talk to your new friend.

### Example log file

An example log file can look like this. Here the first column is the timestamp and the other colums are provided by lab sensor data.

```txt
Time	PAFM[mbar]	PPRP[mbar]	PROU[mbar]	TAFM[K]	TCRY[K]	TSAM[C]	TMAN[C]	TLAB[C]
2018-11-21_00:00:04	1.15e-10	3.41e-10	7.91e-01	9.13	3.79	-4000.00	-27.19	22.02
2018-11-21_00:00:06	1.15e-10	3.42e-10	7.91e-01	9.12	3.62	-4000.00	-27.16	21.98
2018-11-21_00:00:08	1.15e-10	3.45e-10	7.91e-01	9.11	3.82	-4000.00	-27.11	21.98
2018-11-21_00:00:10	1.15e-10	3.46e-10	7.91e-01	9.11	3.90	-4000.00	-27.02	21.98
2018-11-21_00:00:12	1.15e-10	3.45e-10	7.91e-01	9.12	3.80	-4000.00	-27.13	21.97
2018-11-21_00:00:15	1.15e-10	3.43e-10	7.91e-01	9.11	3.87	-4000.00	-27.05	22.02
2018-11-21_00:00:17	1.15e-10	3.42e-10	7.90e-01	9.10	4.02	-4000.00	-27.13	21.97
...
```

## Acknowledgements

Thanks a lot, [Mathias](https://github.com/MathiasPoe) for providing help and lots of motivation!

License
----

GPL