## main file is jarvis.py :
still it is implementing to work according to a wakeword.

## currently voiceControl.py file is working fine without wakeword.
to check commands got by mqtt 
mosquitto_sub -h test.mosquitto.org -p 1883 -t "rhasspy/intent/recognized" -v

##

sudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# You might need to log out and log back in for the group change to take effect
newgrp docker


## the following is wrong
docker run -d -p 12101:12101 \
    --name rhasspy \
    --restart unless-stopped \
    -v "$HOME/.config/rhasspy/profiles:/profiles" \
    -v "/etc/localtime:/etc/localtime:ro" \
    --device /dev/snd:/dev/snd \
    rhasspy/rhasspy \
    --user-profiles /profiles \
    --profile en
##
## correct one:
docker run -d \
  --network=host \
  --name rhasspy \
  -v "$HOME/.config/rhasspy/profiles:/profiles" \
  rhasspy/rhasspy \
  --user-profiles /profiles \
  --profile en



## http://localhost:12101/



pip install sounddevice numpy scipy

####
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

sudo systemctl start mosquitto
####


pip install paho-mqtt


## to check commands got by mqtt 
mosquitto_sub -h test.mosquitto.org -p 1883 -t "rhasspy/intent/recognized" -v