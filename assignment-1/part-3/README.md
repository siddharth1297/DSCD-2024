# Part3: Building a YouTube-like application with RabbitMQ

## RabbitMQ

#### Install
$ sh ../install.sh; python -m pip install -r ../requirements.txt

#### RabbitMQ commands(TODO: Make it for Linux) 
brew services stop rabbitmq
brew services start rabbitmq
brew services info rabbitmq

#### RabbitMQ credentials
usname = guest
passwrd = guest

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
