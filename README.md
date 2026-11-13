# Zep / Graphiti temporal memory reproduction

This project is a simplified reproduction of the temporal-memory mechanism in [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956). It writes dated conversations to the authors' open-source [Graphiti](https://github.com/getzep/graphiti) engine, retrieves graph facts, and compares answers based on full conversation history, dated graph facts, and the same facts with dates hidden.

The project also tests one modification: writing each message as a separate graph episode instead of writing an entire session as one episode. On a fixed 30-question LongMemEval Oracle subset, the dated graph scored 26.67% with session episodes and 66.67% with message episodes across three paired trials. Graph construction calls increased from 308 to 4,522 per trial on average. See [REPORT.md](REPORT.md) for the experiment design, limitations, and full results.

This is not the proprietary Zep service or an exact reproduction of the paper's published benchmark. It uses DeepSeek, a local Kuzu database, BGE-small embeddings, relation-only retrieval, and an Oracle subset that supplies relevant sessions.

## Requirements

- Python 3.12 and Git.
- Internet access for installation, the first embedding-model download, and DeepSeek API calls.
- A DeepSeek API key with available usage credit.
- Enough free disk space for the embedding model, local graph databases, and run outputs.

The project was tested on Windows. The commands below also show how to set up a standard Python environment on macOS or Linux, but those platforms have not been validated for this exact Graphiti/Kuzu combination. If installation fails, check whether the pinned dependencies provide wheels for your operating system and Python version.

## 1. Clone the project and Graphiti

Run these commands in a terminal. They create a new `ZepReproduction` folder under your current directory; no machine-specific path is required.

```sh
git clone https://github.com/Enterprise2333/ZepReproduction.git
cd ZepReproduction
git clone https://github.com/getzep/graphiti.git graphiti
git -C graphiti checkout fb60e59d4a208c99e7d0186ee6335d2a257f17f2
```

The Graphiti source snapshot is pinned for reproducibility and is intentionally excluded from this repository. The local `graphiti/` directory must exist before the editable package installation.

## 2. Create an environment and install dependencies

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e "graphiti[kuzu]"
python -m pip install -r requirements.txt
```

macOS or Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "graphiti[kuzu]"
python -m pip install -r requirements.txt
```

Run subsequent commands from the project root with this environment active. `environment-lock.txt` records the versions used for the reported experiment; it is an audit record, not an additional install command.

## 3. Configure DeepSeek and prepare embeddings

Copy `.env.example` to `.env` in the project root, then replace `replace_with_your_key` with your own `DEEPSEEK_API_KEY`. Keep the `DEEPSEEK_MODEL=deepseek-chat` line for the reported setup. The `.env` file is ignored by Git; do not commit or share it.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
python prepare_model.py
python prepare_model.py --offline
```

macOS or Linux:

```sh
cp .env.example .env
python prepare_model.py
python prepare_model.py --offline
```

Edit `.env` before running an API-backed command. The first `prepare_model.py` call downloads `BAAI/bge-small-en-v1.5` into `model_cache/`. The `--offline` call checks that the cache is ready. Evaluation itself uses only this local cache.

## 4. Run checks and examples

```sh
python -m unittest discover -p "test_*.py"
python smoke.py
python evaluate.py --suite synthetic --limit 20
```

The tests do not need an API key. `smoke.py` and the evaluations call DeepSeek and may incur API charges. The smoke example writes an old fact, updates it, and searches the resulting temporal graph. The synthetic suite covers simple two-event memory cases.

## 5. Run the LongMemEval Oracle comparison

Download the public [LongMemEval Oracle JSON](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json) and save it as `longmemeval_oracle.json` in the project root. For example:

Windows PowerShell:

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json" -OutFile "longmemeval_oracle.json"
```

macOS or Linux:

```sh
curl -L "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json" -o longmemeval_oracle.json
```

Use the same selection settings for the session and message conditions:

```sh
python evaluate.py --suite longmemeval --limit 10 --seed 5660 --max-chars 30000 --episode-granularity session
python evaluate.py --suite longmemeval --limit 10 --seed 5660 --max-chars 30000 --episode-granularity message
```

`--limit 10` selects up to ten questions from each of three question types, for a total of 30 in the reported dataset. The run manifest records the selected IDs, data hash, prompts, model settings, and source version. The two commands each build graphs and make many API calls; the message condition is substantially more expensive. Start with `--limit 1` if you only want to check that the pipeline runs.

Each run creates a timestamped folder under `results/` with a manifest, per-question predictions, summaries, ingestion records, and isolated Kuzu databases. This folder can contain full public conversation contexts and is ignored by Git. The repository's `artifacts/` folder contains the published aggregate experiment results. `FORMAL_GRANULARITY_RESULTS.md` summarizes the completed three-trial comparison.

## How to interpret the results

The three answer methods use the same answer model and prompt. The no-date comparison hides `valid_at` and `invalid_at` only when composing the answer context; it does not build a graph without temporal data. The full-history baseline reads the original dated sessions. The automatic judge is another source of variation. Three trials repeat the same 30 questions and do not represent 90 independent test cases.

Message-level writing preserves user and assistant roles, order, and the original session timestamp. It does not invent time offsets. Graphiti's recent-episode window stays at its default setting, so the effective amount of original conversation in that window changes with episode granularity. Full-history accuracy remained higher than the modified graph on this Oracle subset. The paper's LongMemEval-S scores are reference points, not directly comparable numbers.

## Key files

- `runtime.py`: DeepSeek client, local embedding model, Kuzu setup, and Graphiti integration.
- `evaluate.py`: question selection, graph ingestion, answering, judging, and run records.
- `smoke.py` and `synthetic.py`: small temporal-memory checks.
- `REPORT.md` and `output/pdf/Zep_Reproducibility_Report.pdf`: report and simple PDF.
- `FORMAL_GRANULARITY_RESULTS.md` and `artifacts/formal-granularity-summary.json`: completed aggregate results.
- `PRESENTATION.md`: presentation outline.

