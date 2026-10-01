# ViZDoom played by a small indecis model, pinned to indecis v0.3.0.
#
#   make tools       indecis v0.3.0 release binaries, checksums verified
#   make backbone    bekko-embedding-v1-a8m at a pinned revision
#   make data        training and test states, labeled by the scripted policy
#   make model       fine-tunes the backbone on them (a few minutes)
#   make bench       plays every policy in real time and in lockstep
#   make show        the game with the model's view and decisions, 1920x1080
#   make video       the same, recorded with sound to build/$(SCENARIO).mp4
#
# From pixels:
#   make siglip data-pixels model-pixels bench-pixels video-pixels

INDECIS_VERSION := 0.3.0
ARCH := $(shell uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
SHA256_amd64 := 564385e018bc3efa4851fd6236bce372f746baa3e771270a4107c39bc120591f
SHA256_arm64 := e5ba1c4e3a2e546aa7aec5250ab929d8c5ab015681ae791228d113298a51af1e
TARBALL := indecis_$(INDECIS_VERSION)_linux_$(ARCH).tar.gz

BEKKO := bekko-embedding-v1-a8m
BEKKO_REVISION := c721113d59a1d91b447450324f51c4b3332c924a
BACKBONE := build/$(BEKKO)

TRAIN_EPISODES ?= 200
TEST_EPISODES ?= 40
BENCH_EPISODES ?= 20

PY := uv run python

.PHONY: tools backbone data model bench show video test clean siglip data-pixels model-pixels bench-pixels video-pixels

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
# The image model: SigLIP 2 and a spatial head trained on its patches.

SIGLIP := siglip2-base-patch32-256
SIGLIP_REVISION := 94dffa8cb1179de3e03f091dbc3917e5d5a9ae84
SIGLIP_DIR := build/$(SIGLIP)
PIXEL_TRAIN_EPISODES ?= 60
PIXEL_TEST_EPISODES ?= 15

siglip: $(SIGLIP_DIR)/model.safetensors

$(SIGLIP_DIR)/model.safetensors:
	mkdir -p $(SIGLIP_DIR)
	for f in config.json model.safetensors tokenizer.json; do \
		curl -sfL -o $(SIGLIP_DIR)/$$f https://huggingface.co/google/$(SIGLIP)/resolve/$(SIGLIP_REVISION)/$$f; \
	done

# Cores per image in indecis-serve (0: one). Two cores help only when they
# are both performance cores: unpinned, on a hybrid processor, a second
# core often lands on an efficiency core and slows every decision.
PIXEL_THREADS ?= 0
DAGGER_EPISODES ?= 40
ROUND ?= 1

# Frames the scripted policy sees, one decision in three, labeled with its
# answers, and their mirror images; test episodes differ from training ones.
data-pixels:
	$(PY) play.py harvest-pixels --episodes $(PIXEL_TRAIN_EPISODES) --first-seed 1 --mirror --out build/pixels/train
	$(PY) play.py harvest-pixels --episodes $(PIXEL_TEST_EPISODES) --first-seed 1001 --out build/pixels/test

# DAgger: the current pixel model plays, the script labels what it sees.
# Measured on 20 episodes, two rounds lowered the score (+17.2 against
# +19.4): it is kept for experiments, with DAGGER=1 in model-pixels.
dagger-pixels: tools
	$(PY) play.py harvest-pixels --driver pixels --episodes $(DAGGER_EPISODES) --first-seed $$((3000 + 100 * $(ROUND))) \
		--mirror --threads $(PIXEL_THREADS) --out build/pixels/dagger$(ROUND)

# Trains on every harvested directory; features are cached.
model-pixels: tools siglip
	bin/indecis train-vision -backbone $(SIGLIP_DIR) -schema model/schema.json \
		-train $$(ls build/pixels/train/labels.jsonl $(if $(DAGGER),build/pixels/dagger*/labels.jsonl) 2>/dev/null | paste -sd,) \
		-test build/pixels/test/labels.jsonl -cache build/pixels/cache \
		-layer 8 -epochs 20 -seed 1 -out build/model-pixels

bench-pixels: tools
	mkdir -p results
	$(PY) play.py bench --policies scripted,trained,pixels --episodes $(BENCH_EPISODES) --first-seed 2001 \
		--threads $(PIXEL_THREADS) --json results/pixels.json | tee results/pixels.md

video-pixels: tools
	uv run --group show python play.py show --policy pixels --episodes $(SHOW_EPISODES) --first-seed 2001 \
		--threads $(PIXEL_THREADS) --record build/pixels.mp4

clean:
	rm -rf bin build
