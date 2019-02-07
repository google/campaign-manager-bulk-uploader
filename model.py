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

from dcm_dao import DCMDAO
from dcm_job import DCMJob
from google.appengine.ext import blobstore
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
from google.appengine.datastore.datastore_query import Cursor
from protorpc import messages
import datetime
import time

PER_PAGE = 10


class Settings(ndb.Model):
  username = ndb.StringProperty()
  password = ndb.StringProperty()
  config = ndb.JsonProperty()
  created_at = ndb.DateTimeProperty(auto_now_add=True)
  updated_at = ndb.DateTimeProperty(auto_now_add=True)


class ProjectLoggerSeverity(messages.Enum):
  FATAL = 111
  ERROR = 222
  WARNING = 333
  INFO = 444
  DEBUG = 555
  TRACE = 666


class ProjectLogger(ndb.Model):
  project = ndb.KeyProperty()
  message = ndb.TextProperty()
  severity = msgprop.EnumProperty(
      ProjectLoggerSeverity, required=True, default=ProjectLoggerSeverity.INFO)
  created_at = ndb.DateTimeProperty(auto_now_add=True)
  updated_at = ndb.DateTimeProperty(auto_now_add=True)


class ProjectStatus(messages.Enum):
  INITIALIZED = 111
  RUNNING = 333
  CANCELLED = 444
  ERROR = 666
  COMPLETED = 999


class Project(ndb.Model):
  name = ndb.StringProperty()
  credentials = ndb.JsonProperty()
  profile_id = ndb.StringProperty()
  notes = ndb.TextProperty()
  status = msgprop.EnumProperty(
      ProjectStatus, required=True, default=ProjectStatus.INITIALIZED)
  feed = ndb.BlobKeyProperty()
  assets = ndb.BlobKeyProperty(repeated=True)
  created_at = ndb.DateTimeProperty(auto_now_add=True)
  updated_at = ndb.DateTimeProperty(auto_now_add=True)
  last_run_at = ndb.DateTimeProperty()
  last_completed_at = ndb.DateTimeProperty()


def show_settings():
  settings = Settings.get_by_id('settings')
  if not settings:
    settings = Settings(
        id='settings', username='admin', password='admin', config='{}')
    settings.put()
  return settings


def update_settings(username, password, config):
  key = ndb.Key(Settings, 'settings')
  settings = key.get()
  settings.username = username
  settings.password = password
  settings.config = config
  settings.updated_at = datetime.datetime.utcnow()
  settings.put()
  return settings


def projects(bookmark_cursor=None):
  cursor = None

  if bookmark_cursor:
    cursor = Cursor(urlsafe=bookmark_cursor)

  query = Project.query()

  next_query = query.order(-Project.updated_at)
  previous_query = query.order(Project.updated_at)

  entities, next_cursor, has_next = next_query.fetch_page(
      PER_PAGE, start_cursor=cursor)

  if next_cursor:
    next_cursor = next_cursor.urlsafe()

  has_previous = False
  previous_cursor = None
  if cursor:
    previous_cursor = cursor.reversed()
    previous_entities, previous_cursor, has_previous = previous_query.fetch_page(
        PER_PAGE, start_cursor=previous_cursor)

  if previous_cursor:
    has_previous = True
    previous_cursor = previous_cursor.urlsafe()

  return {
      'entities': entities,
      'nextCursor': next_cursor,
      'hasNext': has_next,
      'previousCursor': previous_cursor,
      'hasPrevious': has_previous
  }


def show_project(project_id):
  return Project.get_by_id(project_id, use_cache=False, use_memcache=False)


def create_project(name, profile_id, credentials):
  project = Project(name=name, profile_id=profile_id, credentials=credentials)
  project.put()

  logger = ProjectLogger(
      message='Created.',
      project=project.key,
      severity=ProjectLoggerSeverity.INFO)
  logger.put()

  return project


def update_project(project_id, name, profile_id, feed, assets, notes=''):
  key = ndb.Key(Project, project_id)
  project = key.get()
  project.name = name
  project.profile_id = profile_id
  project.notes = notes
  project.feed = blobstore.BlobKey(feed['key']) if feed else None
  project.assets = [blobstore.BlobKey(a['key']) for a in assets]
  project.updated_at = datetime.datetime.utcnow()
  project.put()

  logger = ProjectLogger(
      message='Updated.', project=key, severity=ProjectLoggerSeverity.INFO)
  logger.put()

  return project


def update_project_with_feed(project_id, feed):
  key = ndb.Key(Project, project_id)
  project = key.get()
  project.feed = feed
  project.updated_at = datetime.datetime.utcnow()
  project.put()

  logger = ProjectLogger(
      message='Feed added.', project=key, severity=ProjectLoggerSeverity.INFO)
  logger.put()

  return project


def update_project_with_asset(project_id, asset):
  key = ndb.Key(Project, project_id)
  project = key.get()
  project.assets.append(asset)  # TODO: Overwrite if filename already exists.
  project.updated_at = datetime.datetime.utcnow()
  project.put()

  logger = ProjectLogger(
      message='Asset added.', project=key, severity=ProjectLoggerSeverity.INFO)
  logger.put()

  return project


def start_project_run(project_id):
  key = ndb.Key(Project, project_id)
  deferred.defer(project_run, key)

  logger = ProjectLogger(
      message='Added to deferred queue.',
      project=key,
      severity=ProjectLoggerSeverity.INFO)
  logger.put()

  return


def project_run(key):
  project = key.get()

  project.status = ProjectStatus.RUNNING
  project.last_run_at = datetime.datetime.utcnow()
  project.updated_at = datetime.datetime.utcnow()
  project.put()

  run_logger = ProjectLogger(
      message='Running.', project=key, severity=ProjectLoggerSeverity.INFO)
  run_logger.put()

  try:
    dcm_dao = DCMDAO(project)
    dcm_job = DCMJob(project, dcm_dao)
    dcm_job.start()
  except Exception, e:
    project.status = ProjectStatus.ERROR
    project.last_completed_at = datetime.datetime.utcnow()
    project.updated_at = datetime.datetime.utcnow()
    project.put()

    error_logger = ProjectLogger(
        message=str(e), project=key, severity=ProjectLoggerSeverity.ERROR)
    error_logger.put()

    raise deferred.PermanentTaskFailure, e

  project.status = ProjectStatus.COMPLETED
  project.last_completed_at = datetime.datetime.utcnow()
  project.updated_at = datetime.datetime.utcnow()
  project.put()

  completed_logger = ProjectLogger(
      message='Completed.', project=key, severity=ProjectLoggerSeverity.INFO)
  completed_logger.put()


def cancel_project_run(project_id):
  key = ndb.Key(Project, project_id)
  project = key.get()
  project.status = ProjectStatus.CANCELLED
  project.updated_at = datetime.datetime.utcnow()
  project.put()

  logger = ProjectLogger(
      message='Cancelled.', project=key, severity=ProjectLoggerSeverity.WARNING)
  logger.put()

  return


def destroy_project(project_id):
  key = ndb.Key(Project, project_id)
  key.delete()

  ndb.delete_multi(
      ProjectLogger.query(ProjectLogger.project == key).fetch(keys_only=True))


def project_loggers(project_id, bookmark_cursor):
  key = ndb.Key(Project, project_id)

  cursor = None

  if bookmark_cursor:
    cursor = Cursor(urlsafe=bookmark_cursor)

  query = ProjectLogger.query(ProjectLogger.project == key)

  next_query = query.order(-ProjectLogger.updated_at)
  previous_query = query.order(ProjectLogger.updated_at)

  entities, next_cursor, has_next = next_query.fetch_page(
      PER_PAGE, start_cursor=cursor)

  if next_cursor:
    next_cursor = next_cursor.urlsafe()

  has_previous = False
  previous_cursor = None
  if cursor:
    previous_cursor = cursor.reversed()
    previous_entities, previous_cursor, has_previous = previous_query.fetch_page(
        PER_PAGE, start_cursor=previous_cursor)

  if previous_cursor:
    has_previous = True
    previous_cursor = previous_cursor.urlsafe()

  return {
      'entities': entities,
      'nextCursor': next_cursor,
      'hasNext': has_next,
      'previousCursor': previous_cursor,
      'hasPrevious': has_previous
  }
