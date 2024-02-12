#!/bin/bash

# Allow ssh using password: https://stackoverflow.com/questions/59533620/how-to-connect-to-gcp-vm-instance-with-password-using-ssh
## In /etc/ssh/sshd_config
## change -> PasswordAuthentication yes
## sudo service ssh restart
## sudo passwd
sudo apt update
sudo apt upgrade

sudo apt install vim git python3-pip
