#!/usr/bin/env python3

import glob
import json
import os
import pickle
import sys
import time
from time import sleep
from timeit import default_timer as timer

import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

if __name__ == "__main__":
    pass


def group_auth(path, credentials, token):
    credentials = glob.glob(credentials)
    creds = None
    if os.path.exists(token):
        with open(token, "rb") as tkn:
            creds = pickle.load(tkn)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials[0],
                scopes=[
                    "https://www.googleapis.com/auth/admin.directory.group",
                    "https://www.googleapis.com/auth/admin.directory.group.member",
                ],
            )
            creds = flow.run_console()
        with open(token, "wb") as tkn:
            pickle.dump(creds, tkn)
    group = googleapiclient.discovery.build("admin", "directory_v1", credentials=creds)
    return group


def ls_groups(list_groups, path, credentials, token):
    group = group_auth(path, credentials, token)
    if list_groups == "my_customer":
        secondary_request = group.groups().list(customer="my_customer")
    else:
        secondary_request = group.groups().list(domain=list_groups)
    secondary_response = secondary_request.execute()
    if secondary_response and "groups" in secondary_response:
        secondary_instances = secondary_response["groups"]
        for secondary_instance in secondary_instances:
            print(secondary_instance["name"], "(", secondary_instance["email"], ")")


def ls_group_members(groupaddr, path, credentials, token):
    group = group_auth(path, credentials, token)
    response = []
    group_mem = []
    request = {'nextPageToken': None}
    while 'nextPageToken' in request:
        request = group.members().list(groupKey=groupaddr, pageToken=request['nextPageToken']).execute()
        response += request['members']
        group_mem += [i['email'] for i in request['members'] if i["role"] != "OWNER"]
    return group_mem


def add_group_members(groupaddr, path, credentials, token, sleep_time, retry):
    start = timer()
    group = group_auth(path, credentials, token)
    batch = group.new_batch_http_request()
    keys = glob.glob("%s/*.json" % path)
    sa_emails = []
    [sa_emails.append(json.loads(open(key, "r").read())["client_email"]) for key in keys]
    group_members = ls_group_members(groupaddr, path, credentials, token)
    # init_num_group_members = len(group_members)
    sa = [i for i in sa_emails if i not in group_members]
    while sa and retry:
        print("Adding", str(len(sa)), "service accounts to group:", groupaddr)
        j = 0
        retry -= 1
        while sa:
            try:
                j += 1
                ce = sa.pop(0)
                batch.add(group.members().insert(groupKey=groupaddr, body={
                    "email": ce,
                    "role": "MEMBER"
                }),
                          callback=None)
                if j >= 100 or len(sa) == 0:
                    print("Adding", j, "SAs to", groupaddr, "Remaining # SAs:", len(sa))
                    j = 0
                    batch.execute()
                    batch = group.new_batch_http_request()
            except:
                pass
    duration = round(timer() - start, 2)
    return duration


def del_group_members(groupaddr, path, credentials, token, sleep_time, retry):
    start = timer()
    group = group_auth(path, credentials, token)
    batch = group.new_batch_http_request()
    sa = ls_group_members(groupaddr, path, credentials, token)
    while sa and retry:
        print("Deleting", str(len(sa)), "service accounts from group:", groupaddr)
        j = 0
        retry -= 1
        while sa:
            try:
                j += 1
                ce = sa.pop(0)
                batch.add(group.members().delete(groupKey=groupaddr, memberKey=ce), callback=None)
                if j >= 100 or len(sa) == 0:
                    print("Deleting", j, "SAs from", groupaddr)
                    j = 0
                    batch.execute()
                    batch = group.new_batch_http_request()
            except:
                pass
        sa = ls_group_members(groupaddr, path, credentials, token)
        if sa:
            print("Google batch missed some. Retrying delete of", len(sa), "SAs")
    duration = round(timer() - start, 2)
    return duration
