#!/bin/bash
set -e

cleanup() {
    echo "Stopping services..."
    supervisorctl -c /etc/supervisor/conf.d/supervisord.conf stop all || true
    exit 0
}

trap cleanup SIGTERM SIGINT

if [ -z "$MANIFEST_PATH" ]; then
    echo "Error: MANIFEST_PATH environment variable is required"
    echo "Usage: docker run -e MANIFEST_PATH=/data/manifest.json -v /host/path:/data dbt-drawio"
    exit 1
fi

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "Error: manifest.json not found at $MANIFEST_PATH"
    exit 1
fi

echo "Starting DBT Visualizer..."
echo "Manifest path: $MANIFEST_PATH"

cd /app

# Generate schema as drawio-user
su - drawio-user -c "python3 /app/generate_scheme.py --path \"$MANIFEST_PATH\" --name /app/dbt_schema.xml"

if [ $? -ne 0 ]; then
    echo "Error: Failed to generate schema"
    exit 1
fi

echo "Schema generated successfully: /app/dbt_schema.xml"

# Ensure file permissions
chown drawio-user:drawio-user /app/dbt_schema.xml
chmod 644 /app/dbt_schema.xml

# Configure Fluxbox to hide toolbar and maximize windows
mkdir -p /home/drawio-user/.fluxbox
cat << EOF > /home/drawio-user/.fluxbox/init
session.screen0.toolbar.visible: false
session.screen0.slit.onTop: false
session.screen0.fullMaximization: true
EOF
# Configure Fluxbox to maximize draw.io window
cat << EOF > /home/drawio-user/.fluxbox/apps
[app] (drawio)
  [Maximized] {yes}
  [Deco] {NONE}
[end]
EOF
chown -R drawio-user:drawio-user /home/drawio-user/.fluxbox

# Start Supervisor as drawio-user
echo "Starting VNC and draw.io..."
exec su - drawio-user -c "/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf"