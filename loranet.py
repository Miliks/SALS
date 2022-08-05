#!/usr/bin/env python
##DEF: Importa i moduli necessari ed in particolare, dal modulo network importa LoRa e tutti i parametri di config.py
import config
from network import LoRa
import socket
import binascii
import struct
import time
import _thread
import pycom
import time

## Si definisce la classe LoraNet con sotto elencate tutte le funzioni e variabili appartententi alla class
class LoraNet:

## DEF: Dentro la classe LoraNet si definisce una funzione particolare detta "inizializzatore" o "metodo costruttore".
## all'interno dell'inizializzatore ( def __init__() ) si definisce prima l'istanza della classe indicata con "self" (se stesso) e tutte le altre
## proprietà (o attributi) che saranno passate a self: sleep_time, check_rx, frequency, dr, ecc.....
    def __init__(self, sleep_time, check_rx, frequency, dr, region, activation, device_class=LoRa.CLASS_C, auth = None):
        ## DEF: Le variabili sleep_time, check_rx, frequency, dr, ecc.. faranno riferimento allo stesso self 
        ## e sono definite "Variabili dell'istanza" e con la parola self si definisce la referenza a ciascuna istanza della classe.
        self.sleep_time = sleep_time
        self.check_rx = check_rx
        self.frequency = frequency
        self.dr = dr
        self.region = region
        self.device_class = device_class
        self.activation = activation
        self.auth = auth
        self.sock = None
        self._exit = False
        self.s_lock = _thread.allocate_lock()
        self.lora = LoRa(mode=LoRa.LORAWAN, region = self.region, device_class = self.device_class)
        self._process_ota_msg = None

## DEF: Crea un metodo (o funzione) chiamato "stop" a cui è passata l'instanza self che impostaerà la variabile "exit" come True
    def stop(self):
        self._exit = True

## DEF: Definisco una funzione chiamata "init" che aggiunge a self la variabile process_msg_callback
    def init(self, process_msg_callback):
        self._process_ota_msg = process_msg_callback

## DEF: Definisco la funzione "read_sleep_time" che fa capo a self e restituisce il valore della variabile di istanza sleep_time
    def read_sleep_time(self):
        return self.sleep_time

## DEF: Definisco la funzione "read_check_rx" che fa capo a self e restituisce il valore della variabile di istanza check_rx
    def read_check_rx(self):
        return self.check_rx

## DEF: Definisco una funzione chiamata "receive_callback" che aggiunge a self la variabile di istanza lora
    def receive_callback(self, lora):
        #callback on reception ack-sync
        events = lora.events()
        if events & LoRa.RX_PACKET_EVENT:
            rx, port = self.sock.recvfrom(256)
            #decode received meassage and extract sleep time
            rx_data = rx.decode()
            rx_sleep_time = int(rx_data.split(',')[1].split('.')[0])
            print('Ack/sync received. Decoded received sleep time', rx_sleep_time)
            self.sleep_time = rx_sleep_time
            self.check_rx = True
            if config.LED_ON:
                #toggle blue led, message received
                pycom.rgbled(0x0000FF) #blue
                print('Received, blue led on')

## DEF: Definisce una funzione chiamata "connect" in riferiment a self.
## Se la variabile activation è diversa da Lota.OTAA e Lora.ABP, interviene l'istruzione "raise" per segnalare l'errore
    def connect(self):
        if self.activation != LoRa.OTAA and self.activation != LoRa.ABP:
            raise ValueError("Invalid Lora activation method")

## DEF Se tramite la funzione "len" il numero di elementi nella variabile auth è < 3, allora restituisce l'errore
        if len(self.auth) < 3:
            raise ValueError("Invalid authentication parameters")

        self.lora.callback(trigger=LoRa.RX_PACKET_EVENT, handler=self.receive_callback)

## DEF: Se la variabile di istanza "activation" è su LoRa.OTAA, allora setta tre canali con anche i valori di data rate minimo e massimo.
## Altrimenti, setta solo un canale alla frequenza di 868100000 Hz con Data Rate minimo e massimo
        if self.activation == LoRa.OTAA:
            # set the 3 default channels to the same frequency
            self.lora.add_channel(0, frequency=self.frequency, dr_min=0, dr_max=5)
            self.lora.add_channel(1, frequency=self.frequency, dr_min=0, dr_max=5)
            self.lora.add_channel(2, frequency=self.frequency, dr_min=0, dr_max=5)
        else:
            # set the 3 default channels as per LoRaWAN specification
            self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
            self.lora.add_channel(1, frequency=868300000, dr_min=0, dr_max=5)
            self.lora.add_channel(2, frequency=868500000, dr_min=0, dr_max=5)

## DEF: Ciclo for che nella variabile "i" rimuove tutti i canali dea 3 a 16 con lora.remove_channel(i)
        # remove all the non-default channels
        for i in range(3, 16):
            self.lora.remove_channel(i)

        # authenticate with abp or ota
## DEF: Se i valori della variabile activation sono impostati su LoRa.OTAA, allora la variabile "self._authenticate_otaa" conterrà i valori
## della variabile self.auth. Viceversa sarà la variabile "self._authenticate_abp" a prendere i valori di self.auth.
        if self.activation == LoRa.OTAA:
            self._authenticate_otaa(self.auth)
        else:
            self._authenticate_abp(self.auth)

## DEF: Definizione di una variabile per la creazione del socket
        # create socket to server
        self._create_socket()

## DEF: Definisce una funzione chiamata "authenticate_otaa", aggiunge a self la variabile "auth_params" che contiene una tupla di 3 valori
    def _authenticate_otaa(self, auth_params):
        # create an OTAA authentication params

## DEF: Nella tupla di "auth_params", vengono selezionati i parametri in ordine di posizione [0],[1],[2]. Tramite la funzione "binascii.unhexlify"
## (importata dal modulo binascii), i valori sono trasformati da binari a esadecimali
        self.dev_eui = binascii.unhexlify(auth_params[0])
        self.app_eui = binascii.unhexlify(auth_params[1])
        self.app_key = binascii.unhexlify(auth_params[2])

## DEF: si definisce la variabile "self.lora.join" con un bound method, in quanto assume le funzioni e le variabili di self
        self.lora.join(activation=LoRa.OTAA, auth=(self.dev_eui, self.app_eui, self.app_key), timeout=0, dr=self.dr)
        while not self.lora.has_joined():
            time.sleep(2.5)
            print('Not joined yet...')

    def has_joined(self):
        return self.lora.has_joined()

## DEF: Definisce una funzione _authenticate_abp che assume i parametri da "auth_params" in rifermiento alla stessa istanza self
    def _authenticate_abp(self, auth_params):

## DEF: Nella tupla di "auth_params", vengono selezionati i parametri in ordine di posizione [0],[1],[2]. Tramite la funzione "binascii.unhexlify"
## (importata dal modulo binascii), i valori sono trasformati da binari a esadecimali
        # create an ABP authentication params
## DEF: Nella definizione della variabile "self.dev_addr", il modulo "struct.unpack" crea una tupla con un elemento partendo dal valore
## "binascii.unhexlify(auth_params[0])" e decomprimendo in base al formato indicato ">1"
        self.dev_addr = struct.unpack(">l", binascii.unhexlify(auth_params[0]))[0]
        self.nwk_swkey = binascii.unhexlify(auth_params[1])
        self.app_swkey = binascii.unhexlify(auth_params[2])

## DEF: si definisce la variabile "self.lora.join" con un bound method, in quanto assume le funzioni e le variabili di self
        self.lora.join(activation=LoRa.ABP, auth=(self.dev_addr, self.nwk_swkey, self.app_swkey))

## DEF: Definizione di una funzione per la creazione del socket e delle variabili che assumono i parametri da self    
    def _create_socket(self):
        # create a LoRa socket

## DEF: Creazione di un'istanza socket in cui sono stati passati i parametri di:
## - socket.AF_LORA: Si riferisce alla famiglia di indirizzi ipv4
## - socket.SOCK_RAW: Indica il tipo di socket usato e il numero di costanti
        self.sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
       # self.sock.sendall(json)
        # set the LoRaWAN data rate
        self.sock.setsockopt(socket.SOL_LORA, socket.SO_DR, self.dr)
        # make the socket non blocking
        self.sock.setblocking(False)

## DEF: Definizione della funzione per l'invio dei pacchetti con l'acquisizione dei parametri dall'istanza self
    def send(self, packet):
        with self.s_lock:
            #self.lora.nvram_restore()
            self.sock.send(packet)
            #self.lora.nvram_save()

            print('Sent data', packet)
            if config.LED_ON:
                # green led toggle on message sent
                pycom.rgbled(0x00FF00) #green
                print('Sent data, green led on')
               
