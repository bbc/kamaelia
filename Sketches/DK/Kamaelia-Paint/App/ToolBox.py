# -*- coding: utf-8 -*-
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
import pygame
import Axon
from Axon.Ipc import producerFinished, WaitComplete
from Kamaelia.UI.Pygame.Display import PygameDisplay
from Kamaelia.UI.Pygame.Button import Button
from ColourSelector import ColourSelector
from Slider import Slider
class ToolBox(Axon.Component.component):
    Inboxes = {"inbox"    : "Receive events from Pygame Display",
               "control"  : "For shutdown messages",
               "callback" : "Receive callbacks from Pygame Display",
               "buttons" : "Recieve interrupts from the buttons"
              }
              
    Outboxes = {"outbox" : "XY positions emitted here",
                "signal" : "For shutdown messages",
                "display_signal" : "Outbox used for communicating to the display surface"
               }
    def __init__(self, position=None, size=(500,500)):
        """x.__init__(...) initializes x; see x.__class__.__doc__ for signature"""
        super(ToolBox,self).__init__()
        self.size = size
        self.dispRequest = { "DISPLAYREQUEST" : True,
                           "callback" : (self,"callback"),
                           "events" : (self, "inbox"),
                           "size": self.size,
                           "transparency" : None }
        if not position is None:
            self.dispRequest["position"] = position
            
    def waitBox(self,boxname):
        """Generator. yields 1 until data ready on the named inbox."""
        waiting = True
        while waiting:
            if self.dataReady(boxname): return
            else: yield 1
    
    def main(self):
        """Main loop."""
        displayservice = PygameDisplay.getDisplayService()
        self.link((self,"display_signal"), displayservice)
        self.send( self.dispRequest,
                    "display_signal")
        for _ in self.waitBox("callback"): yield 1
        self.display = self.recv("callback")
        
        # tool buttons
        circleb = Button(caption="Circle",position=(10,10), msg = (("Tool", "Circle"),)).activate()
        eraseb = Button(caption="Eraser",position=(100,10), msg = (("Tool", "Eraser"),)).activate()
        lineb = Button(caption="Line",position=(10,50), msg = (("Tool", "Line"),)).activate()
        bucketb = Button(caption="Bucket",position=(10,90), msg = (("Tool", "Bucket"),)).activate()
        eyeb = Button(caption="Eyedropper",position=(10,130), msg = (("Tool", "Eyedropper"),)).activate()
        addlayerb = Button(caption="Add Layer",position=(10,540), msg = (("Layer", "Add"),)).activate()
        prevlayerb = Button(caption="<-",position=(80,540), msg = (("Layer", "Prev"),)).activate()
        nextlayerb = Button(caption="->",position=(110,540), msg = (("Layer", "Next"),)).activate()
        dellayerb = Button(caption="Delete",position=(140,540), msg = (("Layer", "Delete"),)).activate()
        self.link( (circleb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (eraseb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (lineb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (bucketb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (eyeb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (addlayerb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (prevlayerb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (nextlayerb,"outbox"), (self,"outbox"), passthrough = 2 )
        self.link( (dellayerb,"outbox"), (self,"outbox"), passthrough = 2 )
        colSel = ColourSelector(position = (10,170), size = (255,255)).activate()
        self.link( (colSel,"outbox"), (self,"outbox"), passthrough = 2 )
        SizeSlider = Slider(size=(255, 50), messagePrefix = "Size", position = (10, 460), default = 9).activate()
        self.link( (SizeSlider,"outbox"), (self,"outbox"), passthrough = 2 )
        AlphaSlider = Slider(size=(255, 10), messagePrefix = "Alpha", position = (10, 515), default = 255).activate()
        self.link( (AlphaSlider,"outbox"), (self,"outbox"), passthrough = 2 )
        self.drawBG()
        done = False
        while not done:
            if not self.anyReady():
                self.pause()
            yield 1
    def drawBG(self):
        self.display.fill( (255,255,255) )
if __name__ == "__main__":
    from Kamaelia.Chassis.Pipeline import Pipeline
    from Kamaelia.Util.Console import ConsoleEchoer
    Pipeline(ToolBox(size = (275,600)), ConsoleEchoer()).run()
    
   # ToolBox(size = (275,600)).activate()
    Axon.Scheduler.scheduler.run.runThreads()
        
        
        

