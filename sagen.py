#!/usr/bin/env python3
# usage: sagen.py --action flag
# example: sagen.py --list-projects

import sys, errno, os, pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from argparse import ArgumentParser
import argparse
from base64 import b64decode
from json import loads
from time import sleep
from glob import glob
from sagenconf import *

SCOPES = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/cloud-platform','https://www.googleapis.com/auth/iam']
project_create_ops = []
current_key_dump = []

# Create service accounts
def _create_accounts(iam,project,sas_per_project):
    batch = iam.new_batch_http_request(callback=_def_batch_resp)
    global next_sa_num
    count = sas_per_project - len(_list_sas(iam,project))
    print(f'Creating ' + str(count) + ' service accounts in project ' + project)
    for i in range(count):
        sa_id = email_prefix + f"{next_sa_num:06}"
        #print("Creating service account = ", sa_id)
        next_sa_num += 1
        batch.add(iam.projects().serviceAccounts().create(name='projects/' + project, body={ 'accountId': sa_id, 'serviceAccount': { 'displayName': sa_id }}))
    batch.execute()
    sleep(sleep_time)
    #count = sas_per_project - len(_list_sas(iam,project))
    #if count > 0:
    #    _create_accounts(iam,project,sas_per_project)

# List projects
def _get_projects(service):
    return [i['projectId'] for i in service.projects().list().execute()['projects']]

# Default batch callback handler
def _def_batch_resp(id,resp,exception):
    if exception is not None:
        if str(exception).startswith('<HttpError 429'):
            sleep(sleep_time/10)
        else:
            print(str(exception))

# Project Creation Batch Handler
def _pc_resp(id,resp,exception):
    global project_create_ops
    if exception is not None:
        print(str(exception))
    else:
        for i in resp.values():
            project_create_ops.append(i)

# Project Creation
def _create_projects(cloud,count,next_project_num):
    global project_create_ops
    batch = cloud.new_batch_http_request(callback=_pc_resp)
    new_projs = []
    for i in range(count):
        next_project_str = str(f"{next_project_num:04}")
        new_proj = project_prefix + next_project_str
        print(f'The new project is named ' + new_proj + ' using prefix ' + project_prefix + ' and number ' + str(next_project_num))
        next_project_num = next_project_num + 1
        new_projs.append(new_proj)
        batch.add(cloud.projects().create(body={'project_id':new_proj}))
    batch.execute()
    sleep(sleep_time)
    for i in project_create_ops:
        while True:
            resp = cloud.operations().get(name=i).execute()
            if 'done' in resp and resp['done']:
                break
            sleep(sleep_time)
    return new_projs

# Enable services ste for projects in projects
def _enable_services(service,projects,ste):
    batch = service.new_batch_http_request(callback=_def_batch_resp)
    for i in projects:
        for j in ste:
            batch.add(service.services().enable(name='projects/%s/services/%s' % (i,j)))
    batch.execute()

# List SAs in project
def _list_sas(iam,project):
    resp = iam.projects().serviceAccounts().list(name='projects/' + project,pageSize=100).execute()
    if 'accounts' in resp:
        return resp['accounts']
    return []

# Create Keys Batch Handler
def _batch_keys_resp(id,resp,exception):
    global current_key_dump
    if exception is not None:
        current_key_dump = None
        sleep(sleep_time/10)
    elif current_key_dump is None:
        sleep(sleep_time/10)
    else:
        current_key_dump.append((
            resp['name'][resp['name'].rfind('/'):],
            b64decode(resp['privateKeyData']).decode('utf-8')
        ))

# Create Keys
def _create_sa_keys(iam,projects,path):
    global current_key_dump
    global next_json_key_num
    for i in sorted(projects):
        current_key_dump = []
        #print('Downloading keys from %s' % i)
        if current_key_dump is None or len(current_key_dump) < sas_per_project:
            batch = iam.new_batch_http_request(callback=_batch_keys_resp)
            total_sas = _list_sas(iam,i)
            print(f"Downloading " + str(len(total_sas)) + " SA keys in project " + i)
            for j in total_sas:
                batch.add(iam.projects().serviceAccounts().keys().create(
                    name='projects/%s/serviceAccounts/%s' % (i,j['uniqueId']),
                    body={
                        'privateKeyType':'TYPE_GOOGLE_CREDENTIALS_FILE',
                        'keyAlgorithm':'KEY_ALG_RSA_2048'
                    }
                ))
            batch.execute()
            if current_key_dump is not None:
                for j in range(len(current_key_dump)):
                    k = current_key_dump[j]
                    json_name = json_key_prefix + str(next_json_key_num)
                    with open('%s/%s.json' % (path, json_name),'w+') as f:
                        f.write(k[1])
                    next_json_key_num += 1
            else:
                print('Redownloading keys from %s' % i)
                current_key_dump = []

# Delete Service Accounts
def _delete_sas(iam,project):
    sas = _list_sas(iam,project)
    batch = iam.new_batch_http_request(callback=_def_batch_resp)
    for i in sas:
        batch.add(iam.projects().serviceAccounts().delete(name=i['name']))
    batch.execute()

# def serviceaccountfactory(
#     credentials='credentials.json',
#     token='token.pickle',
#     path=None,
#     list_projects=False,
#     list_sas=None,
#     create_projects=None,
#     max_projects=max_proj,
#     enable_services=None,
#     services=['iam','drive'],
#     create_sas=None,
#     delete_sas=None,
#     download_keys=None,
#     sas_per_project=100,
#     *args,
#     **kwargs
#     ):

def serviceaccountfactory(credentials,token,path,list_projects,list_sas,create_projects,max_projects,
    enable_services,services,create_sas,delete_sas,download_keys,sas_per_project,*args,**kwargs):

    selected_projects = []
    proj_id = loads(open(credentials,'r').read())['installed']['project_id']
    creds = None
    if os.path.exists(token):
        with open(token, 'rb') as t:
            creds = pickle.load(t)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
            creds = flow.run_console()
        with open(token, 'wb') as t:
            pickle.dump(creds, t)

    cloud = build('cloudresourcemanager', 'v1', credentials=creds)
    iam = build('iam', 'v1', credentials=creds)
    serviceusage = build('serviceusage','v1',credentials=creds)

    projs = None
    while projs == None:
        try:
            projs = _get_projects(cloud)
        except HttpError as e:
            if loads(e.content.decode('utf-8'))['error']['status'] == 'PERMISSION_DENIED':
                try:
                    serviceusage.services().enable(name='projects/%s/services/cloudresourcemanager.googleapis.com' % proj_id).execute()
                except HttpError as e:
                    print(e._get_reason())
                    input('Press Enter to retry.')
    if list_projects:
        return sorted(_get_projects(cloud))
    if list_sas:
        return _list_sas(iam,list_sas)
    if create_projects:
        print("create projects: {}".format(create_projects))
        if create_projects > 0:
            current_count = len(_get_projects(cloud))
            if current_count + create_projects <= max_projects:
                print('Creating %d projects' % (create_projects))
                nprjs = _create_projects(cloud, create_projects, next_project_num)
                selected_projects = nprjs
            else:
                sys.exit('Please reduce the value n for --quick-setup.\n'
                       'You can create %d projects in total, and have %d projects already.\n'
                        % (create_projects, max_projects, current_count))
        else:
            print('Will overwrite all service accounts in existing projects.\n'
                  'So make sure you have some projects already.')
            input("Press Enter to continue...")

    if enable_services:
        ste = []
        ste.append(enable_services)
        if enable_services == '~':
            ste = selected_projects
        elif enable_services == '*':
            ste = _get_projects(cloud)
        services = [i + '.googleapis.com' for i in services]
        print('Enabling services')
        _enable_services(serviceusage,ste,services)
    if create_sas:
        for proj in create_sas:
            stc = []
            stc.append(proj)
            if proj == '~':
                stc = sorted(selected_projects)
            elif proj == '*':
                stc =  sorted(_get_projects(cloud))
            for i in sorted(stc):
                _create_accounts(iam,i,sas_per_project)
            #_create_accounts(iam, stc, sas_per_project)
    # if create_sas:
    #     stc = []
    #     stc.append(create_sas)
    #     if create_sas == '~':
    #         stc = sorted(selected_projects)
    #     elif create_sas == '*':
    #         stc =  sorted(_get_projects(cloud))
    #     for i in sorted(stc):
    #         _create_accounts(iam,i,sas_per_project)
    #     #_create_accounts(iam, stc, sas_per_project)

    if download_keys:
        try:
            os.mkdir(path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise
        for proj in download_keys:
            std = []
            std.append(proj)
            if proj == '~':
                std = selected_projects
            elif proj == '*':
                std = _get_projects(cloud)
            _create_sa_keys(iam,std,path)
            #next_json_key_num = _create_sa_keys(iam,std,path)
    # if delete_sas:
    #         std = []
    #         std.append(str(delete_sas))
    #         if delete_sas == '~':
    #             std = sorted(selected_projects)
    #         elif delete_sas == '*':
    #             std = sorted(_get_projects(cloud))
    #         for i in sorted(std):
    #             print('Deleting service accounts in %s' % i)
    #             _delete_sas(iam,i)

    if delete_sas:
        for proj in delete_sas:
            # print("delete_sas = ", delete_sas)
            # print(type(delete_sas))
            # print("proj = ", proj)
            #exit()
            std = []
            std.append(proj)
            # if delete_sas == '~':
            if proj == '~':
                std = sorted(selected_projects)
            # elif delete_sas == '*':
            elif proj == '*':
                std = sorted(_get_projects(cloud))
            for i in sorted(std):
                # print("std = ", std)
                # print("i = ", i)
                # print(type(i))
                # exit()
                print('Deleting service accounts in %s' % i)
                _delete_sas(iam,i)

if __name__ == '__main__':

    if len(sys.argv) < 2:
        os.system('python3 sagen.py --help')
        print("\n=== sagen.py requires at least one argument. See options above. ===\n")
        exit()

    parse = ArgumentParser(description='A tool to create and manage Google service accounts.')
    parse.add_argument('--path','-p',default='accounts',help='Directory for account credential files.\n')
    parse.add_argument('--token','-t',default='token.pickle',help='Specify the pickle token file path.')
    parse.add_argument('--credentials','-cr',default='credentials.json',help='Specify the credentials file path.')
    parse.add_argument('--list-projects','-lp',default=False,action='store_true',help='List projects viewable by the user.')
    parse.add_argument('--list-sas','-ls',default=False,help='List service accounts in a project.')
    parse.add_argument('--create-projects','-cp',type=int,default=None,help='Creates up to N projects.')
    parse.add_argument('--max-projects','-mp',type=int,default=12,help='Max number of project allowed. Default: 12')
    parse.add_argument('--enable-services','-es',default=None,help='Enables services on the project. Default: IAM and Drive')
    parse.add_argument('--services','-s',nargs='+',default=['iam','drive'],help='Specify a different set of services to enable. Overrides the default.')
    parse.add_argument('--create-sas','-cs',nargs='+',default=None,help='Create service accounts in a project.')
    parse.add_argument('--sas-per-project','-spp',type=int,default=100,help='Number of service accounts created per project.')
    parse.add_argument('--delete-sas','-ds',nargs='+',default=None,help='Delete service accounts in a project.')
    parse.add_argument('--download-keys','-k',nargs='+',default=None,help='Download keys for all the service accounts in a project.')
    parse.add_argument('--quick-setup','-qs',default=None,type=int,help='Create projects, enable services, create service accounts and download keys. ')
    parse.add_argument('--new-only','-n',default=False,action='store_true',help='Do not use existing projects.')
    args = parse.parse_args()

    # print("Printing all args")
    # print(args)
    # print(type(args))
    # print(**vars(args))
    # #print(argparse.Namespace())
    # #print(locals())
    # #print(globals())
    # exit()
    
    # If credentials file is invalid, search for one.
    if not os.path.exists(args.credentials):
        options = glob('*.json')
        print('No credentials found at %s. Please enable the Drive API in:\n'
              'https://developers.google.com/drive/api/v3/quickstart/python\n'
              'and save the json file as credentials.json' % args.credentials)
        if len(options) < 1:
            exit(-1)
        else:
            i = 0
            print('Select a credentials file below.')
            inp_options = [str(i) for i in list(range(1,len(options) + 1))] + options
            while i < len(options):
                print('  %d) %s' % (i + 1,options[i]))
                i += 1
            inp = None
            while True:
                inp = input('> ')
                if inp in inp_options:
                    break
            if inp in options:
                args.credentials = inp
            else:
                args.credentials = options[int(inp) - 1]
            print('Use --credentials %s next time to use this credentials file.' % args.credentials)
    if args.quick_setup:
        opt = '*'
        if args.new_only:
            opt = '~'
        args.services = ['iam','drive']
        args.create_projects = args.quick_setup
        args.enable_services = opt
        args.create_sas = opt
        args.download_keys = opt

    resp = serviceaccountfactory(**vars(args))
    # resp = serviceaccountfactory(
    #     path=args.path,
    #     token=args.token,
    #     credentials=args.credentials,
    #     list_projects=args.list_projects,
    #     list_sas=args.list_sas,
    #     create_projects=args.create_projects,
    #     max_projects=args.max_projects,
    #     create_sas=args.create_sas,
    #     delete_sas=args.delete_sas,
    #     enable_services=args.enable_services,
    #     services=args.services,
    #     download_keys=args.download_keys
    # )
    if resp is not None:
        if args.list_projects:
            if resp:
                print('Projects (%d):' % len(resp))
                for i in resp:
                    print('  ' + i)
            else:
                print('No projects.')
        elif args.list_sas:
            if resp:
                print('Service accounts in %s (%d):' % (args.list_sas,len(resp)))
                for i in resp:
                    print('  %s (%s)' % (i['email'],i['uniqueId']))
            else:
                print('No service accounts.')
