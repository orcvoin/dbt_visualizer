FROM python:3.10

# disable sandbox/zygote inside Electron
ENV DISABLE_ZYGOTE_MANAGER=1
ENV CHROME_DISABLE_SANDBOX=1

# Install necessary utilities and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    graphviz \
    graphviz-dev \
    gcc \
    g++ \
    pkg-config \
    curl \
    jq \
    apt-utils \
    findutils \
    libgtk-3-0 \
    libnotify4 \
    libnss3 \
    xdg-utils \
    libatspi2.0-0 \
    libsecret-1-0 \
    libasound2 \
    libx11-xcb1 \
    libxss1 \
    libxtst6 \
    libatk-bridge2.0-0 \
    libgbm1 \
    libnspr4 \
    tightvncserver \
    supervisor \
    fluxbox \
    x11vnc \
    xvfb \
    novnc \
    websockify \
    wmctrl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    networkx \
    pygraphviz

# Install draw.io and make symlink to "drawio"
RUN set -eux; \
    apt-get update; \
    apt-get install -y curl jq apt-utils findutils \
        libgtk-3-0 libnotify4 libnss3 xdg-utils libatspi2.0-0 libsecret-1-0 libasound2; \
    LATEST_VERSION=$(curl -s -L https://api.github.com/repos/jgraph/drawio-desktop/releases/latest | jq -r '.tag_name | ltrimstr("v")'); \
    if [ -z "$LATEST_VERSION" ]; then echo "Error: drawio version not found"; exit 1; fi; \
    curl -L -o /tmp/drawio-amd64.deb "https://github.com/jgraph/drawio-desktop/releases/download/v${LATEST_VERSION}/drawio-amd64-${LATEST_VERSION}.deb"; \
    dpkg -i /tmp/drawio-amd64.deb || apt-get install -f -y; \
    rm /tmp/drawio-amd64.deb; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*; \
    ln -sf /opt/drawio/drawio /usr/bin/drawio; \
    command -v drawio >/dev/null 2>&1 || { echo "Error: drawio binary not found in /usr/bin"; exit 1; }


RUN printf '#!/bin/sh\nexec /opt/drawio/drawio --no-sandbox \
--disable-setuid-sandbox --disable-gpu \
--disable-seccomp-filter-sandbox "$@"\n' \
    > /usr/local/bin/drawio \
 && chmod +x /usr/local/bin/drawio


# make executable
RUN chmod +x /usr/local/bin/drawio

# Create non-root user and directories with correct permissions
RUN useradd -m -s /bin/bash drawio-user; \
    mkdir -p /app /data /logs /var/log/supervisor /var/run/supervisor /home/drawio-user/.vnc; \
    chown drawio-user:drawio-user /app /data /logs /var/log/supervisor /var/run/supervisor /home/drawio-user/.vnc; \
    chmod 775 /var/log/supervisor /var/run/supervisor

# Copy scripts and configs
COPY vnc_auto.html /usr/share/novnc/vnc_auto.html
COPY generate_scheme.py /app/generate_scheme.py
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/app/docker-entrypoint.sh"]