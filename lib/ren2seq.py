#!/usr/bin/env python3
import json, os, sys

# default_dir = "/opt/test/accounts/"

def ren_seq(dir):
    filelist = os.listdir(dir)
    new_name = []

    for file in sorted(filelist):
        try:
            with open(dir + file) as f:
                data = json.load(f)
                digits = list(filter(lambda x: x.isdigit(), data['client_email'].split("@")[0]))
                new_name = ("".join(digits) + ".json").lstrip("0")
                if os.path.exists(dir + new_name):
                    continue
                os.rename(dir + file, dir + new_name)
                print(new_name)
        except:
            continue

if __name__ == "__main__":
    dir = sys.argv[1]
    ren_seq(dir)

