// Copyright 2019 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use strict";

var App = angular.module("App", [
  "ngRoute",
  "ngMaterial",
  "ngMessages",
  "angularFileUpload"
]);

App.config(function($routeProvider) {
  $routeProvider.when("/settings", {
    controller: "SettingsController",
    templateUrl: "/partials/settings.html",
    resolve: {
      settings: function($rootScope, $http, $q, $mdToast) {
        $mdToast.show($mdToast.simple().textContent("Loading..."));
        var deferred = $q.defer();
        $http.get("/api/settings").then(function(response) {
          $mdToast.hide();
          deferred.resolve(response.data);
        });
        return deferred.promise;
      }
    }
  });

  $routeProvider.when("/projects/", {
    controller: "ProjectsController",
    templateUrl: "/partials/projects/index.html",
    resolve: {
      projects: function($rootScope, $http, $q, $mdToast, $route) {
        $mdToast.show($mdToast.simple().textContent("Loading..."));
        var deferred = $q.defer();
        var cursor = $route.current.params.pc;
        $http
          .get("/api/projects", { params: { pc: cursor } })
          .then(function(response) {
            $mdToast.hide();
            deferred.resolve(response.data);
          });
        return deferred.promise;
      }
    }
  });

  $routeProvider.when("/projects/new", {
    controller: "NewProjectController",
    templateUrl: "/partials/projects/new.html"
  });

  $routeProvider.when("/projects/:id/edit", {
    controller: "EditProjectController",
    templateUrl: "/partials/projects/edit.html",
    resolve: {
      project: function($http, $q, $mdToast, $route) {
        $mdToast.show($mdToast.simple().textContent("Loading..."));
        var deferred = $q.defer();
        $http
          .get("/api/projects/" + $route.current.params.id)
          .then(function(response) {
            $mdToast.hide();
            deferred.resolve(response.data);
          });
        return deferred.promise;
      }
    }
  });

  $routeProvider.when("/projects/:id/log", {
    controller: "LogProjectController",
    templateUrl: "/partials/projects/log.html",
    resolve: {
      projectLoggers: function($http, $q, $mdToast, $route) {
        $mdToast.show($mdToast.simple().textContent("Loading..."));
        var deferred = $q.defer();
        var cursor = $route.current.params.lc;
        $http
          .get("/api/projects/" + $route.current.params.id + "/log", {
            params: { lc: cursor }
          })
          .then(function(response) {
            $mdToast.hide();
            deferred.resolve(response.data);
          });
        return deferred.promise;
      }
    }
  });

  $routeProvider.otherwise({
    redirectTo: "/projects/"
  });
});

App.controller("AppController", function($scope, $location) {
  $scope.new = function() {
    $location.path("/projects/new");
  };

  $scope.settings = function() {
    $location.path("/settings");
  };
});

App.controller("SettingsController", function(
  $scope,
  $rootScope,
  $window,
  $http,
  $location,
  $mdToast,
  settings
) {
  $scope.settings = settings;
  $scope.clonedSettings = angular.copy($scope.settings);

  $scope.back = function() {
    $window.history.back();
  };

  $scope.save = function() {
    $mdToast.show($mdToast.simple().textContent("Saving..."));
    $http.put("/api/settings", $scope.clonedSettings).then(function(response) {
      $mdToast.hide().then(function() {
        location.reload();
      });
    });
  };
});

App.controller("ProjectsController", function(
  $scope,
  $route,
  $rootScope,
  $http,
  $location,
  $mdToast,
  projects
) {
  $scope.projects = projects["entities"];
  $scope.hasPrevious = projects["hasPrevious"];
  $scope.hasNext = projects["hasNext"];
  $scope.previousCursor = projects["previousCursor"];
  $scope.nextCursor = projects["nextCursor"];

  $scope.previous = function() {
    $location.search("pc", $scope.previousCursor);
  };

  $scope.next = function() {
    $location.search("pc", $scope.nextCursor);
  };

  $scope.edit = function(project) {
    $location.path("/projects/" + project.id + "/edit");
  };

  $scope.delete = function(project) {
    $mdToast.show(
      $mdToast.simple().textContent("Deleting project " + project.id + "...")
    );
    $http.delete("/api/projects/" + project.id).then(function(response) {
      for (var i = 0; i < $scope.projects.length; i++) {
        if ($scope.projects[i].id == project.id) {
          $scope.projects.splice(i, 1);
          break;
        }
      }
      $mdToast.hide();
    });
  };
});

App.controller("NewProjectController", function(
  $scope,
  $rootScope,
  $http,
  $location,
  $mdToast
) {
  $scope.save = function() {
    var project = {
      name: $scope.name,
      profileId: $scope.profileId
    };

    $mdToast.show($mdToast.simple().textContent("Saving..."));

    gapi.load("auth2", function() {
      var auth2 = gapi.auth2.init({
        clientId: BulkUploader.CLIENT_ID,
        discoveryDocs: [
          "https://www.googleapis.com/discovery/v1/apis/drive/v3/rest"
        ],
        scope:
          "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/dfatrafficking"
      });

      auth2.grantOfflineAccess().then(function(result) {
        if (result["error"]) {
          $mdToast.show($mdToast.simple().textContent(result["error"]));
        } else {
          project["code"] = result["code"];
          $http.post("/api/projects", project).then(
            function(response) {
              $mdToast.hide().then(function() {
                $location.path("/projects/" + response.data.id + "/edit");
              });
            },
            function(failure) {
              $mdToast.show(
                $mdToast
                  .simple()
                  .textContent("Something went wrong! Check your settings.")
              );
            }
          );
        }
      });
    });
  };
});

App.controller("EditProjectController", function(
  $scope,
  $route,
  $window,
  $rootScope,
  $http,
  $routeParams,
  $location,
  $timeout,
  $mdToast,
  $mdDialog,
  FileUploader,
  project
) {
  $scope.project = project;
  $scope.clonedProject = angular.copy($scope.project);
  $scope.retries = 0;

  var MAX_RETRIES = 500;
  var RETRY_TIMEOUT = 5000;

  var checkStatus = function() {
    $scope.retries = $scope.retries + 1;

    $http
      .get("/api/projects/" + $scope.project.id + "/status")
      .then(function(response) {
        $scope.status = response.data.status;

        if ($scope.retries < MAX_RETRIES) {
          nextLoad();
        }
      });
  };

  var loadPromise;

  var cancelNextLoad = function() {
    $timeout.cancel(loadPromise);
  };

  var nextLoad = function() {
    cancelNextLoad();
    loadPromise = $timeout(checkStatus, RETRY_TIMEOUT);
  };

  checkStatus();

  $scope.$on("$destroy", function() {
    cancelNextLoad();
  });

  $scope.feedUploader = new FileUploader({
    autoUpload: true,
    removeAfterUpload: true,
    queueLimit: 1,
    url: $scope.project.feedUploadUrl
  });

  $scope.feedUploader.filters.push({
    name: "csvFilter",
    fn: function(item, options) {
      if (item.type == "text/csv") {
        return true;
      } else {
        return false;
      }
    }
  });

  $scope.feedUploader.onWhenAddingFileFailed = function(item, filter, options) {
    if (filter.name == "csvFilter") {
      $mdToast.show(
        $mdToast.simple().textContent("The feed needs to be a CSV!")
      );
    }
  };

  $scope.feedUploader.onCompleteAll = function() {
    $route.reload();
  };

  $scope.assetsUploader = new FileUploader({
    autoUpload: true,
    removeAfterUpload: true
  });

  $scope.originalAssetsUploadItemFn = $scope.assetsUploader.uploadItem;

  $scope.assetsUploader.uploadItem = function() {
    var t = this;
    var args = arguments;
    $http
      .get("/api/projects/" + $scope.project.id + "/asset_upload_url")
      .then(function(response) {
        $scope.assetsUploader.onBeforeUploadItem = function(item) {
          item.url = response.data.uploadUrl;
        };
      })
      .then(function() {
        $scope.originalAssetsUploadItemFn.apply(t, args);
      });
  };

  $scope.assetsUploader.onCompleteAll = function() {
    $route.reload();
  };

  $scope.startRun = function() {
    $scope.retries = 0;
    $http
      .post("/api/projects/" + $scope.project.id + "/run")
      .then(function(response) {
        $scope.status = "RUNNING";
        checkStatus();

        $mdToast
          .show(
            $mdToast
              .simple()
              .textContent("Running...")
              .action("Cancel")
              .highlightAction(true)
          )
          .then(function(response) {
            if (response == "ok") {
              $scope.cancelRun();
            }
          });
      });
  };

  $scope.cancelRun = function() {
    $http
      .delete("/api/projects/" + $scope.project.id + "/run")
      .then(function(response) {
        checkStatus();

        $mdToast.show($mdToast.simple().textContent("Cancelling..."));
      });
  };

  $scope.downloadFeed = function() {
    if ($scope.clonedProject.feed) {
      $window.open("/api/projects/" + $scope.project.id + "/feed", "_blank");
    }
  };

  $scope.removeFeed = function() {
    $scope.clonedProject.feed = "";
    $scope.update();
  };

  $scope.removeAsset = function(asset) {
    for (var i = 0; i < $scope.clonedProject.assets.length; i++) {
      if ($scope.clonedProject.assets[i]["key"] == asset["key"]) {
        $scope.clonedProject.assets.splice(i, 1);
        break;
      }
    }

    $scope.update();
  };

  $scope.showSheetsDialog = function($event) {
    $event.preventDefault();

    var dialog = $mdDialog
      .prompt()
      .title("Google Sheet URL")
      .textContent(
        "Please enter the URL of the Google Sheet you would like to import."
      )
      .placeholder("Google Sheet URL")
      .ariaLabel("Google Sheet URL")
      .targetEvent($event)
      .initialValue($scope.clonedProject.sheetsFeedUrl)
      .required(true)
      .ok("Import")
      .cancel("Cancel");

    $mdDialog.show(dialog).then(
      function(result) {
        var urlMatch = result
          .trim()
          .match(/^https?:\/\/.*?.google.com\/.*\/d\/(.*?)\//);

        if (urlMatch) {
          var sheetId = urlMatch[1];

          gapi.load("client:auth2", function() {
            gapi.client
              .init({
                clientId: BulkUploader.CLIENT_ID,
                discoveryDocs: [
                  "https://www.googleapis.com/discovery/v1/apis/drive/v3/rest"
                ],
                scope:
                  "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/dfatrafficking"
              })
              .then(function() {
                gapi.auth2
                  .getAuthInstance()
                  .signIn()
                  .then(function() {
                    gapi.client.load("drive", "v3", function() {
                      gapi.client.drive.files
                        .export({
                          fileId: sheetId,
                          mimeType: "text/csv"
                        })
                        .then(
                          function(response) {
                            var file = new File(
                              response.body.split("\n"),
                              "feed.csv",
                              { type: "text/csv" }
                            );
                            $scope.feedUploader.addToQueue(file);
                            $scope.clonedProject.sheetsFeedUrl = result;
                            $scope.update();
                          },
                          function(response) {
                            $mdToast.show(
                              $mdToast
                                .simple()
                                .textContent(response.result.error.message)
                            );
                          }
                        );
                    });
                  });
              });
          });
        } else {
          $mdToast.show(
            $mdToast
              .simple()
              .textContent("Oops! That URL doesn't look right. Try another.")
          );
        }
      },
      function() {
        // Do nothing.
      }
    );
  };

  $scope.update = function() {
    $mdToast.show($mdToast.simple().textContent("Updating..."));
    $http
      .put("/api/projects/" + $scope.project.id, $scope.clonedProject)
      .then(function(response) {
        $mdToast.hide().then(function() {
          $route.reload();
        });
      });
  };

  $scope.log = function() {
    $location.path("/projects/" + project.id + "/log");
  };

  $scope.sdf = function() {
    // TODO: Implement SDF generator.
  };
});

App.controller("LogProjectController", function(
  $scope,
  $route,
  $http,
  $timeout,
  $location,
  projectLoggers
) {
  $scope.projectLoggers = projectLoggers["entities"];
  $scope.projectName = $scope.projectLoggers[0].projectName;
  $scope.projectId = $scope.projectLoggers[0].projectId;
  $scope.hasPrevious = projectLoggers["hasPrevious"];
  $scope.hasNext = projectLoggers["hasNext"];
  $scope.previousCursor = projectLoggers["previousCursor"];
  $scope.nextCursor = projectLoggers["nextCursor"];
  $scope.retries = 0;

  var MAX_RETRIES = 500;
  var RETRY_TIMEOUT = 5000;

  $scope.previous = function() {
    $location.search("lc", $scope.previousCursor);
  };

  $scope.next = function() {
    $location.search("lc", $scope.nextCursor);
  };

  var checkStatus = function() {
    $scope.retries = $scope.retries + 1;
    var cursor = $route.current.params.lc;

    $http
      .get("/api/projects/" + $scope.projectId + "/log", {
        params: { lc: cursor }
      })
      .then(function(response) {
        $scope.projectLoggers = response.data["entities"];

        if ($scope.retries < MAX_RETRIES) {
          nextLoad();
        }
      });
  };

  var loadPromise;

  var cancelNextLoad = function() {
    $timeout.cancel(loadPromise);
  };

  var nextLoad = function() {
    cancelNextLoad();
    loadPromise = $timeout(checkStatus, RETRY_TIMEOUT);
  };

  checkStatus();

  $scope.$on("$destroy", function() {
    cancelNextLoad();
  });

  $scope.editProject = function() {
    $location.path("/projects/" + $scope.projectId + "/edit");
    $location.search("lc", undefined);
  };
});
