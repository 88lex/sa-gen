# sa-gen

Create up to 100 service accounts for a google project using gcloud SDK

_forked from DashLt at https://gist.github.com/DashLt/4c6ff6e9bde4e9bc4a9ed7066c4efba4_ and

_forked from mc2squared at https://gist.github.com/mc2squared/01c933a8172a26af88285610a0e5af8d_


**requires gcloud command line tools**
install with ```curl https://sdk.cloud.google.com | bash```
or go to ```https://cloud.google.com/sdk/docs/quickstarts``` to read more and install in non-linux OSes.

max 100 service accounts per project

max 12 projects for a normal gmail account. 
max 50 projects for a paid gsuite account. You can request more project from Google if necessary.

run `gcloud init --console-only` first and select a project for your first batch of 100.
For subsequent batches of 100 you run `gcloud init` again, pick 1, [1] Re-initialize this configuration
then choose the account where your projects/SAs reside. Then choose the next project.

Before running the script: 
Create a folder for your keys before running the script

Set your key directory, default is `KEYS_DIR=/opt/sa`. There is no need to change your KEYS_DIR as you 
run more batches and projects, as long as you increment the key numbers appropriately to not overwrite existing keys.

If you want to create more than 100 jsons then increment COUNT for each batch.
For the first batch set COUNT=1 and sagen{1..100} in the script. 

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