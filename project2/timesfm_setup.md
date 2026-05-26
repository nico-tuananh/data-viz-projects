# TimesFM Setup

Use the official repository flow:

```bash
git clone https://github.com/google-research/timesfm.git
cd timesfm
uv venv
source .venv/bin/activate
uv pip install -e .[torch]
```

If `uv` is not installed first:

```bash
python3 -m pip install uv
```

Notes:

- The forecasting script expects a local TimesFM checkout at `../timesfm` relative to `project2/`.
- The TimesFM model weights are downloaded from Hugging Face on first use.
- The evaluation script loads the PyTorch checkpoint `google/timesfm-2.5-200m-pytorch`.
