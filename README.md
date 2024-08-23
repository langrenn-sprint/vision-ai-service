# vision-ai-service

Analyserer en videostrøm for passeringer (people crossing line). Tar skjermbilde av passeringen. 

Start service: 
python3 -m vision_ai_service.app
But first, start dependencies (services & db):
docker-compose up event-service user-service photo-service mongodb


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
JWT_SECRET=secret
JWT_EXP_DELTA_SECONDS=3600
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
DB_USER=admin
DB_PASSWORD=password
EVENTS_HOST_SERVER=localhost
EVENTS_HOST_PORT=8082
PHOTOS_HOST_SERVER=localhost
PHOTOS_HOST_PORT=8092
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086

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