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

import base64
import json
import model
import os
import webapp2
from oauth2client import client
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template


def project_logger_as_dict(project_logger):
  project_logger_id = project_logger.key.id()

  return {
      'id': project_logger_id,
      'projectId': project_logger.project.id(),
      'projectName': project_logger.project.get().name,
      'severity': str(project_logger.severity),
      'message': project_logger.message,
      'createdAt': project_logger.created_at.isoformat() + 'Z',
      'updatedAt': project_logger.updated_at.isoformat() + 'Z'
  }

def as_dict(project):
  project_id = project.key.id()
  assets = [{
      'key': str(a),
      'filename': blobstore.get(a).filename
  } for a in project.assets]
  if project.feed:
    feed = {
        'key': str(project.feed),
        'filename': blobstore.get(project.feed).filename
    }
  else:
    feed = None
  return {
      'id': project_id,
      'name': project.name,
      'profileId': project.profile_id,
      'sheetsFeedUrl': project.sheets_feed_url,
      'notes': project.notes,
      'feedUploadUrl':
          blobstore.create_upload_url('/api/projects/' + str(project_id) +
                                      '/feed'),
      'createdAt': project.created_at.isoformat() + 'Z',
      'updatedAt': project.updated_at.isoformat() + 'Z',
      'lastRunAt':
          project.last_run_at.isoformat() + 'Z'
          if project.last_run_at else None,
      'lastCompletedAt':
          project.last_completed_at.isoformat() + 'Z'
          if project.last_completed_at else None,
      'status': str(project.status),
      'assets': assets,
      'feed': feed
  }


class ApiHandler(webapp2.RequestHandler):

  def as_json(self, data):
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write(json.dumps(data))


class SettingsHandler(ApiHandler):

  def get(self):
    settings = model.show_settings()
    self.as_json({
      'username': settings.username,
      'password': settings.password,
      'config': settings.config,
    })

  def put(self):
    data = json.loads(self.request.body)
    settings = model.update_settings(data['username'], data['password'], data['config'])
    self.as_json({
      'username': settings.username,
      'password': settings.password,
      'config': settings.config,
    })


class ProjectsHandler(ApiHandler):

  def get(self):
    cursor = self.request.get('pc')
    projects = model.projects(cursor)
    projects['entities'] = [as_dict(project) for project in projects['entities']]
    self.as_json(projects)


class ProjectHandler(ApiHandler):

  def post(self):
    data = json.loads(self.request.body)
    settings = model.show_settings()
    config = json.loads(settings.config)
    config_web = config.get('web', {})
    client_id = config_web.get('client_id', '')
    client_secret = config_web.get('client_secret', '')

    credentials = client.credentials_from_code(
        client_id,
        client_secret,
        ['https://www.googleapis.com/auth/dfatrafficking'],
        data['code'])
    project = model.create_project(data['name'], data['profileId'],
                                   credentials.to_json())
    self.as_json(as_dict(project))

  def get(self, project_id):
    project_id = int(project_id)
    project = model.show_project(project_id)
    self.as_json(as_dict(project))

  def put(self, project_id):
    project_id = int(project_id)
    data = json.loads(self.request.body)
    project = model.update_project(project_id, data['name'], data['profileId'],
                                   data['feed'], data['assets'],
                                   data['sheetsFeedUrl'], data['notes'])
    self.as_json(as_dict(project))

  def delete(self, project_id):
    project_id = int(project_id)
    model.destroy_project(project_id)


class ProjectStatusHandler(ApiHandler):

  def get(self, project_id):
    project_id = int(project_id)
    project = model.show_project(project_id)
    self.as_json({'status': str(project.status)})


class ProjectLoggersHandler(ApiHandler):

  def get(self, project_id):
    cursor = self.request.get('lc')
    project_id = int(project_id)
    project_loggers = model.project_loggers(project_id, cursor)
    project_loggers['entities'] = [project_logger_as_dict(project_logger) for project_logger in project_loggers['entities']]
    self.as_json(project_loggers)


class ProjectFeedUploadHandler(blobstore_handlers.BlobstoreUploadHandler):

  def post(self, project_id):
    project_id = int(project_id)
    upload = self.get_uploads()[0]
    model.update_project_with_feed(project_id, upload.key())
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write('{}')


class ProjectFeedDownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):

  def get(self, project_id):
    project_id = int(project_id)
    project = model.show_project(project_id)
    project_feed_key = project.feed
    project_feed_info = blobstore.BlobInfo(project.feed)
    if not blobstore.get(project_feed_key):
      self.error(404)
    else:
      self.send_blob(project_feed_info, save_as=True)


class ProjectAssetUploadHandler(blobstore_handlers.BlobstoreUploadHandler):

  def post(self, project_id):
    project_id = int(project_id)
    upload = self.get_uploads()[0]
    model.update_project_with_asset(project_id, upload.key())
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write('{}')


class ProjectAssetUploadUrlHandler(ApiHandler):

  def get(self, project_id):
    upload_url = blobstore.create_upload_url('/api/projects/' + project_id +
                                             '/asset')
    self.as_json({'uploadUrl': upload_url})


class ProjectRunHandler(ApiHandler):

  def post(self, project_id):
    project_id = int(project_id)
    model.start_project_run(project_id)
    self.as_json({})

  def delete(self, project_id):
    project_id = int(project_id)
    model.cancel_project_run(project_id)
    self.as_json({})


def check_auth(auth, stored_username, stored_password):
  encoded_auth = auth[1]
  username_colon_pass = base64.b64decode(encoded_auth)
  username, password = username_colon_pass.split(':')
  return username == stored_username and password == stored_password


class MainHandler(webapp2.RequestHandler):

  def get(self):
    settings = model.show_settings()
    config = json.loads(settings.config)
    client_id = config.get('web', {}).get('client_id', '')

    auth = self.request.authorization
    if auth is None or not check_auth(auth, settings.username, settings.password):
      self.response.status_int = 401
      self.response.headers['WWW-Authenticate'] = 'Basic realm="Login Required"'
      return

    template_values = {
      'CLIENT_ID': client_id,
    }
    path = os.path.join(os.path.dirname(__file__), 'frontend', 'index.html')
    output = template.render(path, template_values)
    self.response.write(output)



app = webapp2.WSGIApplication(
    [
        webapp2.Route(
            r'/', handler=MainHandler, methods=['GET']),
        webapp2.Route(
            r'/api/settings', handler=SettingsHandler, methods=['GET']),
        webapp2.Route(
            r'/api/settings', handler=SettingsHandler, methods=['PUT']),
        webapp2.Route(
            r'/api/projects', handler=ProjectsHandler, methods=['GET']),
        webapp2.Route(
            r'/api/projects', handler=ProjectHandler, methods=['POST']),
        webapp2.Route(
            r'/api/projects/<project_id>',
            handler=ProjectHandler,
            methods=['GET']),
        webapp2.Route(
            r'/api/projects/<project_id>',
            handler=ProjectHandler,
            methods=['PUT']),
        webapp2.Route(
            r'/api/projects/<project_id>',
            handler=ProjectHandler,
            methods=['DELETE']),
        webapp2.Route(
            r'/api/projects/<project_id>/status',
            handler=ProjectStatusHandler,
            methods=['GET']),
        webapp2.Route(
            r'/api/projects/<project_id>/log',
            handler=ProjectLoggersHandler,
            methods=['GET']),
        webapp2.Route(
            r'/api/projects/<project_id>/run',
            handler=ProjectRunHandler,
            methods=['POST']),
        webapp2.Route(
            r'/api/projects/<project_id>/run',
            handler=ProjectRunHandler,
            methods=['DELETE']),
        webapp2.Route(
            r'/api/projects/<project_id>/feed',
            handler=ProjectFeedDownloadHandler,
            methods=['GET']),
        webapp2.Route(
            r'/api/projects/<project_id>/feed',
            handler=ProjectFeedUploadHandler,
            methods=['POST']),
        webapp2.Route(
            r'/api/projects/<project_id>/asset',
            handler=ProjectAssetUploadHandler,
            methods=['POST']),
        webapp2.Route(
            r'/api/projects/<project_id>/asset_upload_url',
            handler=ProjectAssetUploadUrlHandler,
            methods=['GET'])
    ],
    debug=True)
