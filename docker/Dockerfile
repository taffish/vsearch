FROM debian:12-slim

ARG VSEARCH_VERSION=2.31.0
ARG TARGETARCH
ARG VSEARCH_AMD64_SHA256=1f07aec19cdeaf2a0ce8d9e3c9e6bb76a5cbf54e86d40bc50cb314a06ace2a16
ARG VSEARCH_ARM64_SHA256=b053c0da34b48b5f05ce16268e46bc6dfe3458ab6c0ba688db786045c7e94f43

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=3 update \
       && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
            bash \
            bzip2 \
            ca-certificates \
            coreutils \
            curl \
            file \
            grep \
            gzip \
            libc-bin \
            libbz2-1.0 \
            libgomp1 \
            libstdc++6 \
            sed \
            tar \
            zlib1g; then \
        break; \
      fi; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/*; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -eux; \
    arch="${TARGETARCH:-}"; \
    if [ -z "${arch}" ]; then \
      case "$(uname -m)" in \
        x86_64) arch="amd64" ;; \
        aarch64) arch="arm64" ;; \
        *) echo "unsupported build architecture: $(uname -m)" >&2; exit 1 ;; \
      esac; \
    fi; \
    case "${arch}" in \
      amd64) \
        asset="vsearch-${VSEARCH_VERSION}-linux-x86_64.tar.gz"; \
        root="vsearch-${VSEARCH_VERSION}-linux-x86_64"; \
        sha256="${VSEARCH_AMD64_SHA256}" ;; \
      arm64) \
        asset="vsearch-${VSEARCH_VERSION}-linux-aarch64.tar.gz"; \
        root="vsearch-${VSEARCH_VERSION}-linux-aarch64"; \
        sha256="${VSEARCH_ARM64_SHA256}" ;; \
      *) echo "unsupported TARGETARCH: ${arch}" >&2; exit 1 ;; \
    esac; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
      "https://github.com/torognes/vsearch/releases/download/v${VSEARCH_VERSION}/${asset}" \
      -o /tmp/vsearch.tar.gz; \
    echo "${sha256}  /tmp/vsearch.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/vsearch-src /opt/vsearch/bin /opt/vsearch/share/doc/vsearch \
      /opt/vsearch/share/licenses/vsearch /opt/vsearch/share/man/man1 /opt/vsearch/share/testdata; \
    tar -xzf /tmp/vsearch.tar.gz -C /tmp/vsearch-src; \
    install -m 0755 "/tmp/vsearch-src/${root}/bin/vsearch" /opt/vsearch/bin/vsearch; \
    install -m 0644 "/tmp/vsearch-src/${root}/README.md" /opt/vsearch/share/doc/vsearch/README.md; \
    install -m 0644 "/tmp/vsearch-src/${root}/LICENSE.txt" /opt/vsearch/share/licenses/vsearch/LICENSE.txt; \
    install -m 0644 "/tmp/vsearch-src/${root}/LICENSE_GNU_GPL3.txt" /opt/vsearch/share/licenses/vsearch/LICENSE_GNU_GPL3.txt; \
    install -m 0644 "/tmp/vsearch-src/${root}/man/vsearch.1" /opt/vsearch/share/man/man1/vsearch.1; \
    install -m 0644 "/tmp/vsearch-src/${root}/doc/vsearch_manual.pdf" /opt/vsearch/share/doc/vsearch/vsearch_manual.pdf; \
    ln -sf /opt/vsearch/bin/vsearch /usr/local/bin/vsearch; \
    { \
      printf "upstream_repo=https://github.com/torognes/vsearch\n"; \
      printf "upstream_tag=v%s\n" "${VSEARCH_VERSION}"; \
      printf "runtime_source=official GitHub release binary\n"; \
      printf "runtime_asset=%s\n" "${asset}"; \
      printf "runtime_asset_sha256=%s\n" "${sha256}"; \
      printf "target_arch=%s\n" "${arch}"; \
    } > /opt/vsearch/share/doc/vsearch/source.txt; \
    rm -rf /tmp/vsearch.tar.gz /tmp/vsearch-src

RUN cat > /opt/vsearch/share/testdata/vsearch-smoke.sh <<'EOF'
#!/bin/sh
set -eu

tmp="${1:-/tmp/taf-vsearch-smoke-$$}"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

run_logged() {
  log="$1"
  shift
  if ! "$@" > "$log" 2>&1; then
    cat "$log" >&2
    exit 1
  fi
}

cat > reads.fa <<'FASTA'
>read1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
>read2
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
>read3
ACGTACGTACGTACGTACGTACGTACGTACGTTCGTACGTACGTACGTACGTACGTACGTACGT
FASTA

cat > queries.fa <<'FASTA'
>query1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
FASTA

cat > db.fa <<'FASTA'
>db1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
>db2
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
FASTA

run_logged uniques.log vsearch --fastx_uniques reads.fa --fastaout uniques.fa --sizeout --threads 1
test -s uniques.fa
grep -F ';size=2' uniques.fa >/dev/null || { cat uniques.fa >&2; exit 1; }
grep -F ';size=1' uniques.fa >/dev/null || { cat uniques.fa >&2; exit 1; }

run_logged search.log vsearch --usearch_global queries.fa --db db.fa --id 0.90 --blast6out hits.tsv --threads 1
test -s hits.tsv
grep -F 'query1' hits.tsv >/dev/null || { cat hits.tsv >&2; exit 1; }
grep -F 'db1' hits.tsv >/dev/null || { cat hits.tsv >&2; exit 1; }

gzip -c reads.fa > reads.fa.gz
run_logged sort.log vsearch --sortbylength reads.fa.gz --output sorted.fa --threads 1
test -s sorted.fa
grep -F '>read1' sorted.fa >/dev/null || { cat sorted.fa >&2; exit 1; }

bzip2 -c reads.fa > reads.fa.bz2
run_logged revcomp.log vsearch --fastx_revcomp reads.fa.bz2 --fastaout revcomp.fa --threads 1
test -s revcomp.fa
grep -F '>read1' revcomp.fa >/dev/null || { cat revcomp.fa >&2; exit 1; }
EOF

RUN set -eux; \
    chmod 0755 /opt/vsearch/share/testdata/vsearch-smoke.sh; \
    vsearch --version 2>&1 | grep -F "vsearch v${VSEARCH_VERSION}" >/dev/null; \
    vsearch --help 2>&1 | grep -F -- "--usearch_global" >/dev/null; \
    vsearch --help 2>&1 | grep -F -- "--fastq_mergepairs" >/dev/null; \
    vsearch --help 2>&1 | grep -F -- "--uchime_denovo" >/dev/null; \
    /opt/vsearch/share/testdata/vsearch-smoke.sh /tmp/vsearch-build-smoke; \
    ldd "$(command -v vsearch)" > /tmp/vsearch-ldd.txt 2>&1 || true; \
    if grep -F "not found" /tmp/vsearch-ldd.txt; then exit 1; fi; \
    rm -f /tmp/vsearch-ldd.txt

WORKDIR /root

ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=vsearch
