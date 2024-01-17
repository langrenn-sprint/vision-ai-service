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
% pyenv local 3.11
% poetry install
```

### Prepare .env filer (dummy parameter values supplied)
LOGGING_LEVEL=INFO
PHOTOS_FILE_PATH=/Users/t520834/github/photo-service-gui/docs/photos
VIDEO_URL=http://localhost:8080/video
CAMERA_LOCATION=Finish
TRIGGER_LINE_XYXY=0.15:0.70:1:0.70
DETECTION_BOX_MINIMUM_SIZE=0.08

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
### Test start: vision_ai_service

```
Alternatively you can use `poetry run`:
```
% poetry run vision_ai_service --help
```