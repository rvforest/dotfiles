#!/usr/bin/env bash
# Check if en_US.UTF-8 locale is available
# Redirect stdout to /dev/null and send stderr into the pipe so grep only sees stderr
if locale -a 2>&1 >/dev/null | grep -q 'No such file or directory'; then
  echo "en_US.UTF-8 locale missing, generating..."
  sudo locale-gen en_US.UTF-8
  sudo update-locale LANG=en_US.UTF-8
else
  echo "en_US.UTF-8 locale already available."
fi
