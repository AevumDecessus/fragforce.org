#!/usr/bin/env bash

cd /code
# Migrate public db
pipenv run python manage.py migrate
# Collect static files
pipenv run python manage.py collectstatic --no-input
pipenv shell
