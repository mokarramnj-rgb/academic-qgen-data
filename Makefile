.PHONY: sample style db plan test clean

sample:
	python3 -m src.satt --html data/raw/class8.html --class 8 --out data/class8_sample.jsonl

style: sample
	python3 -m src.style --jsonl data/class8_sample.jsonl --out data/style_profile.json

db: sample
	python3 -m src.db --jsonl data/class8_sample.jsonl --db data/qbank.sqlite

plan: db
	python3 -m src.plan --db data/qbank.sqlite --user demo --weeks 4 \
		--curriculum data/curriculum.example.json

test:
	python3 -m tests.test_pipeline

clean:
	rm -f data/*.jsonl data/*.sqlite data/*.sqlite-wal data/*.sqlite-shm
