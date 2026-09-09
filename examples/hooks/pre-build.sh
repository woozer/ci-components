#!/bin/sh
set -eu
# Working directory is the component's configured working-directory.
test -f pom.xml
printf '%s\n' 'Application-specific prerequisites verified'
