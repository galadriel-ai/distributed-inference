#!/bin/bash
while true; do logrotate --force --state /home/appuser/.logrotate-state /etc/logrotate.d/log-file; sleep 21600; done