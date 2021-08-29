from confuse.core import Configuration
import paho.mqtt.client as mqtt
from rpi_backlight import Backlight
from ft5406 import Touchscreen, TS_PRESS
import confuse
import socket
import json
import subprocess
import time
import asyncio
class PiKiosk:
    ts = Touchscreen()
    bl = Backlight()
    hostname: str = socket.gethostname()
    conf: Configuration
    client: mqtt.Client
    base_topic:str = "rpi/screen/{hostname}".format(hostname=hostname)
    config_topic:str = "homeassistant/light/{hostname}/config".format(hostname=hostname)
    def on_connect(self,client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            client.subscribe("{base_topic}/#".format(base_topic = self.base_topic))
        else:
            print("Bad connection Returned code=",rc)
    
    def on_set(self,payload):
        if payload["state"] == 'ON':
            self.bl.power = True
            subprocess.call("DISPLAY=:0 xscreensaver-command -deactivate", shell=True)
        else:
            self.bl.power = False
            subprocess.call("DISPLAY=:0 xscreensaver-command -activate", shell=True)
        if 'brightness' in payload:
            print("State message received")
            self.bl.brightness = (payload['brightness']/255)*100
        self.send_state()
    def send_state(self):
        state = "ON" if self.bl.power  else "OFF"
        brightness = (self.bl.brightness/100)*255
        state_payload = json.dumps({"state": state, "brightness": brightness})
        self.client.publish("{base_topic}/state".format(base_topic = self.base_topic), state_payload, 0, True)
    
    def on_message(self,client, userdata, msg):
        payload = json.loads(str(msg.payload.decode("utf-8")))
        if msg.topic == "{base_topic}/set".format(base_topic = self.base_topic):
            self.on_set(payload)
        #elif msg.topic == "{self.base_topic}/state":
        #    self.on_state(payload)
    def on_press(self,event: int, touch):
        if event == TS_PRESS:
            self.bl.power = True
            self.bl.brightness = 255
    def mqtt_light_config(self):
        config_payload = json.dumps({
                "~": self.base_topic,
                "name": self.hostname,
                "unique_id": self.hostname + "_light",
                "cmd_t": "~/set",
                "stat_t": "~/state",
                "schema": "json",
                "brightness": True
        })
        self.client.publish(self.config_topic, config_payload, 0, True)
    def __init__(self,config: Configuration):
        self.conf = config
        broker=config['mqtt']['host'].get()
        self.client = mqtt.Client(self.hostname)
        self.client.username_pw_set(config['mqtt']['user'].get(), config['mqtt']['password'].get()) 
        self.client.on_connect=self.on_connect  #bind call back function
        self.client.on_message=self.on_message
        self.client.connect(broker)      #connect to broker        
        self.client.loop_start()


        for touch in self.ts.touches:
            touch.on_press = self.on_press
    
    async def start(self):
        self.mqtt_light_config()
        self.send_state()
        tasks = map(asyncio.create_task, [self.loop()])
        #tasks = asyncio.create_task(self.loop)
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    async def loop(self):
        while True:
            self.send_state()
            await asyncio.sleep(1)