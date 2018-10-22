# Newsletter2Go list management tool

This is a simple commandline client for the Newsletter2Go API. 

## Installation

This needs python 3 and requests. in ubuntu these are the packages `python3` and `python3-requests`.
Alternatively, you can install the requests-dependency using a virtual environment:

    virtualenv --python=python3 venv && . venv/bin/activate && pip install -r requirements.txt

## Usage

### Get lists

A list id is required to use the other commands, show all lists with their id and name:

    n2gclient.py --authkey "authkey from web frontend" --user "username" --password "password" --lists

### Get list recipients

Using a list id, get all of its recipients (this may take a while, as multiple requests are made):

    n2gclient.py --authkey "authkey from web frontend" --user "username" --password "password" --listid "abcdefgh" --get

### Set list recipients

Reading a newline seperated list from standard input, set the recipients for a list:

    cat recipients | n2gclient.py --authkey "authkey from web frontend" --user "username" --password "password" --listid "abcdefgh" --set

The list is cleared before uploading the new recipients.

### Clear list recipients

Remove all recipients from a list:

    n2gclient.py --authkey "authkey from web frontend" --user "username" --password "password" --listid "abcdefgh" --clear
