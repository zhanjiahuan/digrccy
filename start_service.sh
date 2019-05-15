#!/bin/bash
gunicorn  --config=gunicorn.conf wsgi_gunicorn:app --log-level=info
