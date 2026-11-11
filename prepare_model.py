"""Explicit first-use download; evaluation itself uses only the local cache."""
import argparse
from runtime import LocalEmbedder
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        model = LocalEmbedder(args.cache_dir, allow_download=not args.offline)
        vector = next(model.model.embed(["model readiness check"]))
        assert len(vector) == 384
        print("Embedding ready: 384 dimensions")
    except Exception as exc:
        raise SystemExit("Embedding unavailable. Run prepare_model.py online first, using the same --cache-dir. " + str(exc))
