#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 British Broadcasting Corporation and Kamaelia Contributors(1)
#
# (1) Kamaelia Contributors are listed in the AUTHORS file and at
#     http://www.kamaelia.org/AUTHORS - please extend this file,
#     not this notice.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -------------------------------------------------------------------------
#
"""
==========
Encryptor 
==========
Encryptor encrypts the data on its inbox with the key. The key
is passed as constructor param or sent to its "keyevent" inbox

Example usage
-------------
key = "1234567890123456"
pipeline (
    chargen(),
    Encryptor(key),
    Decryptor(key),
    consoleEchoer()
).run()
    
How it works?
--------------
Encryptor uses xtea cipher for encryption. xtea is a block cipher whose block
size is 8 bytes and key length is 16 bytes. The data to be encrypted needs
to divided into fixed blocks. If the data is smaller than block size it is
padded 0x80 followed by null bytes. In case the last block contains the 0x80,
to avoid ambiguity, another block called MAGIC STRING (block size * chr(0x80))
is added. This indicates that the block before MAGIC STRING is not padded.
"""

#TODO
#to be able plugin different ciphers
#separate padding from encryption

import Axon
import struct
from Kamaelia.Community.AM.Kamaelia.KPIFramework.KPI.Crypto import xtea

class Encryptor(Axon.Component.component):
    """\   Encryptor([key]) -> new Enryptor component.
    Encrypts data and sends to outbox
    Keyword arguments:
    - key    -- key string (default="\0")
    """
    
    Inboxes = {"inbox" : "data packets",
               "keyevent": "key for encryption",
               "control" : "receive shutdown messages"}
    Outboxes = {"outbox" : "encrypted data packets",
                "signal" : "pass shutdown messages"}

    def __init__(self,key="\0"):
        """x.__init__(...) initializes x; see x.__class__.__doc__ for signature"""
        super(Encryptor,self).__init__()
        self.key = key


    def main(self):
        blocksize = 8
        #the format string used for padding
        fmtstr = '!'+ str(blocksize) +'s'
        #MAGIC_STRING indicates that its preceding block is not padded
        MAGIC_STRING = blocksize * chr(0x80)
        while 1:
            yield 1

            if self.dataReady("keyevent"):
                self.key = self.recv("keyevent")
                #print "key recieved at the encryptor",self.key

            if self.dataReady("inbox"):
                data = self.recv("inbox")
                #drop the data until key is available
                if self.key == "\0":
                    continue
                enc = ''
                i = 0
                #do padding if less than block size
                #Pad with 0x80 followed by zero (null) bytes
                datalen = len(data)
                #if the data contains more than one block
                if datalen > blocksize:
                    #encrypt all the blocks, there is no need for padding
                    for i in range(0, datalen-blocksize, blocksize):
                        block = data[i:i+blocksize]
                        enc = enc + xtea.xtea_encrypt(self.key,block)
                    i = i + blocksize
                #get the last block
                block = data[i:datalen]
                if len(block) == blocksize:
                    enc = enc + xtea.xtea_encrypt(self.key,block)
                    #if the last block contains 0x80 then add MAGIC_STRING
                    #to avoid ambiguity
                    if block.find(chr(0x80)) != -1:
                        enc = enc + xtea.xtea_encrypt(self.key,MAGIC_STRING)
                else:
                    #pad with 0x80 followed null bytes
                    block = struct.pack(fmtstr, block + chr(0x80))
                    enc = enc + xtea.xtea_encrypt(self.key,block)
                self.send(enc, "outbox")
