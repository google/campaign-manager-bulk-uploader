# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from apiclient import http
from datetime import datetime
from dateutil import tz
from google.appengine.ext import blobstore
from googleapiclient.discovery import build
from oauth2client.client import Credentials
import httplib2
import time


class DCMDAO(object):

  MAX_RETRIES = 5
  MAX_TIMEOUT = 1800
  API_NAME = 'dfareporting'
  API_VERSION = 'v3.2'

  def __init__(self, project):
    credentials = Credentials.new_from_json(project.credentials)
    authed_http = credentials.authorize(httplib2.Http())

    self.service = build(self.API_NAME, self.API_VERSION, http=authed_http)
    self.profile_id = project.profile_id
    self.creatives = {}
    self.placements = {}
    self.campaigns = {}
    self.ads = {}

  def get_campaign_from_name(self, campaign_name, retry_count=0):
    if campaign_name in self.campaigns:
      return self.campaigns[campaign_name]

    campaign = self.get_campaign(campaign_name)
    if campaign is not None:
      self.campaigns[campaign_name] = campaign
      return self.campaigns[campaign_name]

    return None

  def get_campaign(self, campaign_name, retry_count=0):
    try:
      response = self.service.campaigns().list(
          profileId=self.profile_id, searchString=campaign_name).execute()

      if 'campaigns' in response:
        for campaign in response['campaigns']:
          if campaign['name'] == campaign_name:
            return campaign

      return None
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.get_campaign(campaign_name, retry_count + 1)
      else:
        raise

  def create_campaign(self,
                      advertiser_id,
                      campaign_name,
                      start_date,
                      end_date,
                      default_landing_page_name,
                      default_landing_page_url,
                      retry_count=0):
    try:
      campaign = self.get_campaign(campaign_name)

      if campaign is not None:
        raise Exception(
            'A campaign called "%s" already exists!' % campaign_name)
      else:
        campaign = {
            'name': campaign_name,
            'advertiserId': advertiser_id,
            'archived': False,
            'startDate': start_date,
            'endDate': end_date
        }

        advertiser_landing_page = {
            'advertiserId': advertiser_id,
            'name': default_landing_page_name,
            'url': default_landing_page_url
        }

        default_landing_page = self.service.advertiserLandingPages().insert(
            profileId=self.profile_id, body=advertiser_landing_page).execute()

        campaign['defaultLandingPageId'] = default_landing_page['id']

        self.campaigns[campaign_name] = self.service.campaigns().insert(
            profileId=self.profile_id, body=campaign).execute()
        return self.campaigns[campaign_name]
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.create_campaign(advertiser_id, campaign_name, start_date,
                                    end_date, default_landing_page_name,
                                    default_landing_page_url, retry_count + 1)
      else:
        raise

  def get_sizes(self, width, height, retry_count=0):
    try:
      sizes = self.service.sizes().list(
          profileId=self.profile_id, height=height, width=width).execute()
      return sizes
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.get_sizes(width, height, retry_count + 1)
      else:
        raise

  def get_creative(self, creative_id, retry_count=0):
    try:
      return self.service.creatives().get(
          profileId=self.profile_id, id=creative_id)
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.get_creative(creative_id, retry_count + 1)
      else:
        raise

  def create_ad(self,
                campaign,
                creative_name,
                ad_name,
                ad_start_date,
                ad_end_date,
                priority,
                hard_cutoff,
                ad_type,
                click_through_url,
                landing_page_url_suffix,
                creative_landing_page_url,
                creative_rotation_type,
                placement_name,
                retry_count=0,
                max_timeout=MAX_TIMEOUT):
    try:
      creative_assignment = {'active': True}

      if 'tracker' not in ad_type:
        creative = self.creatives[creative_name]
        creative = self.get_creative(creative['id']).execute()
        timeout = 0

        while not creative['active'] and timeout < max_timeout:
          timeout += 30
          time.sleep(timeout)
          creative = self.get_creative(creative['id']).execute()

        if not creative['active']:
          raise Exception(
              'A creative with ID "%s" was not found after %d seconds!',
              creative['id'], timeout)

        creative_assignment['creativeId'] = creative['id']

      if creative_landing_page_url:
        creative_assignment['clickThroughUrl'] = {
            'defaultLandingPage': False,
            'customClickThroughUrl': creative_landing_page_url
        }
      else:
        creative_assignment['clickThroughUrl'] = {'defaultLandingPage': True}

      if ad_name in self.ads:
        creative_assignments = self.ads[ad_name]['creativeRotation'][
            'creativeAssignments']
        creative_assignments.append(creative_assignment)

        creative_update = {
            'creativeRotation': {
                'creativeAssignments': creative_assignments
            }
        }

        existing_ad_id = self.ads[ad_name]['id']
        response = self.service.ads().patch(
            profileId=self.profile_id, id=existing_ad_id,
            body=creative_update).execute()
        self.ads[ad_name] = response
        return response

      creative_rotation = {'creativeAssignments': [creative_assignment]}

      if creative_rotation_type == 'sequential':
        creative_rotation['type'] = 'CREATIVE_ROTATION_TYPE_SEQUENTIAL'
      elif creative_rotation_type == 'even':
        creative_rotation['type'] = 'CREATIVE_ROTATION_TYPE_RANDOM'
        creative_rotation['weightCalculationStrategy'] = 'WEIGHT_STRATEGY_EQUAL'
      elif creative_rotation_type == 'click-through rate':
        creative_rotation['type'] = 'CREATIVE_ROTATION_TYPE_RANDOM'
        creative_rotation[
            'weightCalculationStrategy'] = 'WEIGHT_STRATEGY_HIGHEST_CTR'
      elif creative_rotation_type == 'optimized':
        creative_rotation['type'] = 'CREATIVE_ROTATION_TYPE_RANDOM'
        creative_rotation[
            'weightCalculationStrategy'] = 'WEIGHT_STRATEGY_OPTIMIZED'
      elif creative_rotation_type == 'custom':
        creative_rotation['type'] = 'CREATIVE_ROTATION_TYPE_RANDOM'
        creative_rotation[
            'weightCalculationStrategy'] = 'WEIGHT_STRATEGY_CUSTOM'
      else:
        creative_rotation['type'] = 'CREATIVE_ROTATION_TYPE_RANDOM'
        creative_rotation[
            'weightCalculationStrategy'] = 'WEIGHT_STRATEGY_OPTIMIZED'

      ad_priority_formatted = '01'
      if priority:
        ad_priority_formatted = priority.zfill(2)

      hard_cutoff_boolean = False
      if hard_cutoff == 'yes' or hard_cutoff == 'true':
        hard_cutoff_boolean = True

      delivery_schedule = {
          'impressionRatio': '1',
          'priority': ('AD_PRIORITY_%s' % ad_priority_formatted),
          'hardCutoff': hard_cutoff_boolean
      }

      placement_assignments = [{
          'active': True,
          'placementId': self.placements[placement_name]['id'],
      }]

      ad = {
          'active': True,
          'campaignId': campaign['id'],
          'creativeRotation': creative_rotation,
          'deliverySchedule': delivery_schedule,
          'name': ad_name,
          'placementAssignments': placement_assignments,
          'type': 'AD_SERVING_STANDARD_AD'
      }

      if 'tracking' in ad_type:
        ad['type'] = 'AD_SERVING_TRACKING'

      if 'tracker' in ad_type:
        ad['type'] = 'AD_SERVING_CLICK_TRACKER'

        if 'static' in ad_type:
          ad['active'] = False

        ad['dynamicClickTracker'] = 'dynamic' in ad_type

        if click_through_url:
          ad['clickThroughUrl'] = {
              'defaultLandingPage': False,
              'customClickThroughUrl': click_through_url
          }
        else:
          ad['clickThroughUrl'] = {'defaultLandingPage': True}

      if ad_start_date:
        unconverted_start_time = datetime.strptime(
            '%s 23:59:59' % ad_start_date, '%Y-%m-%d %H:%M:%S')
      else:
        unconverted_start_time = datetime.strptime(
            '%s 23:59:59' % campaign['startDate'], '%Y-%m-%d %H:%M:%S')

      unconverted_start_time = unconverted_start_time.replace(
          tzinfo=tz.gettz('America/New_York'))
      converted_start_time = unconverted_start_time.astimezone(tz.gettz('UTC'))

      ad['startTime'] = converted_start_time.isoformat()

      if ad_end_date:
        unconverted_end_time = datetime.strptime('%s 00:00:00' % ad_end_date,
                                                 '%Y-%m-%d %H:%M:%S')
      else:
        unconverted_end_time = datetime.strptime(
            '%s 00:00:00' % campaign['endDate'], '%Y-%m-%d %H:%M:%S')

      unconverted_end_time = unconverted_end_time.replace(
          tzinfo=tz.gettz('America/New_York'))
      converted_end_time = unconverted_end_time.astimezone(tz.gettz('UTC'))

      ad['endTime'] = converted_end_time.isoformat()

      if landing_page_url_suffix:
        ad['clickThroughUrlSuffixProperties'] = {
            'clickThroughUrlSuffix': landing_page_url_suffix,
            'overrideInheritedSuffix': True
        }

      self.ads[ad_name] = self.service.ads().insert(
          profileId=self.profile_id, body=ad).execute()
      return self.ads[ad_name]
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.create_ad(campaign, creative_name, ad_name, ad_start_date,
                              ad_end_date, priority, hard_cutoff, ad_type,
                              click_through_url, landing_page_url_suffix,
                              creative_landing_page_url, creative_rotation_type,
                              retry_count + 1)
      else:
        raise

  def create_placement(self,
                       placement_name,
                       asset_size,
                       campaign,
                       site_id,
                       retry_count=0):
    try:
      if placement_name in self.placements:
        return self.placements[placement_name]

      placement = {
          'name': placement_name,
          'campaignId': campaign['id'],
          'siteId': site_id,
          'paymentSource': 'PLACEMENT_AGENCY_PAID',
          'pricingSchedule': {
              'startDate': campaign['startDate'],
              'endDate': campaign['endDate'],
              'pricingType': 'PRICING_TYPE_CPM'
          }
      }

      placement['compatibility'] = 'DISPLAY'

      width, height = asset_size.split('x')
      sizes = self.get_sizes(int(width), int(height))['sizes']
      if sizes:
        placement['size'] = {'id': sizes[0]['id']}
      else:
        placement['size'] = {'width': int(width), 'height': int(height)}

      placement['tagFormats'] = [
          'PLACEMENT_TAG_STANDARD', 'PLACEMENT_TAG_JAVASCRIPT',
          'PLACEMENT_TAG_IFRAME_JAVASCRIPT', 'PLACEMENT_TAG_IFRAME_ILAYER',
          'PLACEMENT_TAG_INTERNAL_REDIRECT', 'PLACEMENT_TAG_TRACKING',
          'PLACEMENT_TAG_TRACKING_IFRAME', 'PLACEMENT_TAG_TRACKING_JAVASCRIPT'
      ]

      self.placements[placement_name] = self.service.placements().insert(
          profileId=self.profile_id, body=placement).execute()
      return self.placements[placement_name]
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.create_placement(placement_name, asset_size, campaign,
                                     site_id, retry_count + 1)
      else:
        raise

  def upload_creative_asset(self,
                            asset_type,
                            filename,
                            asset_key,
                            advertiser_id,
                            retry_count=0):
    try:
      creative_asset = {
          'assetIdentifier': {
              'name': filename,
              'type': asset_type
          }
      }

      asset_file = blobstore.BlobReader(asset_key)
      mimetype = blobstore.BlobInfo(asset_key).content_type
      media = http.MediaIoBaseUpload(
          asset_file, mimetype=mimetype, resumable=False)

      return self.service.creativeAssets().insert(
          advertiserId=advertiser_id,
          profileId=self.profile_id,
          media_body=media,
          body=creative_asset).execute()
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.upload_creative_asset(asset_type, filename, asset_key,
                                          advertiser_id, retry_count + 1)
      else:
        raise

  def insert_creative(self, creative, retry_count=0):
    try:
      return self.service.creatives().insert(
          profileId=self.profile_id, body=creative).execute()
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.insert_creative(creative, retry_count + 1)
      else:
        raise

  def insert_creative_associations(self,
                                   campaign_id,
                                   association,
                                   retry_count=0):
    try:
      self.service.campaignCreativeAssociations().insert(
          profileId=self.profile_id, campaignId=campaign_id,
          body=association).execute()
    except http.HttpError, e:
      if e.resp.status in [403, 500, 503] and retry_count < self.MAX_RETRIES:
        return self.insert_creative_associations(campaign_id, association,
                                                 retry_count + 1)
      else:
        raise

  def upload_asset(self,
                   asset_type,
                   asset_name,
                   asset_file,
                   asset_size,
                   advertiser_id,
                   campaign_id,
                   ad_type,
                   backup_asset_file=None,
                   backup_asset_name=None,
                   backup_url=None):
    creative = {
        'advertiserId': advertiser_id,
        'name': asset_name,
        'active': True
    }

    if 'track' in ad_type:
      creative['type'] = 'TRACKING_TEXT'
    else:
      creative['type'] = 'DISPLAY'

      filename = blobstore.BlobInfo(asset_file).filename

      response = self.upload_creative_asset(asset_type, filename, asset_file,
                                            advertiser_id)

      creative['creativeAssets'] = [{
          'assetIdentifier': response['assetIdentifier'],
          'role': 'PRIMARY'
      }]

      if filename[-4:] == '.zip':
        backup_response = self.upload_creative_asset(
            'HTML_IMAGE', backup_asset_name, backup_asset_file, advertiser_id)
        backup_creative_asset_id = backup_response['assetIdentifier']

        creative['creativeAssets'].append({
            'assetIdentifier': backup_creative_asset_id,
            'role': 'BACKUP_IMAGE'
        })

        creative['backupImageClickThroughUrl'] = {
            'customClickThroughUrl': backup_url
        }
        creative['backupImageReportingLabel'] = 'backup_image_exit'
        creative['backupImageTargetWindow'] = {
            'targetWindowOption': 'NEW_WINDOW'
        }

        creative['clickTags'] = [{
            'eventName': 'exit',
            'name': 'clickTag',
            'clickThroughUrl': {
                'customClickThroughUrl': backup_url
            }
        }]

      width, height = asset_size.strip().lower().split('x')
      sizes = self.get_sizes(int(width), int(height))['sizes']
      if sizes:
        creative['size'] = {'id': sizes[0]['id']}
      else:
        creative['size'] = {'width': int(width), 'height': int(height)}

    result = self.insert_creative(creative)
    self.creatives[asset_name] = result

    association = {'creativeId': result['id']}

    self.insert_creative_associations(campaign_id, association)
    return self.creatives[asset_name]
