#!/bin/sh

gunicorn -b 127.0.0.1:6000 main:app
