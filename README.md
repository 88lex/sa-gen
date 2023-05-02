### **sagen**

May 2023 NOTE: `sa-gen` has been updated to 
  - Create a Google Group if it does not already exist (set in sa-gen.conf)
  - Automatically add service account emails to the specified Google Group
  - Install gcloud sdk (if you need) with the `install_gcloud` script
  - Use sa-gen.conf to specify variables (You must rename or copy sa-gen-default.conf to sa-gen.conf, then edit it)
  - Generate a random alphanumeric SUFFIX for your projects (Google needs a unique project name)
  - SUFFIX may also be set manually in `sa-gen.conf` if you like
  - Prior versions of sa-gen still run, and have been put in the /old directory

  - A separate, simple script called `make-tds` (from sasync/utils) is added here as well
    - `make-tds` will create as many new Shared Drives/Team Drives as you like
    - It uses Mawaya's fclone which you can install with `install_fclone`
    - If you specify one existing Shared Drive on the same account then all new Shared Drives/TDs will be created with the same Members and permissions as the existing Shared Drive

THINGS TO CONSIDER:
  - Google accounts generally allow 12, 25 or 50 projects depending on the type of account
  - You may request additional projects. But Google has been a little more selective about granting additional projects recently
  - Each project may have up to 100 service accounts. If you try to create more than 100 you will see an error
  - For each service account you can create and download up to 10 keys. If you try to create more than 10 keys then you will see an error
  - Projects can be deleted. But they stay in a kind of deleted-project-bin for ~30 days. After the 30 day period your unused project quota will increase again
  - Generally, project names are irrelevant. They can be used by most applications/ecosystems regardless of name
  - Service accounts and/or their keys can be deleted. Unlike with projects, deleted service accounts and/or keys can be recreated immediately
  - The naming of service accounts and their respective email addresses are, as with projects, generally irrelevant. As long as they are added to a Google Group then you can use them with Shared Drives/Team Drives.
  
=======================
The documentation below is mostly unchanged, but there may be small differences from the prior version (e.g. slight variable names changes). When I have spare time I will update the docs. If anything glaring, please ping me.


NOTE: `sagen` has a sister application called [safire]( https://github.com/88lex/safire ), a python app with a number of additional features and better speed. `safire` can be installed via git clone, pip install safire or from Colab. [[ It has been a while since `safire` was updated, whereas sa-gen still works nicely, but more slowly. ]]

Please see: https://github.com/88lex/sa-guide For more info on sagen, safire and setting up service accounts.

This script is not enormously difficult, but does require reading carefully and installing/setting up gcloud sdk.

Usage:  `./sa-gen` will run the script using the variables that you insert/edit below.

CHANGELOG: The updated sagen does exactly what the old version did, except
  - Google's back end sometimes lags for a few seconds between creating projects or service accounts and giving the sdk access to see them.
  - As a result, sagen now has variable delays for each cycle of creating service accounts and between each 'function'. The functions are:
    - Creating a project. If a project exists an ERROR message will tell you. It is non-fatal, ignore it.
    - Enabling apis that give the SAs permission to access Google Drive and gsheets. Others can be added manually if you like.
    - Creating service accounts (SAs) in each project that has been created.
    - Downloading json keys that include a token that allows you to access and act upon Drive and gsheet resources. Guard the keys with your life.
    - Creating a members.csv (current) and allmembers.csv (cumulative) list of all SA emails, which can be added to My Drive, a Shared Drive (Team Drive) and/or a gsheet. These emails can be added individualy or in bulk (see Bulk Add to Group).

For sa-gen to run correctly you MUST first edit sa-gen itself, inserting your own information in the fields described below.
Be sure to run `chmod +x sa-gen` to all the script to execute.


This script uses gcloud sdk to create multiple projects and up to 100 service accounts per project.
It also downloads a json file for each service account that is created, putting a copy of the json file into the
directory that you specify in `KEYS_DIR` in the script.

The script creates a csv file in the `KEYS_DIR` directory that can be used to bulk upload service account emails to a google group,
which can then be added to your Team Drives and/or My Drive folders. This allows you to use service accounts with rclone sync/copy

If you have already installed `gcloud sdk` please be sure you have initialized the account for which you wish to create projects and service accounts.

If you have not installed `gcloud sdk` please go to https://cloud.google.com/sdk/docs/quickstarts and follow the instructions to install for your OS,
Once you have installed gcloud sdk be sure to run `gcloud init` and authorize (auth) to the account where you want to create service accounts.

There are a number of variables that you need to specify to run sa-gen for your own account, and to create service accounts and jsons
that are names the way you want to name them. These variables are described below. The names and numeric ranges are quite flexible -
name them as you like.

**export KEYS_DIR=/opt/sa/all**
This is the location where you want to store your service account json keys. Please create it before running this script
Note that you can create a maximum of 100 service accounts per project, but you can store all of your json keys in this
directory as long as the json file names do not overlap.

**export ORGANIZATION_ID="insertyourorganizationID"**
This can be left blank ( "" ) if you have already initialized the organization in gcloud sdk with `gcloud init`.

However if you want to be certain then you can manually replace it with your own ORGANIZATION_ID. It is a numeric ID, rather than your account/domain name.
The easiest way find your own ORGANIZATION ID is to use the console where you have installed `gcloud sdk` and type the command `gcloud organizations list`.
This will show you your DISPLAY_NAME, ID, and DIRECTORY_CUSTOMER_ID. The 12 digit number in the middle is your ORGANIZATION_ID. Insert that
number in the script.

If for some reason you cannot find the ORGANIZATION_ID using the gcloud sdk you can also go to https://console.cloud.google.com/iam-admin/settings.
On that screen go to the top. Choose `Select Project`, then in the popup choose `Select From` and choose your account/domain name. You should see
a column titled ID. The 12 digit number next to your account/domain name is the ORGANIZATION_ID.

NOTE: DO NOT USE UPPER CASE, spaces or non-alphanumeric symbols. The GROUP_NAME and PROJECT_BASE_NAME that you use below MUST be lower-case alphanumeric characters (a-z, 0-9, - or _ are okay).

**export GROUP_NAME=mygroup@mydomain.com**
This is the name of the group that you will share your team drives or my drive folders with.
Normally this will be in the format `some_group_name@googlegroups.com` or `mygroup@mydomain.com`
You can create the group by going to `https://admin.google.com/ac/groups`.

**export PROJECT_BASE_NAME=myprojectbasename**
This is the base name for a project created with this script. It will be appended with the number of each project
as they are created. For example, a base of 'sasync' will create projects called `sasync1`, `sasync2` and so on.
You should choose a base name likely to be unique to your organisation.
NOTE: If using a domain that you share with others, then use a name other than `sasync` as sa-gen will fail if that project name has already been used.

**export FIRST_PROJECT_NUM=1**
**export LAST_PROJECT_NUM=2**
These are the starting and ending numbers that are appended to the project name. As noted above, a base name of `sasync` and first number of `1` will create projects `sasync1`, `sasync2` until the LAST_PROJECT_NUM .

Use as many projects as you like, within allowable limits. Paid gsuite accounts can create a max of 50 accounts, but can apply for more.
Free accounts can create up to 12 projects.

It is a good idea to NOT delete old projects. Google keeps them for 30 days after deletion and this reduces the number of new projects you can create.
If you have old projects and want to reuse them then it is easier to rename them to fit your pattern above.

If you have already created projects then it is a good idea to start with the next unused project number. For example, if you have
created 500 jsons in projects sacopy1 through sacopy5 and you want to create 5 more projects then you would set FIRST_PROJECT_NUM=6 and
LAST_PROJECT_NUM=10.

**export SA_EMAIL_BASE_NAME=sagen**
This is the base name for each service account email created with this script. It will be appended with the number of each service account
as they are created. For example, an email base of 'sagen' along with a project base of 'sasync' will create service accounts with email addresses
in the format sagen1@sasync1.iam.gserviceaccount.com , incrementing up to sagen100@sasync1.iam.gserviceaccount.com. If you have more
than one project then the script will increment SA numbers and project numbers, e.g. sagen101@sasyncy2.iam.gserviceaccount.com and so on.

**export FIRST_SA_NUM=1**
FIRST_SA_NUM will be the number of the first service account and json file for this batch that you are creating.
If this is your first batch then set FIRST_SA=1. Otherwise set it to your highest SA number+1

**export NUM_SAS_PER_PROJECT=100**
NUM_SAS_PER_PROJECT is the number of service accounts/SAs that you want to create for each project

If you have set all of these correctly they you can run `./sa-gen` and it will cycle through creation of your projects and service accounts.
The json files will be in the directory you specified, along with a file called `members.csv` which you can bulk upload to your group.

**Once you have set the above variables go the command line and run `./sa-gen` . The script will create the projects and service accounts for you.**

**Please see https://github.com/88lex/sa-guide for further information. Note that sa-guide may not be completely updated, but should provide some help.**

*****************
*****************

**NOTES:**
Forked from DashLt at https://gist.github.com/DashLt/4c6ff6e9bde4e9bc4a9ed7066c4efba4 and
Forked from mc2squared at https://gist.github.com/mc2squared/01c933a8172a26af88285610a0e5af8d
Borrowed some great ideas from JD at https://gist.github.com/zen-jd/cc6c609b9389443bd7eeac3be8c74710
