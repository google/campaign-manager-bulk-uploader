#!/bin/sh

###########################################################################
#
#  Copyright 2018 Google Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
###########################################################################

read -p "$(tput setaf 3)Enter your Project ID:$(tput sgr 0) "

gcloud config set project $REPLY

echo "Deploying to App Engine..."

pip install -t lib -r requirements.txt --upgrade
gcloud app deploy --project=$REPLY
gcloud datastore indexes create index.yaml --project=$REPLY

echo "Complete!"

gcloud app browse --project=$REPLY
