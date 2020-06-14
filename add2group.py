#!/usr/bin/env python3

# add2group.py adds service accounts to groups
# Forked from folderclone and autorclone
# usage: ./add2group.py -g mygroup@domain.com

import googleapiclient.discovery, json, progress.bar, glob, sys, argparse, time, os, pickle
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from timeit import default_timer as timer
from time import sleep
start = timer()

parse = argparse.ArgumentParser()
parse.add_argument('--path', '-p', default='accounts', help='Path to service accounts folder.')
parse.add_argument('--credentials', '-c', default='credentials/credentials.json', help='Path to credentials file.')
parse.add_argument('--token', '-t', default='credentials/token.pickle', help='Path to token file.')
parsereq = parse.add_argument_group('required arguments')
parsereq.add_argument('--groupaddr', '-g', help='The address of groups for your organization.', required=True)
args = parse.parse_args()
credentials = glob.glob(args.credentials)
creds = None

if os.path.exists(args.token):
    with open(args.token, 'rb') as token:
        creds = pickle.load(token)

# If there are no (valid) credentials available, refresh or authorize in browser
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(credentials[0], scopes=[
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member'
        ])
        creds = flow.run_console()
    with open(args.token, 'wb') as token:
        pickle.dump(creds, token)

group = googleapiclient.discovery.build("admin", "directory_v1", credentials=creds)
print(group.members())
batch = group.new_batch_http_request()
sa = glob.glob('%s/*.json' % args.path)
pbar = progress.bar.Bar("Reading accounts", max=len(sa))

j = 0
for i in sa:
    try:
        ce = json.loads(open(i, 'r').read())['client_email']
        body = {"email": ce, "role": "MEMBER"}
        batch.add(group.members().insert(groupKey=args.groupaddr, body=body))
        pbar.next()
        j = j + 1
        if j >=100:
            batch.execute()
            j = 0            
    except:
        pass

pbar.finish()
# print("Adding accounts to ", args.groupaddr)
# batch.execute()
print("Completed adding SAs to group", args.groupaddr,"==> Elapsed Time = ", round(timer() - start, 2), "seconds")
