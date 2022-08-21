#!/bin/bash

docker stop instagram-scrapper-staging && docker rm instagram-scrapper-staging 
git pull origin dev
docker build -t instagram-scrapper-staging .
docker run -i --name instagram-scrapper-staging --restart unless-stopped -p 8090:8090 instagram-scrapper-staging
