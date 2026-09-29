"""Harvests training data, plays episodes and compares policies.

    uv run python play.py harvest --episodes 200 --out build/data/train.jsonl
    uv run python play.py play --policy trained --episodes 3
    uv run python play.py bench --episodes 20
    uv run --group show python play.py show --policy trained --record demo.mp4
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import vizdoom as vzd  # noqa: E402

from indecis_vizdoom import loop, policies  # noqa: E402
from indecis_vizdoom.game import make_game  # noqa: E402
from indecis_vizdoom.server import indecis_serve  # noqa: E402

POLICIES = ("scripted", "random", "trained", "backbone", "pixels")

# The pixel policy sees the game at this resolution, without HUD: the
# frames it was trained on.
PIXELS_RESOLUTION = vzd.ScreenResolution.RES_320X240


def harvest(args) -> None:
    """Lockstep episodes played by the scripted policy; one example per
    distinct state text (the text determines the scripted answer)."""
    game = make_game(args.scenario)
    seen: dict[str, dict] = {}

    def record(text, d, frame):
        if text not in seen:
            seen[text] = {"text": text, "labels": {"fire": d.fire, "turn": d.turn}}

    policy = policies.Scripted()
    for seed in range(args.first_seed, args.first_seed + args.episodes):
        loop.lockstep(game, policy, seed, args.interval, record)
    game.close()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        for ex in seen.values():
            f.write(json.dumps(ex) + "\n")
    print(f"{len(seen)} distinct states from {args.episodes} episodes -> {args.out}", file=sys.stderr)


def harvest_pixels(args) -> None:
    """Lockstep episodes played by the scripted policy; every --every-th
    decision, the frame the pixel policy would see and the scripted answer,
    in the format of indecis train-vision."""
    game = make_game(args.scenario, resolution=PIXELS_RESOLUTION)
    frames = os.path.join(args.out, "frames")
    os.makedirs(frames, exist_ok=True)
    n, slot = 0, 0
    with open(os.path.join(args.out, "labels.jsonl"), "w") as f:
        def record(text, d, frame):
            nonlocal n, slot
            slot += 1
            if slot % args.every:
                return
            name = f"frames/{n:06d}.png"
            with open(os.path.join(args.out, name), "wb") as img:
                img.write(policies.png(frame))
            f.write(json.dumps({"image": name, "labels": {"fire": d.fire, "turn": d.turn}}) + "\n")
            n += 1

        policy = policies.Scripted()
        for seed in range(args.first_seed, args.first_seed + args.episodes):
            loop.lockstep(game, policy, seed, args.interval, record)
    game.close()
    print(f"{n} frames from {args.episodes} episodes -> {args.out}", file=sys.stderr)


@contextlib.contextmanager
def open_policy(name: str, args, url: str | None):
    if name == "scripted":
        p = policies.Scripted()
    elif name == "random":
        p = policies.Random(args.first_seed)
    elif name == "pixels":
        p = policies.Pixels(url, "doom-pixels")
    else:
        p = policies.Indecis(url, "doom" if name == "trained" else "backbone")
    try:
        yield p
    finally:
        p.close()


@contextlib.contextmanager
def server(args, names):
    if not any(n in ("trained", "backbone", "pixels") for n in names):
        yield None
        return
    models = {}
    if "trained" in names:
        models["doom"] = args.model
    if "backbone" in names:
        models["backbone"] = args.backbone
    if "pixels" in names:
        models["doom-pixels"] = args.pixel_model
    with indecis_serve(args.indecis_serve, models, args.addr) as served:
        yield served


def run(args, names) -> list[dict]:
    game = make_game(args.scenario, resolution=PIXELS_RESOLUTION if "pixels" in names else None)
    results = []
    with server(args, names) as served:
        url = served.url if served else None
        for name in names:
            with open_policy(name, args, url) as p:
                play = loop.realtime if args.realtime else loop.lockstep
                eps = []
                for seed in range(args.first_seed, args.first_seed + args.episodes):
                    ep = play(game, p, seed, args.interval)
                    eps.append(ep)
                    print(f"{name:9} seed={seed} score={ep.score:+.0f} kills={ep.kills} "
                          f"decisions/s={ep.decisions_per_second:.1f} skipped={ep.skipped}", file=sys.stderr)
                results.append(loop.summary(name, eps))
    game.close()
    return results


SUBTITLES = {
    "trained": "bekko-embedding-v1-a8m, 7.7M parameters, fine-tuned with indecis v0.2.0. Pure Go, one CPU core, no GPU.",
    "backbone": "bekko-embedding-v1-a8m without training, in open mode.",
    "scripted": "Hand-written rules: the ceiling the trained model imitates.",
    "random": "Random decisions.",
    "pixels": "SigLIP 2 image encoder (86M parameters) and a spatial head trained with indecis. Pure Go, CPU, no GPU.",
}


def show(args) -> None:
    from indecis_vizdoom.show import show as run_show

    seeds = list(range(args.first_seed, args.first_seed + args.episodes))
    title = {"trained": "indecis plays Doom", "backbone": "indecis plays Doom",
             "pixels": "indecis plays Doom from pixels"}.get(args.policy, f"{args.policy} plays Doom")
    with server(args, [args.policy]) as served, open_policy(args.policy, args, served.url if served else None) as p:
        memory = served.memory if served else None
        run_show(p, title, SUBTITLES[args.policy], seeds, args.scenario, args.interval, args.scale, args.record, memory)


def table(results: list[dict], realtime: bool) -> str:
    lines = [f"Mode: {'real time' if realtime else 'lockstep'}", "",
             "| Policy | Score | Kills | Decisions/s | Latency p50 | p95 | Skipped slots | Turn choices |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        turns = ", ".join(f"{k} {v:.0%}" for k, v in r["turns"].items())
        lines.append(f"| {r['policy']} | {r['score']:+.1f} (sd {r['score_sd']:.1f}) | {r['kills']:.1f} | "
                     f"{r['decisions_per_second']:.1f} | {r['latency_p50_ms']:.1f} ms | {r['latency_p95_ms']:.1f} ms | "
                     f"{r['skipped_per_episode']:.1f} | {turns} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--scenario", default="defend_the_center")
    common.add_argument("--episodes", type=int, default=10)
    common.add_argument("--first-seed", type=int, default=1)
    common.add_argument("--interval", type=int, default=4, help="tics between two decision slots")
    h = sub.add_parser("harvest", parents=[common])
    h.add_argument("--out", required=True)
    hp = sub.add_parser("harvest-pixels", parents=[common])
    hp.add_argument("--out", required=True, help="directory: frames/ and labels.jsonl")
    hp.add_argument("--every", type=int, default=3, help="keep one decision in this many")
    for cmd in ("play", "bench", "show"):
        p = sub.add_parser(cmd, parents=[common])
        p.add_argument("--lockstep", dest="realtime", action="store_false",
                       help="the game waits for each decision (default: latency costs game time)")
        p.add_argument("--model", default="build/model")
        p.add_argument("--backbone", default="build/bekko-embedding-v1-a8m")
        p.add_argument("--pixel-model", default="build/model-pixels", help="image model of the pixels policy")
        p.add_argument("--indecis-serve", default="bin/indecis-serve")
        p.add_argument("--addr", default="127.0.0.1:8090")
        p.add_argument("--json", help="also write the results to this file")
        if cmd in ("play", "show"):
            p.add_argument("--policy", choices=POLICIES, default="trained")
        if cmd == "show":
            p.add_argument("--scale", type=float, default=1.0, help="window size relative to 1920x1080")
            p.add_argument("--record", help="also write the video to this MP4 file (needs ffmpeg)")
        else:
            p.add_argument("--policies", default=",".join(POLICIES))
    args = ap.parse_args()
    if args.cmd == "harvest":
        harvest(args)
        return
    if args.cmd == "harvest-pixels":
        harvest_pixels(args)
        return
    if args.cmd == "show":
        show(args)
        return
    names = [args.policy] if args.cmd == "play" else args.policies.split(",")
    results = run(args, names)
    print(table(results, args.realtime))
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"realtime": args.realtime, "results": results}, f, indent=2)


if __name__ == "__main__":
    main()
