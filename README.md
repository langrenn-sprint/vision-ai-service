# vision-ai-service

Analyserer en videostrøm for passeringer (people crossing line). Tar skjermbilde av passeringen. 

## Overvåke folder for endringer i filer

```
% pip install vision-ai-service
% vision_ai_service --help                                 
Usage: vision_ai_service [OPTIONS] URL

  CLI for monitoring directory and send content of files as json to
  webserver URL.

  URL is the url to a webserver exposing an endpoint accepting your json.

  To stop the vision-ai-service, press Control-C.

Options:
  --version                  Show the version and exit.
  -d, --directory DIRECTORY  Relative path to the directory to watch
                             [default: /home/stigbd/src/heming-
                             langrenn/sprint-excel/vision-ai-service]

  -h, --help                 Show this message and exit.

```

## Development
### Requirements
- [pyenv](https://github.com/pyenv/pyenv-installer)
- [pipx](https://github.com/pipxproject/pipx)
- [poetry](https://python-poetry.org/)
- [nox](https://nox.thea.codes/en/stable/)
- [nox-poetry](https://github.com/cjolowicz/nox-poetry)
- [pillow](https://pypi.org/project/Pillow/)
- [google-cloud-vision]

```
% curl https://pyenv.run | bash
% pyenv install 3.9.1
% pyenv install 3.7.9
% python3 -m pip install --user pipx
% python3 -m pipx ensurepath
% pipx install poetry
% pipx install nox
% pipx inject nox nox-poetry
```

### Install
```

% git clone https://github.com/heming-langrenn/sprint-excel.git
% cd vision-ai-service
% pyenv local 3.9.1 3.7.9
% poetry install
```

### Prepare .env filer (dummy parameter values supplied)
LOGGING_LEVEL=DEBU
PHOTO_FTP_DEST=ftp.server.no
PHOTO_FTP_UID=uid@server.no
PHOTO_FTP_PW=password
PHOTO_FTP_BASE_URL=http://www.server.no/sprint/
AZURE_VISION_SUBSCRIPTION_KEY=the_key_from_MS
AZURE_VISION_ENDPOINT=azure_endpoint
GOOGLE_APPLICATION_CREDENTIALS=credentials_file
PHOTOPUSHER_SETTINGS_FILE=/home/github/vision-ai-service/vision-ai-service_settings.json
USER_SERVICE_URL=http://localhost:8086
WEBSERVER_UID=username
WEBSERVER_PW=password
WEBSERVER_TOKEN=token_from_user_service

### Run all sessions
```
% nox
```
### Run all tests with coverage reporting
```
% nox -rs tests
```
### Run cli script
```
% poetry shell
% vision_ai_service --help
### Test start: vision_ai_service -d tests/files/input/ http://resultat.skagenoslosprint.no
### Test start: vision_ai_service -d tests/files/input/ http://localhost:8080

```
Alternatively you can use `poetry run`:
```
% poetry run vision_ai_service --help
```

### Photopusher photo_settings (from vision-ai-service_settings.json)
### All parameters must be in "brackets"
CONFIDENCE_LIMIT - for cognitive services, a float between 0 and 1
PHOTO_THUMB_SIZE - max height/width for thumbnail, an int
PHOTO_WATERMARK_TEXT - text to watermark image, typically name of event
AZURE_THUMB_SERVICE - "True" for Azure, anything else for Pillow
AZURE_VISION_TEXT_SERVICE - "True" for Azure, anything else for Google
