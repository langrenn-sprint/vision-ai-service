# photopusher

Overvåker folder og sender data i nye/endrede filer som json til sprint-webserver.

## Overvåke folder for endringer i filer

```
% pip install sprint-photopusher
% sprint_photopusher --help                                 
Usage: sprint_photopusher [OPTIONS] URL

  CLI for monitoring directory and send content of files as json to
  webserver URL.

  URL is the url to a webserver exposing an endpoint accepting your json.

  To stop the photopusher, press Control-C.

Options:
  --version                  Show the version and exit.
  -d, --directory DIRECTORY  Relative path to the directory to watch
                             [default: /home/stigbd/src/heming-
                             langrenn/sprint-excel/photopusher]

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
Set environmen variable to link up secrets and settings
% export PHOTOPUSHER_SETTINGS="/home/heming/github/sprint-photopusher/photopusher_settings.json"
% export PHOTOPUSHER_CREDENTIALS="/home/heming/github/secrets/photopusher_credentials.json"
% export GOOGLE_APPLICATION_CREDENTIALS="/home/heming/github/secrets/kjelsaas-langrenn-257719-a69dfe50d3f2.json"

% git clone https://github.com/heming-langrenn/sprint-excel.git
% cd sprint-photopusher
% pyenv local 3.9.1 3.7.9
% poetry install
```
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
% sprint_photopusher --help
### Test start: sprint_photopusher -d tests/files/input/ http://resultat.skagenoslosprint.no
### Test start: sprint_photopusher -d tests/files/input/ http://localhost:8080

```
Alternatively you can use `poetry run`:
```
% poetry run sprint_photopusher --help
```

### Photopusher photo_settings (from photopusher_settings.json)
### All parameters must be in "brackets"
CONFIDENCE_LIMIT - for cognitive services, a float between 0 and 1
PHOTO_THUMB_SIZE - max height/width for thumbnail, an int
PHOTO_WATERMARK_TEXT - text to watermark image, typically name of event
AZURE_THUMB_SERVICE - "True" for Azure, anything else for Pillow
AZURE_VISION_TEXT_SERVICE - "True" for Azure, anything else for Google
