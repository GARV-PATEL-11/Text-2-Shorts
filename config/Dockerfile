# PROPOSED reproducible render/runtime image (not built or tested in this package).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg texlive-latex-base texlive-latex-extra texlive-fonts-recommended dvisvgm \
      libcairo2-dev libpango1.0-dev pkg-config build-essential bubblewrap socat curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"
# Claude Code CLI: install per https://code.claude.com/docs (native installer); pin a version >= 2.1.275.
# Note: bubblewrap inside Docker needs user namespaces (or run the container itself as the isolation boundary).
COPY . .
RUN python tools/build_manim_api_index.py --out cache/manim_api/0.20.1/index.json && python tools/preflight.py --planning-only || true
ENTRYPOINT ["t2s"]
