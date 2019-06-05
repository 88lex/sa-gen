**sa-gen**

This script uses gcloud sdk to create multiple projects and up to 100 service accounts per project.
It also downloads a json file for each service account that is created.

The script also creates a csv file that can be used to bulk upload service account emails to a google group, 
which can then be added to your Team Drives and/or My Drive folders. This allows you to use service accounts with rclone sync/co


**NOTES:**
Forked from DashLt at https://gist.github.com/DashLt/4c6ff6e9bde4e9bc4a9ed7066c4efba4 and
Forked from mc2squared at https://gist.github.com/mc2squared/01c933a8172a26af88285610a0e5af8d
Borrowed some great ideas from JD at https://gist.github.com/zen-jd/cc6c609b9389443bd7eeac3be8c74710

**export KEYS_DIR=/opt/sa**
This is the location where you want to store your service account json keys. Please create it before running this script
Note that you can create a maximum of 100 service accounts per project, but you can store all of your json keys in this
directory as long as the json file names do not overlap.

**export ORGANIZATION_ID=123456789012**
This is your ORGANIZATION_ID. It is the numeric ID, rather than your account/domain name
To find it go to https://console.cloud.google.com/iam-admin/settings. Under Organization name you will see the numeric `OrganizationID`. 
Alternatively you can choose your organization by manually running `gcloud init` after installing the sdk. If you do this then you
can leave it blank `ORGANIZATION_ID=""`

**export GROUP_NAME=mygroup@mydomain.com**
This is the name of the group that you will share your team drives or my drive folders with.
Normally this will be in the format "some_group_name@googlegroups.com" or "mygroup@mydomain.com"

**export PROJECT_BASE_NAME=sasync**
This is the base name for a project created with this script. It will be appended with the number of each project
as they are created. For example, a base of 'sacopy' will create projects called `sacopy1`, `sacopy2` and so on.

**export FIRST_PROJECT_NUM=1
export LAST_PROJECT_NUM=12**

These are the starting and ending numbers for the project name. As noted above, a base name of 'sacopy` and first number of `1` will
create projects `sacopy1`, `sacopy2` until the LAST_PROJECT_NUM
Note that paid gsuite accounts can create a max of 50 accounts, but can apply for more. Free accounts can create up to 12 projects

**export SA_EMAIL_BASE_NAME=sagen**
This is the base name for each service account email created with this script. It will be appended with the number of each service account
as they are created. For example, a base of 'sagen' will create service accounts with email addresses
in the format sagen1@sacopy1.iam.gserviceaccount.com , incrementing up to sagen100@sacopy1.iam.gserviceaccount.com. If you have more
than one project then the script will increment SA numbers and project numbers, e.g. sagen101@sacopy2.iam.gserviceaccount.com and so on.

**export FIRST_SA_NUM=1**
FIRST_SA_NUM will be the number of the first service account and json file for this batch that you are creating.
If this is your first batch then set FIRST_SA=1. Otherwise set it to your highest SA number+1

**export NUM_SAS_PER_PROJECT=100**
NUM_SAS_PER_PROJECT is the number of service accounts/SAs that you want to create for each project

If you have set all of these correctly they you can run `./sa-gen` and it will cycle through creation of your projects and service accounts. 
The json files will be in the directory you specified, along with a file called `members.csv` which you can bulk upload to your group.

** See https://github.com/88lex/sa-guide for further information. Note that sa-guide may not be completely updated, but should provide some help.**




*************************
*************************

THIS IS THE README.MD FOR THE OLD sa-gen-original THAT IS STILL AVAILABLE IN THE REPO

Create up to 100 service accounts for a google project using gcloud SDK

_forked from DashLt at https://gist.github.com/DashLt/4c6ff6e9bde4e9bc4a9ed7066c4efba4_ and

_forked from mc2squared at https://gist.github.com/mc2squared/01c933a8172a26af88285610a0e5af8d_


requires gcloud command line tools

install with ```curl https://sdk.cloud.google.com | bash```
or go to ```https://cloud.google.com/sdk/docs/quickstarts``` to read more and install in non-linux OSes.

max 100 service accounts per project

max 12 projects for a normal gmail account. 
max 50 projects for a paid gsuite account. You can request more project from Google if necessary.

run `gcloud init --console-only` first and select a project for your first batch of 100.
For subsequent batches of 100 you run `gcloud init` again, pick 1, [1] Re-initialize this configuration
then choose the account where your projects/SAs reside. Then choose the next project.

Before running the script: 
Create a folder for your keys

Set your key directory, default is `KEYS_DIR=/opt/sa`. There is no need to change your KEYS_DIR as you 
run more batches and projects, as long as you increment the key numbers appropriately to not overwrite existing keys.

If you want to create more than 100 jsons then increment COUNT for each batch.
For the first batch set `COUNT=1` and `sagen{1..100}` in the script. 
( Note that `sagen` is simply a text prefix for the name that the SA email will be given. You may choose whatever prefix you like.)

For more batches edit and change `COUNT=101` and `sagen{101..200}` in the script. Third batch `COUNT=201` `sagen{201..300}` and so on...

FURTHER NOTES TO THE ABOVE:

In the first pass use the following:

```
KEYS_DIR=/opt/sa
#
# If you want to create more than 100 jsons then increment COUNT for each batch.
# For the first batch COUNT=1. Second batch COUNT=101. Third batch COUNT=201 ...
COUNT=1
for name in sagen{1..101}; do
```

Then in the second pass do the following

```
KEYS_DIR=/opt/sa
#
# If you want to create more than 100 jsons then increment COUNT for each batch.
# For the first batch COUNT=1. Second batch COUNT=101. Third batch COUNT=201 ...
COUNT=101
for name in sagen{101..201}; do
```

Then for the third pass do the following:

```
KEYS_DIR=/opt/sa
#
# If you want to create more than 100 jsons then increment COUNT for each batch.
# For the first batch COUNT=1. Second batch COUNT=101. Third batch COUNT=201 ...
COUNT=201
for name in sagen{201..301}; do
```