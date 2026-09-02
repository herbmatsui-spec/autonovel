# Stage 1: Build Apache AGE extension
FROM pgvector/pgvector:pg16 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    postgresql-server-dev-16 \
    flex \
    bison \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch PG16 https://github.com/apache/age.git /tmp/age \
    && cd /tmp/age \
    && make \
    && make install

# Stage 2: Final lightweight image
FROM pgvector/pgvector:pg16

# Copy Apache AGE extension artifacts from builder
COPY --from=builder /usr/lib/postgresql/16/lib/age.so /usr/lib/postgresql/16/lib/age.so
COPY --from=builder /usr/share/postgresql/16/extension/age* /usr/share/postgresql/16/extension/
COPY --from=builder /usr/lib/postgresql/16/lib/bitcode/age* /usr/lib/postgresql/16/lib/bitcode/
