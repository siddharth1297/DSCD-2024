#!/bin/bash

# Install rabbitmq and start
sudo apt install curl gnupg rabbitmq-server -y
sudo systemctl start rabbitmq-server
