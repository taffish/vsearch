FROM debian:12-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251
ARG VSEARCH_VERSION=2.32.0
ARG TARGETARCH
ARG VSEARCH_AMD64_SHA256=c9d7ad4e10e942286ad84004a913e0f2f82957f6156c97a7d6d2389750dd6e41
ARG VSEARCH_ARM64_SHA256=43296e39f29aa7fcd5e3aadcc1a3f0dee910840d8d0d84cf07a78c61b4a75a11
ARG VSEARCH_SOURCE_SHA256=99578a8b960a0fb87c1f19dc65aedecddc01cfa91851b697dac8294dd08a6ceb
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 \
    TAFFISH_ENV=TAFFISH TAFFISH_NAME=vsearch TAFFISH_VERSION=2.32.0 TAFFISH_RELEASE=1
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        bash bzip2 ca-certificates coreutils curl file grep gzip libc-bin libbz2-1.0 \
        libgomp1 libstdc++6 python3 sed tar zlib1g; then break; fi; \
      if [ "$attempt" = 5 ]; then exit 1; fi; \
      apt-get clean; rm -rf /var/lib/apt/lists/*; sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*
RUN set -eux; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) platform=linux-x86_64; sha256="$VSEARCH_AMD64_SHA256" ;; \
      arm64) platform=linux-aarch64; sha256="$VSEARCH_ARM64_SHA256" ;; \
      *) echo "unsupported TARGETARCH: $arch" >&2; exit 1 ;; \
    esac; \
    asset="vsearch-${VSEARCH_VERSION}-${platform}.tar.gz"; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
      "https://github.com/torognes/vsearch/releases/download/v${VSEARCH_VERSION}/${asset}" -o /tmp/binary.tar.gz; \
    echo "$sha256  /tmp/binary.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/vsearch-binary /tmp/vsearch-source /opt/vsearch/bin /opt/vsearch/share/{doc,licenses,testdata,man,completion} /work; \
    tar -xzf /tmp/binary.tar.gz -C /tmp/vsearch-binary --strip-components=1; \
    install -m 0755 /tmp/vsearch-binary/bin/vsearch /opt/vsearch/bin/vsearch; \
    install -m 0644 /tmp/vsearch-binary/README.md /opt/vsearch/share/doc/; \
    cp -a /tmp/vsearch-binary/man/. /opt/vsearch/share/man/; \
    cp /tmp/vsearch-binary/LICENSE*.txt /opt/vsearch/share/licenses/; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
      "https://github.com/torognes/vsearch/releases/download/v${VSEARCH_VERSION}/vsearch-${VSEARCH_VERSION}.tar.gz" -o /tmp/source.tar.gz; \
    echo "$VSEARCH_SOURCE_SHA256  /tmp/source.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/source.tar.gz -C /tmp/vsearch-source --strip-components=1; \
    cp /tmp/vsearch-source/completion/completions/{vsearch,_vsearch,vsearch.fish} /opt/vsearch/share/completion/; \
    cp /tmp/vsearch-source/completion/README.md /opt/vsearch/share/completion/; \
    cp /tmp/vsearch-source/NEWS /opt/vsearch/share/doc/; \
    ln -s /opt/vsearch/bin/vsearch /usr/local/bin/vsearch; \
    printf 'tag=v%s\ncommit=d44d6da51f7fe0b4281f02af76d04923f2075e61\nasset=%s\nasset_sha256=%s\nsource_sha256=%s\n' \
      "$VSEARCH_VERSION" "$asset" "$sha256" "$VSEARCH_SOURCE_SHA256" > /opt/vsearch/share/doc/source.txt; \
    dpkg-query -W > /opt/vsearch/share/doc/dpkg-packages.tsv; \
    rm -rf /tmp/binary.tar.gz /tmp/source.tar.gz /tmp/vsearch-binary /tmp/vsearch-source
COPY docker/vsearch-db.py /usr/local/bin/vsearch-db
COPY docker/vsearch-smoke.py docker/vsearch-resource-smoke.py /opt/vsearch/share/testdata/
RUN set -eux; chmod 0755 /usr/local/bin/vsearch-db; \
    python3 /opt/vsearch/share/testdata/vsearch-smoke.py identity; \
    python3 /opt/vsearch/share/testdata/vsearch-smoke.py core; \
    vsearch-db --version
WORKDIR /work
ENTRYPOINT []
