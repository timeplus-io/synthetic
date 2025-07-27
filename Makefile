IMAGE_VERSION := $(shell git rev-parse --short HEAD)
BIN_NAME = synthetic
IMAGE_NAME = $(BIN_NAME):$(IMAGE_VERSION)
DOCKER_ID_USER = timeplus
FULLNAME=$(DOCKER_ID_USER)/${IMAGE_NAME}

PHONY: install_dep install_udf install docker_build docker

install_dep:
	curl -X POST http://localhost:8123/timeplusd/v1/python_packages \
		-u proton:timeplus@t+ \
		-d '{"packages": [{"name": "faker"}]}'

install_udf:
	curl -X POST http://localhost:8123/ \
		-H 'Content-Type: text/plain' \
		-u proton:timeplus@t+ \
		--data-binary @./script/udf.sql

install: install_dep install_udf

docker_build:
	docker build -t $(FULLNAME) .

docker: Dockerfile
	docker buildx build \
		--no-cache -t $(FULLNAME) \
		--build-arg VERSION=$(VERSION) \
		--platform linux/arm64,linux/amd64 \
		--builder container \
		--push .