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
PHOTOS_FILE_PATH=vision-ai-service/files
VIDEO_URL=https://harnaes.no/maalfoto/2023SkiMaal.mp4
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

### Push to docker registry manually (CLI)
docker-compose build
docker login ghcr.io -u <github username>
password: Use a generated access token from GitHub
docker push ghcr.io/langrenn-sprint/vision-ai-service:latest