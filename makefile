SRC = .
PWD = $(shell pwd)

# 1. Set a default value for the target directory (defaults to current PWD)
# If you pass a value from the command line, this default is ignored.  
TARGET_DIR ?= $(PWD)

.PHONY: build
.PHONY: run

build:
	echo "creating venv and exacutable"
	./installdep.sh

run:
	./dist/gca


