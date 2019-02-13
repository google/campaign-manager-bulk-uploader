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

from csv import DictReader
from google.appengine.ext import blobstore
import model


class DCMJob(object):

  def __init__(self, project, dcm_dao):
    if not project.feed:
      raise ValueError('A feed is required!')

    if len(project.assets) == 0:
      raise ValueError('Assets are required!')

    self.csv = blobstore.BlobReader(project.feed).read().splitlines()
    self.mappings = {
        'ad_end_date':
            'Ad End Date',
        'ad_hard_cutoff':
            'Ad Hard Cutoff',
        'ad_landing_page_url_suffix':
            'Ad Landing Page URL Suffix',
        'ad_name':
            'Ad Name',
        'ad_priority':
            'Ad Priority',
        'ad_start_date':
            'Ad Start Date',
        'ad_type':
            'Ad Type',
        'ad_click_through_url':
            'Ad Click-Through URL',
        'advertiser_id':
            'Advertiser ID',
        'campaign_default_landing_page_name':
            'Campaign Default Landing Page Name',
        'campaign_default_landing_page_url':
            'Campaign Default Landing Page URL',
        'campaign_end_date':
            'Campaign End Date',
        'campaign_name':
            'Campaign Name',
        'campaign_start_date':
            'Campaign Start Date',
        'creative_backup_image_click_through_url':
            'Creative Backup Image Click-Through URL',
        'creative_backup_image_filename':
            'Creative Backup Image Filename',
        'creative_filename':
            'Creative Filename',
        'creative_id':
            'Creative ID',
        'creative_landing_page_url':
            'Creative Landing Page URL',
        'creative_name':
            'Creative Name',
        'creative_rotation_type':
            'Creative Rotation Type',
        'creative_size':
            'Creative Size',
        'placement_end_date':
            'Placement End Date',
        'placement_name':
            'Placement Name',
        'placement_start_date':
            'Placement Start Date',
        'site_id':
            'Site ID'
    }
    self.project = project
    self.dcm_dao = dcm_dao

  def start(self):
    self.create_campaigns()
    self.create_creatives()
    self.create_placements()
    self.create_ads()

  def create_campaigns(self):
    csv_dict = DictReader(self.csv)
    for row in csv_dict:
      advertiser_id = row[self.mappings['advertiser_id']].strip()
      campaign_name = row[self.mappings['campaign_name']].strip()
      campaign_start_date = row[self.mappings['campaign_start_date']].strip()
      campaign_end_date = row[self.mappings['campaign_end_date']].strip()
      campaign_default_landing_page_name = row[self.mappings[
          'campaign_default_landing_page_name']].strip()
      campaign_default_landing_page_url = row[self.mappings[
          'campaign_default_landing_page_url']].strip()

      if campaign_name not in self.dcm_dao.campaigns:
        logger = model.ProjectLogger(
            message=('Creating campaign "%s"' % campaign_name),
            project=self.project.key,
            severity=model.ProjectLoggerSeverity.INFO)
        logger.put()

        self.dcm_dao.create_campaign(advertiser_id, campaign_name,
                                     campaign_start_date, campaign_end_date,
                                     campaign_default_landing_page_name,
                                     campaign_default_landing_page_url)

  def create_creatives(self):
    default_creatives = []
    nondefault_creatives = []

    csv_dict = DictReader(self.csv)
    for row in csv_dict:
      ad_type = row[self.mappings['ad_type']].strip().lower()
      if ad_type == 'default':
        default_creatives.append(row)
      else:
        nondefault_creatives.append(row)

    all_creatives = default_creatives + nondefault_creatives

    for row in all_creatives:
      campaign_name = row[self.mappings['campaign_name']].strip()
      campaign = self.dcm_dao.get_campaign_from_name(campaign_name)
      creative_name = row[self.mappings['creative_name']].strip()
      ad_type = row[self.mappings['ad_type']].strip().lower()
      advertiser_id = row[self.mappings['advertiser_id']].strip()
      creative_size = row[self.mappings['creative_size']].strip()
      creative_filename = row[self.mappings['creative_filename']].strip()

      if 'tracker' in ad_type:
        continue

      creative_file = None
      if 'track' not in ad_type:
        creative_file = self.asset_to_upload(creative_filename)

      creative_backup_image_filename = None
      creative_backup_image_file = None
      creative_backup_image_click_through_url = None

      asset_type = 'HTML_IMAGE'

      if creative_filename[-4:] == '.zip':
        asset_type = 'HTML'
        creative_backup_image_filename = row[self.mappings[
            'creative_backup_image_filename']].strip()
        creative_backup_image_file = self.asset_to_upload(
            creative_backup_image_filename)
        creative_backup_image_click_through_url = row[self.mappings[
            'creative_backup_image_click_through_url']].strip()

      logger = model.ProjectLogger(
          message=('Creating creative "%s"' % creative_name),
          project=self.project.key,
          severity=model.ProjectLoggerSeverity.INFO)
      logger.put()

      self.dcm_dao.upload_asset(asset_type, creative_name, creative_file,
                                creative_size, advertiser_id, campaign['id'],
                                ad_type, creative_backup_image_file,
                                creative_backup_image_filename,
                                creative_backup_image_click_through_url)

  def create_placements(self):
    csv_dict = DictReader(self.csv)
    for row in csv_dict:
      ad_type = row[self.mappings['ad_type']].strip().lower()
      if ad_type == 'default':
        continue

      campaign_name = row[self.mappings['campaign_name']].strip()
      campaign = self.dcm_dao.get_campaign_from_name(campaign_name)

      if campaign is None:
        raise Exception('Campaign not found.')

      site_id = row[self.mappings['site_id']]
      creative_size = row[self.mappings['creative_size']].strip().lower()
      placement_name = row[self.mappings['placement_name']].strip()

      logger = model.ProjectLogger(
          message=('Creating placement "%s"' % placement_name),
          project=self.project.key,
          severity=model.ProjectLoggerSeverity.INFO)
      logger.put()

      self.dcm_dao.create_placement(placement_name, creative_size, campaign,
                                    site_id)

  def create_ads(self):
    csv_dict = DictReader(self.csv)
    for row in csv_dict:
      ad_type = row[self.mappings['ad_type']].strip().lower()
      if ad_type == 'default':
        continue

      creative_name = row[self.mappings['creative_name']].strip()
      ad_name = row[self.mappings['ad_name']].strip()
      creative_rotation_type = row[self.mappings[
          'creative_rotation_type']].strip().lower()
      creative_landing_page_url = row[self.mappings[
          'creative_landing_page_url']].strip()
      ad_landing_page_url_suffix = row[self.mappings[
          'ad_landing_page_url_suffix']].strip()
      ad_priority = row[self.mappings['ad_priority']].strip()
      ad_hard_cutoff = row[self.mappings['ad_hard_cutoff']].strip().lower()
      ad_start_date = row[self.mappings['ad_start_date']].strip()
      ad_end_date = row[self.mappings['ad_end_date']].strip()
      ad_click_through_url = row[self.mappings['ad_click_through_url']].strip()
      placement_name = row[self.mappings['placement_name']].strip()
      campaign_name = row[self.mappings['campaign_name']].strip()
      campaign = self.dcm_dao.get_campaign_from_name(campaign_name)

      logger = model.ProjectLogger(
          message=('Creating ad "%s"' % ad_name),
          project=self.project.key,
          severity=model.ProjectLoggerSeverity.INFO)
      logger.put()

      self.dcm_dao.create_ad(campaign, creative_name, ad_name, ad_start_date,
                             ad_end_date, ad_priority, ad_hard_cutoff, ad_type,
                             ad_click_through_url, ad_landing_page_url_suffix,
                             creative_landing_page_url, creative_rotation_type,
                             placement_name)

  def asset_to_upload(self, asset_filename):
    asset_key = None
    for asset in self.project.assets:
      if asset_filename.lower() == blobstore.BlobInfo(asset).filename.lower():
        asset_key = asset
        break

    if not asset_key:
      raise ValueError(
          'Feed contains a reference to "%s" that has not yet been uploaded as an asset to this project!'
          % asset_filename)

    return asset_key
