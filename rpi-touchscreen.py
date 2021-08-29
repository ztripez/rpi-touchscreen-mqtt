#!/usr/bin/env python
import time
import subprocess
import paho.mqtt.client as mqtt
from rpi_backlight import Backlight
from urllib.request import urlopen
from urllib.error import URLError
from ft5406 import Touchscreen, TS_PRESS
import confuse
import socket
import json
hostname = socket.gethostname()
config = confuse.Configuration(hostname, __name__)
config.set_file('default_config.yaml')
base_topic = "rpi/screen/"+hostname
config_topic = "homeassistant/light/"+hostname +"/config"
ts = Touchscreen()
bl = Backlight()
def touch_handler(event, touch):
    if event == TS_PRESS:
        bl.power = True
        bl.brightness =255

for touch in ts.touches:
    touch.on_press = touch_handler

subprocess.call("DISPLAY=:0 xset s off", shell=True)
subprocess.call("DISPLAY=:0 xset -dpms", shell=True)

ts.run()
# Workaround
def wait_for_internet_connection():
    while True:
        try:
            response = urlopen('https://google.com',timeout=1)
            return
        except URLError:
            pass

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        client.subscribe(base_topic + "/#")
    else:
        print("Bad connection Returned code=",rc)

def config_light(client):
    topic = config_topic
    config_payload = json.dumps({
        "~": base_topic,
        "name": hostname,
        "unique_id": hostname + "_light",
        "cmd_t": "~/set",
        "stat_t": "~/state",
        "schema": "json",
        "brightness": True
    })
    client.publish(topic, config_payload, 0, True)
  

def on_message(client, userdata, msg):
    payload = json.loads(str(msg.payload.decode("utf-8")))
    topic = msg.topic
    print("Received message on topic '"
        + topic + "' with QoS " + str(msg.qos))

    if topic == base_topic + '/set':
        print("Set message received")

        # values = payload.split(',')
        if payload["state"] == 'ON':
            bl.power = True
            subprocess.call("DISPLAY=:0 xscreensaver-command -deactivate", shell=True)
        else:
            bl.power = False
            subprocess.call("DISPLAY=:0 xscreensaver-command -activate", shell=True)
        if 'brightness' in payload:
            print("State message received")
            bl.brightness = (payload['brightness']/255)*100
        # getStatus()
    elif topic ==  base_topic + '/state':
        state = "ON" if bl.power  else "OFF"
        brightness = (bl.brightness/100)*255
        state_payload = json.dumps({"state": state, "brightness": brightness})
        client.publish(topic, state_payload, 0, True)

        #subprocess.call("sudo killall kiosk.sh && sudo service lightdm restart", shell=True)

def getStatus():
    topic = base_topic + "/state"
    if bl.power:
        state = 'on'
    else:
        state = 'off'
    brightness = bl.brightness
    payload = state+","+str(brightness)
    print("Publishing " + payload + " to topic: " + topic + " ...")
    state_payload = json.dumps({"state": state, "brightness": brightness})
    client.publish(topic, state_payload, 0, True)

wait_for_internet_connection()
mqtt.Client.connected_flag=False#create flag in class
broker=config['mqtt']['host'].get()
client = mqtt.Client("dashboard")
client.username_pw_set(config['mqtt']['user'].get(), config['mqtt']['password'].get())            #create new instance
client.on_connect=on_connect  #bind call back function
client.on_message=on_message
client.loop_start()
print("Connecting to broker ",broker)
client.connect(broker)      #connect to broker
while not client.is_connected(): #wait in loop
    
    print("In wait loop")
    time.sleep(1)
config_light(client)
while 1:
    try:
        getStatus()

    except Exception as e:
        print("exception")
        print(e)
        log_file=open("log.txt","w")
        log_file.write(str(time.time())+" "+e.__str__())
        log_file.close()

    print("")
    time.sleep(10)
