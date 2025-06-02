check:
	@make lint
	@make test

install:
	pip install -e .[dev]
	python -m build

build:
	python -m build --sdist --wheel --outdir dist/ .

lint:
	@python -m ruff check --select I --fix .
	@python -m ruff format .
	@python -m ruff check .
	@python -m pyright .

test:
	@python -m pytest -s --cov=twscrape tests/

test-cov:
	@python -m pytest -s --cov=twscrape tests/
	@coverage html
	@open htmlcov/index.html

test-py:
	$(eval name=twscrape_py$(v))
	@docker -l warning build -f Dockerfile.py-matrix --build-arg VER=$(v) -t $(name) .
	@docker run $(name)

test-matrix-py:
	@make test-py v=3.10
	@make test-py v=3.11
	@make test-py v=3.12
	@make test-py v=3.13

update-mocks:
	@rm -rf ./tests/mocked-data/raw_*.json
	twscrape --debug user_by_id --raw 2244994945 | jq > ./tests/mocked-data/raw_user_by_id.json
	twscrape --debug user_by_login --raw xdevelopers | jq > ./tests/mocked-data/raw_user_by_login.json
	twscrape --debug following --raw --limit 10  2244994945 | jq > ./tests/mocked-data/raw_following.json
	twscrape --debug followers --raw --limit 10 2244994945 | jq > ./tests/mocked-data/raw_followers.json
	twscrape --debug verified_followers --raw --limit 10 2244994945 | jq > ./tests/mocked-data/raw_verified_followers.json
	twscrape --debug subscriptions --raw --limit 10 58579942 | jq > ./tests/mocked-data/raw_subscriptions.json
	twscrape --debug tweet_details --raw 1649191520250245121 | jq > ./tests/mocked-data/raw_tweet_details.json
	twscrape --debug tweet_replies --limit 1 --raw 1649191520250245121 | jq > ./tests/mocked-data/raw_tweet_replies.json
	twscrape --debug retweeters --raw --limit 10 1649191520250245121 | jq > ./tests/mocked-data/raw_retweeters.json
	twscrape --debug user_tweets --raw --limit 10 2244994945 | jq > ./tests/mocked-data/raw_user_tweets.json
	twscrape --debug user_tweets_and_replies --raw --limit 10 2244994945 | jq > ./tests/mocked-data/raw_user_tweets_and_replies.json
	twscrape --debug user_media --raw --limit 10 2244994945 | jq > ./tests/mocked-data/raw_user_media.json
	twscrape --debug search --raw --limit 5 "tesla lang:en" | jq > ./tests/mocked-data/raw_search.json
	twscrape --debug list_timeline --raw --limit 10 1494877848087187461 | jq > ./tests/mocked-data/raw_list_timeline.json
	twscrape --debug trends --raw sport | jq > ./tests/mocked-data/raw_trends.json
