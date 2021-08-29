from piKiosk import PiKiosk
import confuse
import socket
import asyncio
hostname = socket.gethostname()
config = confuse.Configuration(hostname, __name__)
config.set_file('default_config.yaml')
kiosk = PiKiosk(config)
asyncio.run(kiosk.start())