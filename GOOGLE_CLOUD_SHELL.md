**This is not an officially supported Google product. It is a reference implementation.**

# Bulk Uploader

This tool is a Python and Angular application to showcase the [Campaign Manager API](https://developers.google.com/doubleclick-advertisers) workflow. It aids in quickly launching a new set of campaigns to Campaign Manager from a simple CSV feed and a set of associated creative assets that are created and launched via the Campaign Manager trafficking APIs.

## Deployment

Run this script from the command line:

        ./scripts/deploy.sh

## Your newly deployed application

To view your newly deployed application running, you can open a browser with:

        gcloud app browse

On first run, you will be prompted for a username and password by HTTP basic auth. The default username is `admin` and password is `admin`.

## Credentials and settings

Once the application is running we can change a few of the defaults that have been set up by the application's initialization.

1. Open a browser and navigate to your newly locally running or App Engine deployed application. Remember, you may be prompted for a username and password by the basic auth scheme. The default username is `admin` and password is `admin`.
2. To view your application's settings page, click the menu icon (three dots) that is located in the top-right corner of the application.

Now that you are on the settings page, you can choose to change the HTTP basic auth username and password if needed. This is recommended. Take note of any changes.

The settings screen also allows us to set a `Client ID` and `config.json` for the application to use as authorization for the Campaign Manager API and Sheets API calls. To gather these credentials:

1. Create a new project in the [Google API Console](https://console.developers.google.com).
2. Click on the `+ ENABLE APIS AND SERVICES` button.
3. Find and enable the `DCM/DFA Reporting and Trafficking API`.
4. Find and enable the `Google Drive API`.
5. Go back to the APIs & Services dashboard and click the `Credentials` tab.
6. Configure a new `OAuth client ID` by clicking the `Create credentials` button.
7. If needed, configure the consent screen.
8. Choose `Web application` and pick a name for your new application.
9. Add your application's local and App Engine URLs to `Authorized JavaScript origins` and `Authorized redirect URIs`.
10. Download the JSON file, open it in a text editor, and copy its contents into the `config.json` field of the settings page.

## Samples

A sample CSV feed, and its sample assets are in the `samples` directory of the GitHub repository.

## Congratulations

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

You're all set! Read the user guide and start bulk uploading!
