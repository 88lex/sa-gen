#!/usr/bin/env python3
# usage: sagen.py --action flag   example: ./sagen.py --list-projects OR ./sagen.py -lp

import errno
import os
import pickle
import sys
from base64 import b64decode
from glob import glob
from json import loads
from time import sleep

from configargparse import ArgParser
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from lib import group_manager, ren2email, ren2seq, ren2uniqid

SCOPES = [
    "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/iam", "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.group.member"
]
project_create_ops = []
current_key_dump = []
retry = 10


# Create service accounts
def _create_accounts(iam, project, sas_per_project, email_prefix, sleep_time, nxtsa):
    batch = iam.new_batch_http_request(callback=_def_batch_resp)
    count = sas_per_project - len(_list_sas(iam, project))
    print(f"Creating " + str(count) + " service accounts in project " + project)
    for _ in range(count):
        sa_id = email_prefix + "{n:0{w}}".format(n=nxtsa, w=args.spad)
        nxtsa += 1
        name = "projects/" + project
        body = {"accountId": sa_id, "serviceAccount": {"displayName": sa_id}}
        batch.add(iam.projects().serviceAccounts().create(name=name, body=body))
    batch.execute()
    sleep(sleep_time / 10)
    return nxtsa


# List projects
def _get_projects(service):
    return [i["projectId"] for i in service.projects().list().execute()["projects"]]


# Default batch callback handler
def _def_batch_resp(id, resp, exception):
    if exception is not None:
        if str(exception).startswith("<HttpError 429"):
            sleep(args.sleep_time / 10)
        else:
            print(str(exception))


# Project Creation Batch Handler
def _pc_resp(id, resp, exception):
    global project_create_ops
    if exception is not None:
        print(str(exception))
    else:
        for i in resp.values():
            project_create_ops.append(i)


# Project Creation
def _create_projects(cloud, count, nxtproj, sleep_time):
    global project_create_ops
    batch = cloud.new_batch_http_request(callback=_pc_resp)
    new_projs = []
    for i in range(count):
        _nxtproj = "{n:0{w}}".format(n=nxtproj, w=args.ppad)
        new_proj = args.project_prefix + _nxtproj
        print(f"Creating project", new_proj)
        nxtproj += 1
        new_projs.append(new_proj)
        batch.add(cloud.projects().create(body={"project_id": new_proj}))
    batch.execute()
    sleep(sleep_time)
    for i in project_create_ops:
        while True:
            resp = cloud.operations().get(name=i).execute()
            if "done" in resp and resp["done"]:
                break
            sleep(sleep_time)
    return new_projs


# Enable services ste for projects in projects
def _enable_services(service, projects, ste):
    batch = service.new_batch_http_request(callback=_def_batch_resp)
    for i in projects:
        for j in ste:
            batch.add(service.services().enable(name="projects/%s/services/%s" % (i, j)))
    batch.execute()


# List SAs in project
def _list_sas(iam, project):
    resp = (iam.projects().serviceAccounts().list(name="projects/" + project, pageSize=100).execute())
    if "accounts" in resp:
        return resp["accounts"]
    return []


# Create Keys Batch Handler
def _batch_keys_resp(id, resp, exception):
    global current_key_dump
    if exception is not None:
        current_key_dump = None
        # sleep(sleep_time / 100)
    elif current_key_dump is None:
        # sleep(sleep_time / 100)
        pass
    else:
        current_key_dump.append(
            (resp["name"][resp["name"].rfind("/"):], b64decode(resp["privateKeyData"]).decode("utf-8")))


# Create Keys
def _create_sa_keys(iam, projects, sas_per_project, path, nxtkey, sleep_time):
    global current_key_dump
    # nxtkey = args.nxtkey
    for i in sorted(projects):
        current_key_dump = []
        if current_key_dump is None or len(current_key_dump) < sas_per_project:
            batch = iam.new_batch_http_request(callback=_batch_keys_resp)
            total_sas = _list_sas(iam, i)
            print(f"Downloading " + str(len(total_sas)) + " SA keys in project " + i)
            for j in total_sas:
                batch.add(iam.projects().serviceAccounts().keys().create(
                    name="projects/%s/serviceAccounts/%s" % (i, j["uniqueId"]),
                    body={
                        "privateKeyType": "TYPE_GOOGLE_CREDENTIALS_FILE",
                        "keyAlgorithm": "KEY_ALG_RSA_2048",
                    },
                ))
            batch.execute()
            if current_key_dump is not None:
                for j in range(len(current_key_dump)):
                    k = current_key_dump[j]
                    key_num = "{num:0{width}}".format(num=nxtkey, width=args.kpad)
                    json_name = "".join(filter(None, (args.json_key_prefix, key_num)))
                    with open("%s/%s.json" % (path, json_name), "w+") as f:
                        f.write(k[1])
                    nxtkey += 1
            else:
                print("Redownloading keys from %s" % i)
                current_key_dump = []
        # sleep(sleep_time)
    return nxtkey


# Delete Service Accounts
def _delete_sas(iam, project):
    sas = _list_sas(iam, project)
    batch = iam.new_batch_http_request(callback=_def_batch_resp)
    for i in sas:
        batch.add(iam.projects().serviceAccounts().delete(name=i["name"]))
    batch.execute()


def run_sagen(credentials, token, path, list_projects, list_sas, create_projects, max_projects, enable_services,
              services, create_sas, delete_sas, download_keys, sas_per_project, quick_setup, new_only, nxtproj, nxtsa,
              nxtkey, project_prefix, email_prefix, json_key_prefix, sleep_time, rename_keys, add_to_group,
              delete_from_group, list_groups, list_group_members, group_token, csv, *args, **kwargs):

    selected_projects = []
    proj_id = loads(open(credentials, "r").read())["installed"]["project_id"]
    creds = None
    if os.path.exists(token):
        with open(token, "rb") as t:
            creds = pickle.load(t)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials, scopes=SCOPES)
            creds = flow.run_console()
        with open(token, "wb") as t:
            pickle.dump(creds, t)

    cloud = build("cloudresourcemanager", "v1", credentials=creds)
    iam = build("iam", "v1", credentials=creds)
    serviceusage = build("serviceusage", "v1", credentials=creds)

    projs = None
    while projs == None:
        try:
            projs = _get_projects(cloud)
        except HttpError as e:
            if (loads(e.content.decode("utf-8"))["error"]["status"] == "PERMISSION_DENIED"):
                try:
                    serviceusage.services().enable(name="projects/%s/services/cloudresourcemanager.googleapis.com" %
                                                   proj_id).execute()
                except HttpError as e:
                    print(e._get_reason())
                    input("Press Enter to retry.")

    if list_projects:
        resp = sorted(_get_projects(cloud))
        if resp is not None:
            print("Projects (%d):" % len(resp))
            for i in resp:
                print("  " + i)
        else:
            print("No projects founds.")

    if list_sas:
        if list_sas == ["*"]:
            projects = sorted(_get_projects(cloud))
        else:
            projects = list_sas
            # projects = [list_sas,]
        if projects is not None:
            # global sa_csv
            sa_csv = []
            for project in projects:
                resp = _list_sas(iam, project)
                if resp is not None:
                    print(str(len(resp)) + " service accounts in " + project)
                    sa_list = []
                    for i in range(len(resp)):
                        sa_list.append(resp[i]["email"] + " " + "(" + str(resp[i]["uniqueId"]) + ")")
                        sa_csv.append(resp[i]["email"])
                    print(*sorted(sa_list), sep="\n")
                else:
                    print("No service accounts in " + project)
        if csv:
            with open("sa_list.csv", "w") as f:
                for item in sorted(sa_csv):
                    record = csv + "," + item + "," + "MEMBER" + "\n"
                    f.writelines(record)

    if create_projects:
        print("create projects: {}".format(create_projects))
        if create_projects > 0:
            current_count = len(_get_projects(cloud))
            if current_count + create_projects <= max_projects:
                print("Creating %d projects" % (create_projects))
                new_projs = _create_projects(cloud, create_projects, nxtproj, sleep_time)
                selected_projects = new_projs
            else:
                sys.exit("Please reduce the value n for --quick-setup.\n"
                         "You can create %d projects in total, and have %d projects already.\n" %
                         (max_projects, current_count))
        else:
            print("Using existing projects. Ensure you have some :-)")
            input("Press Enter to continue...")
        sleep(sleep_time)

    if enable_services:
        ste = []
        ste.append(enable_services)
        if enable_services == "~":
            ste = selected_projects
        elif enable_services == "*":
            ste = _get_projects(cloud)
        services = [i + ".googleapis.com" for i in services]
        print("Enabling services")
        _enable_services(serviceusage, ste, services)
        sleep(sleep_time)

    if create_sas:
        for project in create_sas:
            stc = []
            stc.append(project)
            if project == "~":
                stc = sorted(selected_projects)
            elif project == "*":
                stc = sorted(_get_projects(cloud))
            for project in sorted(stc):
                # _create_accounts(iam, project, sas_per_project, email_prefix, sleep_time)
                nxtsa = _create_accounts(iam, project, sas_per_project, email_prefix, sleep_time, nxtsa)

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
            if proj == "~":
                std = selected_projects
            elif proj == "*":
                std = _get_projects(cloud)
            nxtkey = _create_sa_keys(iam, std, sas_per_project, path, nxtkey, sleep_time)

    if list_groups:
        group_manager.ls_groups(list_groups, path, credentials, group_token)

    if list_group_members:
        group_mem = group_manager.ls_group_members(list_group_members, path, credentials, group_token)
        [print(num, member) for num, member in enumerate(sorted(group_mem), 1)]
        print("There are", len(group_mem), "members in the group:", list_group_members)

    if add_to_group:
        path, dirs, files = next(os.walk(path))
        duration = group_manager.add_group_members(add_to_group, path, credentials, group_token, sleep_time, retry)
        print("Completed adding SAs to group", add_to_group, "Time:", duration, "seconds")

    if delete_from_group:
        path, dirs, files = next(os.walk(path))
        duration = group_manager.del_group_members(delete_from_group, path, credentials, group_token, sleep_time, retry)
        print("Completed deleting SAs from group", add_to_group, "Time:", duration, "seconds")

    if delete_sas:
        for proj in delete_sas:
            std = []
            std.append(proj)
            if proj == "~":
                std = sorted(selected_projects)
            elif proj == "*":
                std = sorted(_get_projects(cloud))
            for i in sorted(std):
                print("Deleting service accounts in %s" % i)
                _delete_sas(iam, i)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        os.system("python3 sagen.py --help")
        print("\n=== sagen.py requires at least one argument. See options above. ===\n")
        exit()
    parse = ArgParser(default_config_files=["sagen.conf"],
                      description="Create and manage Google projects, service accounts and json keys.")
    parse.add("-qs", "--quick-setup", default=None, type=int, help="Create projects, svc accts and json keys. ")
    parse.add("-no", "--new-only", default=False, action="store_true", help="New projects only.")
    parse.add("-cf", "--config", is_config_file=True, help="path and filename of config file")
    parse.add("-pa", "--path", default="svcaccts", help="Path to key.json files.\n")
    parse.add("-t", "--token", default="creds/token.pickle", help="Specify the pickle token file path.")
    parse.add("-cr", "--credentials", default="creds/creds.json", help="Specify the credentials file path.")
    parse.add("-lp", "--list-projects", default=False, action="store_true", help="List projects in the account.")
    parse.add("-ls", "--list-sas", nargs="+", default=False, help="List service accounts in a project.")
    parse.add("-cp", "--create-projects", type=int, default=None, help="Creates up to N projects.")
    parse.add("-mp", "--max-projects", type=int, default=50, help="Max number of project allowed. Default: 50")
    parse.add("-es", "--enable-services", default=None, help="Enables services on the project. Default: IAM and Drive")
    parse.add("-svcs", "--services", nargs="+", default=["iam", "drive"], help="Specify services to enable.")
    parse.add("-cs", "--create-sas", nargs="+", default=None, help="Create service accounts in a project.")
    parse.add("-spp", "--sas-per-project", type=int, default=100, help="# of service accounts created per project.")
    parse.add("-ds", "--delete-sas", nargs="+", default=None, help="Delete service accounts in a project.")
    parse.add("-dk", "--download-keys", nargs="+", default=None, help="Download keys for svc accounts in a project.")
    parse.add("-np", "--next-project-num", dest="nxtproj", default=1, type=int, help="Starting # for new projects.")
    parse.add("-ns", "--next-sa-num", dest="nxtsa", default=1, type=int, help="Starting # for service accounts.")
    parse.add("-nk", "--next-json-key-num", dest="nxtkey", default=1, type=int, help="Starting number for json key.")
    parse.add("-ppre", "--project-prefix", default="proj", type=str, help="Starting number for project.")
    parse.add("-epre", "--email-prefix", default="svcacct", type=str, help="prefix of your service account name.")
    parse.add("-kpre", "--json-key-prefix", default=None, type=str, help="Starting # for next json key.")
    parse.add("-st", "--sleep-time", default=5, type=int, help="Time to sleep - let google backend digest batches")
    parse.add("-rk", "--rename-keys", default=None, choices=["email", "seq", "uniq"], help="Rename json keys")
    parse.add("-kpad", "--json-key-zero-pad", dest="kpad", default="6", help="Zero pad json key. e.g. 000001")
    parse.add("-spad", "--sa-zero-pad", dest="spad", default="6", help="Zeros pad service account #. e.g. 0001")
    parse.add("-ppad", "--proj-zero-pad", dest="ppad", default="6", help="Zero pad project number. e.g. 0001")
    parse.add("-csv", "--create-group-csv", dest="csv", default=None, help="Create CSV to bulk upload SA emails")
    parse.add("-agm", "--add-to-group", default=None, help="Add SA email from json keys to group")
    parse.add("-dgm", "--delete-from-group", default=None, help="Delete all members from named group")
    parse.add("-lg", "--list-groups", nargs='?', default=None, const="my_customer", help="List groups for mydomain.com")
    parse.add("-lgm", "--list-group-members", default=None, type=str, help="List members in the named group")
    parse.add("-gt", "--group-token", default="creds/grptoken.pickle", help="Path to group token file.")

    args = parse.parse_args()
    print(parse.format_values())
    ## Below is a method to assign variables from args.variables in argparse
    locals().update(vars(args))
    # nxtsa = args.nxtsa
    # nxtkey = args.nxtkey
    # sleep_time = args.sleep_time
    # sas_per_project = args.sas_per_project

    if args.rename_keys:
        keypath = args.path + "/"
        print("Renaming json keys in " + args.path + " to " + args.rename_keys)
        if args.rename_keys == "email":
            ren2email.ren_email(keypath)
        elif args.rename_keys == "seq":
            ren2seq.ren_seq(keypath)
        elif args.rename_keys == "uniq":
            ren2uniqid.ren_uniq(keypath)
        print("Finished renaming json key files")
        exit()

    # If credentials file is invalid, search for one.
    if not os.path.exists(args.credentials):
        options = glob("*.json")
        print("No credentials found at %s. Please enable the Drive API in:\n"
              "https://developers.google.com/drive/api/v3/quickstart/python\n"
              "and save the json file as creds.json" % args.credentials)
        if len(options) < 1:
            exit(-1)
        else:
            i = 0
            print("Select a credentials file below.")
            inp_options = [str(i) for i in list(range(1, len(options) + 1))] + options
            while i < len(options):
                print("  %d) %s" % (i + 1, options[i]))
                i += 1
            inp = None
            while True:
                inp = input("> ")
                if inp in inp_options:
                    break
            if inp in options:
                args.credentials = inp
            else:
                args.credentials = options[int(inp) - 1]
            print("Use --credentials %s next time to use this credentials file." % args.credentials)
    if args.quick_setup:
        opt = "*"
        if args.new_only:
            opt = "~"
        args.services = ["iam", "drive"]
        args.create_projects = args.quick_setup
        args.enable_services = opt
        args.create_sas = opt
        args.download_keys = opt

    run_sagen(**vars(args))
