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

echo "Installing dependencies..."
pip install --no-cache-dir --upgrade --quiet --target lib --requirement requirements.txt
echo "Done."
echo ""

echo "Deploying to App Engine..."
gcloud app deploy --project=$1
echo "Done."
echo ""

echo "Writing indexes to App Engine..."
gcloud datastore indexes create index.yaml --project=$1
echo "Done."
echo ""

gcloud app browse --project=$1
