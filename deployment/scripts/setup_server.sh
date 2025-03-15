#!/bin/bash
set -e

# Install dependencies if not already installed
if ! command -v nginx &> /dev/null; then
  apt-get update
  apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip git nginx certbot python3-certbot-nginx
fi

# Set pythn3.11 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --set python3 /usr/bin/python3.11

# Setup Nginx configurations
if [ -d "/opt/prodizy-platform/deployment/config/nginx" ]; then
  cp /opt/prodizy-platform/deployment/config/nginx/*.conf /etc/nginx/sites-available/
else
  echo "Nginx config directory missing!"
  exit 1
fi


# Create symbolic links if they don't exist
for conf in /etc/nginx/sites-available/api.conf /etc/nginx/sites-available/mlflow.conf; do
  name=$(basename "$conf")
  if [ ! -f "/etc/nginx/sites-enabled/$name" ]; then
    ln -s "$conf" "/etc/nginx/sites-enabled/$name"
  fi
done

# Create required directories
mkdir -p /opt/mlflow/artifacts
chown -R www-data:www-data /opt/mlflow

# Create required directories
mkdir -p /opt/prodizy-platform/db
chown -R www-data:www-data /opt/prodizy-platform/db

# Reload Nginx to apply changes
sudo nginx -t && sudo systemctl reload nginx

# Setup SSL certificates if needed
if [ ! -f "/etc/letsencrypt/live/app.sindle.online/fullchain.pem" ]; then
  echo "Requesting SSL certificates..."
  sudo certbot --nginx -d api.sindle.online -d mlflow.sindle.online --non-interactive --agree-tos -m admin@sindle.online
fi
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx") | crontab -
