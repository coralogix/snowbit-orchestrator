#!/bin/bash

apt-get update -y
apt-get install nginx -y

systemctl status nginx