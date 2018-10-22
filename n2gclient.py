#!/usr/bin/env python3

import requests
import argparse
import subprocess
import re
import base64
import time
import sys

class N2Go:
    debug = False
    base_url = 'https://api.newsletter2go.com'

    def __init__(self, auth_key, user, password):
        self.token = ""
        self.headers = {}
        self.authenticate(auth_key, user, password)
        self.headers["Content-Type"] = "application/json"

    def authenticate(self, auth_key, user, password):
        url = self.base_url + "/oauth/v2/token"
        headers = { "Authorization": b" ".join([b"Basic",base64.b64encode(auth_key.encode())])}
        body = {"username": user, "password": password, "grant_type": "https://nl2go.com/jwt"}
        res = requests.post(url, headers=headers, json=body)
        res.raise_for_status()

        jres = res.json()
        if self.debug:
            print(jres)

        self.__set_token(jres["access_token"].encode())

    def __set_token(self, token):
        self.token = token
        self.headers["Authorization"] = b" ".join([b"Bearer", self.token])

    def delete_recipients(self, list_id):
        url = self.base_url + "/lists/" + list_id + "/recipients"
        res = requests.delete(url, headers=self.headers)
        if self.debug:
            print(res.json())
        res.raise_for_status()

    def init_recipients(self, list_id, recipients):
        url = self.base_url + "/lists/" + list_id + "/recipients/import/init"
        files = {"file": ("recipients.csv", recipients)}

        # remove content type here
        headers = dict(self.headers)
        del headers["Content-Type"]

        res = requests.post(url, headers=headers, files=files)
        res.raise_for_status()
        jres = res.json()

        if self.debug:
            print(jres)

        return jres["file"]

    def save_recipients(self, list_id, file_id, associations):
        url = self.base_url + "/lists/" + list_id + "/recipients/import/save"
        body = { "file": str(file_id), "associations": associations }
        res = requests.post(url, headers=self.headers, json=body)
        res.raise_for_status()
        jres = res.json()

        if self.debug:
            print(jres)

        if jres["info"]["count"] != 1:
            raise "count value in response isn't 1"
        return jres["value"][0]["id"]
    
    # this returns 400, but likely a bug in n2g api
    def info_import(self, import_id):
        url = self.base_url + "/import/" + str(import_id) + "/info"
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        jres = res.json()
        if jres["info"]["count"] != 1:
            raise "count value in response isn't 1"
        return jres["value"][0]

    def get_list_recipients_ids(self, list_id):
        url = self.base_url + "/lists/" + list_id + "/recipients"
        return self._get_list_recipients_ids(url)

    # helper method for pagination so we don't have to expose
    # the uglyness in the api
    def _get_list_recipients_ids(self, url):
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        jres = res.json()

        if self.debug:
            print(jres)

        recipients_ids = []
        for x in jres["value"]:
            recipients_ids.append(x["id"])

        if "links" in jres["info"]:
            if "_next" in jres["info"]["links"]:
                recipients_ids.extend(self._get_list_recipients_ids(jres["info"]["links"]["_next"]))

        return recipients_ids

    def get_recipient(self, recipient_id):
        url = self.base_url + "/recipients/" + recipient_id
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        jres = res.json()

        if self.debug:
            print(jres)

        if jres["info"]["count"] != 1:
            raise "count value in response isn't 1"
        return jres["value"][0]

    def get_lists_ids(self):
        url = self.base_url + "/lists"
        return self._get_lists_ids(url)

    def _get_lists_ids(self, url):
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        jres = res.json()

        if self.debug:
            print(jres)

        lists_ids = []
        for x in jres["value"]:
            lists_ids.append(x["id"])

        if "links" in jres["info"]:
            if "_next" in jres["info"]["links"]:
                lists_ids.extend(self._get_lists_ids(jres["info"]["links"]["_next"]))

        return lists_ids

    def get_list(self, list_id):
        url = self.base_url + "/lists/" + list_id
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        jres = res.json()

        if self.debug:
            print(jres)

        if jres["info"]["count"] != 1:
            raise "count value in response isn't 1"
        return jres["value"][0]

class Recipients(set):
    @classmethod
    def parse(cls, r):
        x = cls()
        for line in r:
            x.add(str(line).strip())
        return x

    def list(self):
        return list(self)

    def without(self, re):
        return Recipients({x for x in self if not re.match(x)})

    def __repr__(self):
        return "\n".join(self.list())

def list_recipients():
    return Recipients.parse(sys.stdin)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authkey', '-a', type=str, help="newsletter2go auth key")
    parser.add_argument('--user', '-u', type=str, help="newsletter2go username")
    parser.add_argument('--password', '-p', type=str, help="newsletter2go password")
    parser.add_argument('--listid', '-l', type=str, help="list id in newsletter2go api")
    parser.add_argument('--remove', '-r', type=str, help="regexp to remove addresses", default=".*@lists.bytemine.net")
    parser.add_argument('--debug', dest='debug', action='store_true')

    action = parser.add_mutually_exclusive_group()
    action.add_argument('--set', action='store_true', default=False, help='set the recipients of the list')
    action.add_argument('--get', action='store_true', default=False, help='get the recipients of the list')
    action.add_argument('--clear', action='store_true', default=False, help='clear the recipients of the list')
    action.add_argument('--lists', action='store_true', default=False, help='show all lists')
    
    args = parser.parse_args()

    client = N2Go(args.authkey, args.user, args.password)
    client.debug = args.debug

    if args.set:
        # compile regex
        remove = re.compile(args.remove)

        # collect the addresses on the lists
        # this also removes duplicates, as recipients is a set
        recipients = Recipients()
        x = list_recipients()
        recipients.update(x)
        
        # remove the addresses specified by the regexp
        recipients = recipients.without(remove)
        
        if args.debug:
            x = list(recipients)
            x.sort()
            print('\n'.join(x))

        set_list_recipients(client, args.listid, recipients)
    elif args.get:
        get_list_recipients(client, args.listid)
    elif args.clear:
        clear_list_recipients(client, args.listid)
    elif args.lists:
        get_lists(client)

def set_list_recipients(client, listid, recipients):
    client.delete_recipients(listid)
    file_id = client.init_recipients(listid, str(recipients))
    associations = {"0": "email"}
    client.save_recipients(listid, file_id, associations)

def get_list_recipients(client, listid):
    recipient_ids = client.get_list_recipients_ids(listid)
    recipients = []
    for recipient_id in recipient_ids:
        recipients.append(client.get_recipient(recipient_id))
    
    print("\n".join([recipient['email'] for recipient in recipients]))

def clear_list_recipients(client, listid):
    client.delete_recipients(listid)

def get_lists(client):
    lists_ids = client.get_lists_ids()
    lists = []
    for list_id in lists_ids:
        lists.append(client.get_list(list_id))
    
    print("\n".join(["{listid}\t{name}".format(listid=l["id"], name=l["name"]) for l in lists]))

if __name__ == "__main__":
    main()
