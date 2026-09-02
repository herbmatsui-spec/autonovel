FROM postgres:16

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    postgresql-server-dev-16 \
    flex \
    bison \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build and install pgvector
RUN git clone --depth 1 --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector

# Build and install Apache AGE for PostgreSQL 16
RUN git clone --depth 1 --branch master https://github.com/apache/age.git /tmp/age \
    && cd /tmp/age \
    && make \
    && make install \
    && rm -rf /tmp/age

# Cleanup build packages
RUN apt-get purge -y --auto-remove build-essential git postgresql-server-dev-16 flex bison \
    && rm -rf /var/lib/apt/lists/*
