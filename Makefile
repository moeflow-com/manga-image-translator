.PHONY: default

default:
	@echo Please use other targets

venv: conda.yaml
	micromamba env create --file conda.yaml
	micromamba run -n mit-py311 python3 -mvenv --system-site-packages ./venv

run-worker:
	micromamba run -n mit-py311 celery --app moeflow_worker worker --queues mit --loglevel=debug --concurrency=1

run-streamlit:
	micromamba run -n mit-py311 streamlit run streamlit_main.py

prepare-models:
	micromamba run -n mit-py311 python3 docker_prepare.py

build-image:
	docker rmi manga-image-translator || true
	docker build . --tag=manga-image-translator

run-web-server:
	docker run --gpus all -p 5003:5003 --ipc=host --rm zyddnys/manga-image-translator:main \
		--target-lang=ENG \
		--manga2eng \
		--verbose \
		--mode=web \
		--use-gpu \ 
		--host=0.0.0.0 \
		--port=5003
