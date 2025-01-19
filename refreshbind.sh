#!/bin/bash

# Run the scraping process
/home/mema/code/copertinefull/backend/.venv/bin/python /home/mema/code/copertinefull/backend/src/scrape2.py

# Restart the container
/usr/bin/docker compose --project-directory /home/mema/mema_docker_compose/ stop copfront
/usr/bin/docker compose --project-directory /home/mema/mema_docker_compose/ start copfront

