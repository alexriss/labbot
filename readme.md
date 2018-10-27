# LabBot

A Telegram bot that monitors sensor data and sends notifications in case of problems.

## Screenshots

*will be provided shortly.*

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
Time	AFM[mbar]	PREP[mbar]	ROU[mbar]	TAFM[K]	TCRY[K]
2018-10-26_00:00:02	9.36e-11	2.57e-10	7.91e-01	7.31
2018-10-26_00:00:05	9.33e-11	2.57e-10	7.91e-01	7.31
2018-10-26_00:00:07	9.31e-11	2.56e-10	7.91e-01	7.31
...
```

## Acknowledgements

Thanks a lot, [Mathias](https://github.com/MathiasPoe) for providing help and lots of motivation!

License
----

GPL