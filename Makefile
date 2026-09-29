# ViZDoom played by a small indecis model, pinned to indecis v0.2.0.
#
#   make tools       indecis v0.2.0 release binaries, checksums verified
#   make backbone    bekko-embedding-v1-a8m at a pinned revision
#   make data        training and test states, labeled by the scripted policy
#   make model       fine-tunes the backbone on them (a few minutes)
#   make bench       plays every policy in real time and in lockstep
#   make show        the game with the model's view and decisions, 1920x1080
#
# From pixels (needs indecis built from ../indecis, not yet released):
#   make dev-tools model-pixels bench-pixels video-pixels
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

.PHONY: tools backbone data model bench show video test clean dev-tools siglip data-pixels model-pixels bench-pixels video-pixels

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

# --- From pixels ---------------------------------------------------------
# The image model (SigLIP 2 and a trained spatial head) is not in a release
# yet: indecis is built from the sibling repository.

INDECIS_SRC ?= ../indecis
SIGLIP := siglip2-base-patch32-256
SIGLIP_REVISION := 94dffa8cb1179de3e03f091dbc3917e5d5a9ae84
SIGLIP_DIR := build/$(SIGLIP)
PIXEL_TRAIN_EPISODES ?= 60
PIXEL_TEST_EPISODES ?= 15

dev-tools:
	mkdir -p bin-dev
	cd $(INDECIS_SRC) && GOEXPERIMENT=simd CGO_ENABLED=0 go build -o $(CURDIR)/bin-dev/indecis ./cmd/indecis
	cd $(INDECIS_SRC)/decision && GOEXPERIMENT=simd CGO_ENABLED=0 go build -o $(CURDIR)/bin-dev/indecis-serve ./cmd/indecis-serve

siglip: $(SIGLIP_DIR)/model.safetensors

$(SIGLIP_DIR)/model.safetensors:
	mkdir -p $(SIGLIP_DIR)
	for f in config.json model.safetensors tokenizer.json; do \
		curl -sfL -o $(SIGLIP_DIR)/$$f https://huggingface.co/google/$(SIGLIP)/resolve/$(SIGLIP_REVISION)/$$f; \
	done

# Frames the scripted policy sees, one decision in three, labeled with its
# answers; test episodes differ from training ones.
data-pixels:
	$(PY) play.py harvest-pixels --episodes $(PIXEL_TRAIN_EPISODES) --first-seed 1 --out build/pixels/train
	$(PY) play.py harvest-pixels --episodes $(PIXEL_TEST_EPISODES) --first-seed 1001 --out build/pixels/test

model-pixels: siglip
	bin-dev/indecis train-vision -backbone $(SIGLIP_DIR) -schema model/schema.json \
		-train build/pixels/train/labels.jsonl -test build/pixels/test/labels.jsonl \
		-epochs 20 -seed 1 -out build/model-pixels

bench-pixels:
	mkdir -p results
	$(PY) play.py bench --policies scripted,trained,pixels --episodes $(BENCH_EPISODES) --first-seed 2001 \
		--indecis-serve bin-dev/indecis-serve --json results/pixels.json | tee results/pixels.md

video-pixels:
	uv run --group show python play.py show --policy pixels --episodes $(SHOW_EPISODES) --first-seed 2001 \
		--indecis-serve bin-dev/indecis-serve --record build/pixels.mp4

clean:
	rm -rf bin bin-dev build
