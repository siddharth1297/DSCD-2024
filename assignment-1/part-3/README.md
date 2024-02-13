# Part3: Building a YouTube-like application with RabbitMQ

## RabbitMQ

#### Install
$ sh ../install.sh; python -m pip install -r ../requirements.txt

#### RabbitMQ commands (for mac) 
brew services stop rabbitmq <br>
brew services start rabbitmq <br>
brew services info rabbitmq

#### RabbitMQ credentials (for mac)
usname = guest <br>
passwrd = guest <br>

### Install rabbitmq using following command for linux
sudo apt install curl gnupg -y <br>
sudo apt install rabbitmq-server -y <br>

### RabbitMQ commands 
sudo systemctl start rabbitmq-server <br>
sudo systemctl status rabbitmq-server <br>
sudo systemctl stop rabbitmq-server <br>

### For gcloud do this steps to connect with the remote rabbitmq server at .
#### change or add the file at rabbitmq-server /etc/rabbitmq/rabbitmq.conf by adding. <br>
loopback_users = none

#### Give the internal IP of the VM where rabbitmq is running.

## Design
There are two dedicated queue for communication between the server-user and server-youtuber.
Queue 'user_request' is dedicated for handling communication between user and server.
Queue 'youtuber_request' is dedicated for handling communication between user and youtuber.

For every youtuber create a queue with the name <youtubername>.

## Test
1. one-to-one
user: subscribe
youtuber: publish
user: listen
2. one-to-one

3. we can't delete the message form queue after it stored in the queue 
    problem: after unsubscribeing the youtuber from the user messege will delevired of the video of the youtuber if the youtuber has uploded any video when the user is not login.
