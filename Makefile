# ViZDoom played by a small indecis model, pinned to indecis v0.2.0.
#
#   make tools       indecis v0.2.0 release binaries, checksums verified
#   make backbone    bekko-embedding-v1-a8m at a pinned revision
#   make data        training and test states, labeled by the scripted policy
#   make model       fine-tunes the backbone on them (a few minutes)
#   make bench       plays every policy in real time and in lockstep
#   make show        the game with the model's view and decisions, 1920x1080
#   make video       the same, recorded with sound to build/$(SCENARIO).mp4

INDECIS_VERSION := 0.2.0
ARCH := $(shell uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
SHA256_amd64 := 0364355e938d4608cf1301cebd0278c5657e9a40cd32001a05f03956062de250
SHA256_arm64 := 5a5afc2eef0fe4841ba386e150920ae0760ac04e0fb74c566574be9bab1197cf
TARBALL := indecis_$(INDECIS_VERSION)_linux_$(ARCH).tar.gz

BEKKO := bekko-embedding-v1-a8m
BEKKO_REVISION := c721113d59a1d91b447450324f51c4b3332c924a
BACKBONE := build/$(BEKKO)

TRAIN_EPISODES ?= 200
TEST_EPISODES ?= 40
BENCH_EPISODES ?= 20

PY := uv run python

.PHONY: tools backbone data model bench show video test clean

tools: bin/indecis bin/indecis-serve

bin/indecis bin/indecis-serve &: 
	mkdir -p build bin
	curl -sfL -o build/$(TARBALL) https://github.com/Bornholm/indecis/releases/download/v$(INDECIS_VERSION)/$(TARBALL)
	echo "$(SHA256_$(ARCH))  build/$(TARBALL)" | sha256sum -c -
	tar -xzf build/$(TARBALL) -C bin indecis indecis-serve
	bin/indecis check || echo "warning: this processor runs indecis slowly, see above"

backbone: $(BACKBONE)/model.safetensors

$(BACKBONE)/model.safetensors:
	mkdir -p $(BACKBONE)
	for f in config.json model.safetensors tokenizer.json; do \
		curl -sfL -o $(BACKBONE)/$$f https://huggingface.co/hotchpotch/$(BEKKO)/resolve/$(BEKKO_REVISION)/$$f; \
	done

# Train and test states come from different episodes (seeds 1-200 and 1001-1040).
data:
	$(PY) play.py harvest --episodes $(TRAIN_EPISODES) --first-seed 1 --out build/data/train.jsonl
	$(PY) play.py harvest --episodes $(TEST_EPISODES) --first-seed 1001 --out build/data/test.jsonl

model: tools backbone
	bin/indecis train -backbone $(BACKBONE) -schema model/schema.json \
		-train build/data/train.jsonl -test build/data/test.jsonl \
		-epochs 2 -seed 1 -out build/model

# Bench seeds (2001-) differ from the training and test ones.
bench: tools backbone
	mkdir -p results
	$(PY) play.py bench --episodes $(BENCH_EPISODES) --first-seed 2001 --json results/realtime.json | tee results/realtime.md
	$(PY) play.py bench --episodes $(BENCH_EPISODES) --first-seed 2001 --lockstep --json results/lockstep.json | tee results/lockstep.md

SHOW_EPISODES ?= 3
SCENARIO ?= defend_the_center
SHOW_SCALE ?= 1

show: tools
	uv run --group show python play.py show --scenario $(SCENARIO) --policy trained --episodes $(SHOW_EPISODES) --first-seed 2001 --scale $(SHOW_SCALE)

video: tools
	uv run --group show python play.py show --scenario $(SCENARIO) --policy trained --episodes $(SHOW_EPISODES) --first-seed 2001 --scale $(SHOW_SCALE) --record build/$(SCENARIO).mp4

test:
	uv run pytest -q

clean:
	rm -rf bin build
