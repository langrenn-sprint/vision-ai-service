# vision-ai-service

Analyserer en videostrøm for passeringer (people crossing line). Tar skjermbilde av passeringen. 

Usage: python3 vision-ai-service/app.py

## Development
### Requirements
- [pyenv](https://github.com/pyenv/pyenv-installer)
- [pipx](https://github.com/pipxproject/pipx)
- [poetry](https://python-poetry.org/)
- [nox](https://nox.thea.codes/en/stable/)
- [nox-poetry](https://github.com/cjolowicz/nox-poetry)
- [pillow](https://pypi.org/project/Pillow/)


### Install
```

% git clone https://github.com/heming-langrenn/vision-ai-service.git
% cd vision-ai-service
% pyenv local 3.11
% poetry install
```

### Prepare .env filer (dummy parameter values supplied)
LOGGING_LEVEL=INFO
PHOTOS_FILE_PATH=/Users/t520834/github/photo-service-gui/docs/photos
VIDEO_URL=http://localhost:8080/video
DETECTION_BOX_MINIMUM_SIZE=0.08
GLOBAL_SETTINGS_FILE=vision-ai-service/config/global_settings.json
VIDEO_STATUS_FILE=vision-ai-service/config/video_status.json

### Run all sessions
```
% nox
```
### Run all tests with coverage reporting
```
% nox -rs tests
```