FROM python:3.13-alpine
ARG DD_VERSION=dev

RUN apk add --no-cache bash libpq libffi \
  && pip install --no-cache-dir uv

COPY LICENSE.md README.md pyproject.toml uv.lock /seer/
RUN uv sync --no-cache --frozen --no-dev --directory ./seer --no-install-project

COPY scripts/start-seer.sh /start-seer.sh
COPY scripts/start-seerapi.sh /start-seerapi.sh
COPY scripts/start.sh /start.sh
COPY scripts/upgrade.py /upgrade.py
RUN chmod +x /start-seer.sh /start-seerapi.sh /start.sh

COPY src /seer/src
RUN uv sync --no-cache --frozen --no-dev --directory ./seer \
  && pip uninstall -y uv

ENV PATH="/seer/.venv/bin:$PATH"
ENV DD_VERSION=$DD_VERSION

EXPOSE 80
CMD ["/start.sh", "seer"]
