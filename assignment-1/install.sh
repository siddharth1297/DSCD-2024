#!/bin/bash

<<<<<<< HEAD
# Install rabbitmq and start
sudo apt install curl gnupg rabbitmq-server -y
sudo systemctl start rabbitmq-server
=======
# Install RabbitMQ
sudo apt update
sudo apt install python3-pip
python3 -m pip install pika
>>>>>>> remotes/origin/a1p3
