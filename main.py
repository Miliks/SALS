#import machine
#import ubinascii
#WIFI_MAC = ubinascii.hexlify(machine.unique_id()).upper()
# Set  the Gateway ID to be the first 3 bytes of MAC address + 'FFFE' + last 3 bytes of MAC address
#GATEWAY_ID = WIFI_MAC[:6] + "FFFE" + WIFI_MAC[6:12]
#print('Device eui (LORA MAC): ', GATEWAY_ID)
from network import WLAN
import socket
import machine
import time
import struct
import json
import pycom
import binascii

wlan = WLAN(mode=WLAN.STA)
#wlan.connect("VodafoneMobileWiFi-FD0317", auth=(WLAN.WPA2, "9760742968"), timeout=5000)
wlan.connect("motoMi", auth=(WLAN.WPA2, "Miliks1975"), timeout=5000)

while not wlan.isconnected():
    machine.idle()
print("Connected to WiFi\n")

json_data = json.dumps ({ "node_id": "1", "value": [{"measure_time_stamp": "2022-8-03 10:25:43", "temp": "110", "humidity": "60", "ph1": 9.499279390327938, "ph2": 9.499279390327938, "ph3": 9.499279390327938,}]})
print (json_data)


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
url = '91.218.224.179'
host = '91.218.224.179'
port = 80
sockaddr = socket.getaddrinfo(url, 80) [0][-1]

s.connect(sockaddr)

print('socket connected')

headers =  """\
POST /sensordata/insertrecords HTTP/1.1
Content-Type: {content_type}\r
Content-Length: {content_length}\r
Host: {host}\r
Connection: close\r
\r\n"""

body = json_data
body_bytes = body.encode('ascii')
header_bytes = headers.format(
    content_type="application/json",
    content_length=len(body_bytes),
    host=str(host) + ":" + str(port)
).encode('iso-8859-1')

payload = header_bytes + body_bytes

s.sendall(payload)

time.sleep(1)
rec_bytes = s.recv(4096)
print("RESPONSE = " + str(rec_bytes))
print('end')
s.close()
