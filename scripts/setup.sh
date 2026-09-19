#!/bin/bash
set -e

echo "Starting Linux server setup..."

# Update package lists and install nginx
apt-get update -qq
apt-get install -y -qq nginx > /dev/null 2>&1
echo "nginx installed successfully."

# Create the setup log file
echo "Setup completed on $(date)" > /var/log/setup.log
echo "Setup log written to /var/log/setup.log."

# Create the appadmin user if it does not already exist
if id "appadmin" &>/dev/null; then
    echo "User appadmin already exists, skipping creation."
else
    useradd -r -s /bin/false appadmin
    echo "User appadmin created."
fi

echo "Linux server setup complete."
