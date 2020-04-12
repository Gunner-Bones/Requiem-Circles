# Requiem-Circles
Sequel to Killbot Circles; this is a separate repository because the file system is much different.

This bot used for integration into the [Pointercrate](https://pointercrate.com/) website, providing many features and tools used for
[Discord](https://discordapp.com/) users who use Pointercrate. This bot is used in the [Official Demons List Public Server](https://discord.gg/M7bDDQf).

## Getting Started

This bot runs off a [Python 3.7](https://www.python.org/downloads/) script with required libraries. The Discord rewrite API requires
at least Python 3.6, and it's always best to use the latest version of Python.

### Prerequisites

Applications required to run and test the bot:
* A Python 3.7 IDE - [Here is one I use](https://www.jetbrains.com/pycharm/). An IDE is not required, but it will immensely help the coding process.
* [Discord](https://discordapp.com/)

### Discord Bot Setup

You'll need to create your own Discord Bot for testing, so you can control where this bot can activate and who can use the bot on Discord. This can all be done on [Discord](https://discordapp.com/) and the [Discord Developers](https://discordapp.com/developers) dashboard. 

If you have not done so already, create a [Discord](https://discordapp.com/) account, and then on Discord click Add a Server. Choose Create, name your server and then create. If you already have a server you want to use, you don't have to create a new one, as long as you are either the owner or have administrative privelages of that server.

To create a Discord Bot, go on the [Discord Developers](https://discordapp.com/developers) dasboard and login with your Discord account. On the Applications tab, click New Application and name your bot. To turn your application to a bot user, go to the application's Bot tab, and click Add Bot. With your newly created bot, underneath the name it'll give you the bot's Client Token. This will be used for the code to run the discord bot. To add your discord bot to your server, go to the bot's OAuth2 tab. For basic permissions, click the 'bot' checkbox, which will generate a link below. In that link's page, choose the server you want to add the bot to, and click Add. If you go back to your Discord server, you should see your bot has joined it.

### Installing

To get a copy of the Requiem Circles code, clone the repository. Download the ZIP of the repository by finding the *Clone or Download* button on the [repository page](https://github.com/Gunner-Bones/Requiem-Circles), and extract the ZIP file. This will include `rc.py`, which is the main bot script, and a lot of TXT files that contain data for the bot to use.

To be able to use this code with your Discord bot, create a TXT file in the same directory as `rc.py` and name it `pass.txt`. In that TXT file, directly paste your Discord bot's Client Token (where to find that is explained in the **Discord Bot Setup** section).

The Discord Rewrite API is required to run the script. [This](https://discordpy.readthedocs.io/en/rewrite/intro.html#installing) outlines how to install the rewrite API for Python 3.

Once you have installed the rewrite, and set your Python IDE to use the version of Python 3 that contains the rewrite, run `rc.py` to run the bot.

### Testing

Once you have the Discord bot set up correctly in Discord and with your files, run `rc.py` to run the bot. If the script does not error, and the bot user in your Discord goes online, then the script is running properly.

## Deployment

To keep the bot running 24/7, you'll need to host it on a server. A cheap method I use for keeping the bot online is running an [Amazon EC2](https://aws.amazon.com/ec2/) server. They offer a free 1-year tier for a basic server, which should be more than enough to run a couple of Discord bots.
Once you have a server set up, you'll need to run the bot in "nohup", which will run the script until you terminate the process.
To create a nohup BASH script in your server, create a .sh file, and set it up like this:
```
#! /bin/bash
nohup python3.7 rc.py &
```
To run the bot in nohup, run the .sh file. To terminate the script, terminate the .sh file's process.
