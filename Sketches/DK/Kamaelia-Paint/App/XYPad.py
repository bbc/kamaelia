#!/usr/bin/env python
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
# TODO:
# * Convert to vectors?

"""
=============
XY Pad Widget
=============

An XY pad widget with a draggable, bouncing puck.  Pick up  data on the
"outbox" outbox to receive the position of the puck and messages indicating
when it has touched one of the sides.



Example Usage
-------------

Create an XY pad which redraws 60 times per second:

    from Kamaelia.Util.Clock import CheapAndCheerfulClock as Clock

    clock = Clock(float(1)/60).activate()
    xyPad = XYPad().activate()
    clock.link((clock, "outbox"), (xyPad, "newframe"))



How Does it Work?
-----------------

The component requests a display surface from the Pygame Display service
component. This is used as the surface of the XY pad.  It binds listeners for
mouse click and motion to the service.

The component works in one of two different modes, bouncing and non-bouncing.
This is specified upon initialization by the bouncingPuck argument.

In the bouncing mode the puck will continue to move once it has been set into
motion by a mouse drag.  If the mouse button remains down for longer than 0.1
seconds it is deemed to be a drag.  In the bouncing mode the component sends a
(message, 1) tuple to the "outbox" outbox each time the puck collides with one
of the sides.  The messages can be changed using the collisionMsg argument.
They default to "top", "right", "bottom", "left".

In the non-bouncing mode the puck remains stationary after it has been dragged.

Both modes send a (positionMsg, (x, y)) tuple to the "outbox" outbox if the
puck moves.

If the editable argument to the constructor is set to be false the pad will not
respond to mouse presses.

As well as being controlled by the mouse an XY pad can be controlled externally,
for example by a second XY pad.  Position and velocity messages received on the
"remoteChanges" inbox are used to change the motion of the puck.  Position
messages are of the form ("Position", (xPos, yPos)), and velocity messages are
of the form ("Velocity", (xVel, yVel)).

In order to allow communication between two XY pads the component outputs
position and velocity messages to the "localChanges" outbox.  By connecting the
"localChanges" outbox of one XY pad to the "remoteChanges" inbox of another,
the second pad can duplicate the motion of the first.

The XY pad only redraws the surface and updates the puck position when it
receives a message on its "newframe" inbox.  Note that although providing
messages more frequently here will lead to more frequent updates, it will also
lead to higher CPU usage.

The visual appearance of the pad can be specified by arguments to the
constructor.  The size, position and colours are all adjustable.

If a producerFinished or shutdownMicroprocess message is received on its
"control" inbox, it is passed on out of its "signal" outbox and the component
terminates.
"""

import time
import pygame
import Axon

from Axon.Ipc import producerFinished, WaitComplete
from Kamaelia.UI.Pygame.Display import PygameDisplay
from Kamaelia.UI.Pygame.Button import Button
from Kamaelia.Util.Clock import CheapAndCheerfulClock as Clock

class XYPad(Axon.Component.component):
    """\
    XYPad([bouncingPuck, position, bgcolour, fgcolour, positionMsg,
           collisionMsg, size]) -> new XYPad component.
    
    Create an XY pad widget using the Pygame Display service.  Sends messages
    for position and direction changes out of its "outbox" outbox.

    Keyword arguments (all optional):
    bouncingPuck -- whether the puck will continue to move after it has been
                    dragged (default=True)
    position     -- (x,y) position of top left corner in pixels
    bgcolour     -- (r,g,b) fill colour (default=(255,255,255))
    fgcolor      -- (r, g, b) colour of the puck and border
    messagePrefix -- string to be prepended to all messages
    positionMsg  -- sent  as the first element of a (positionMsg, 1) tuple when
                   the puck moves
    collisionMsg -- (t, r, b, l) sent as the first element of a
                    (collisionMsg[i], 1) tuple when the puck hits a side
                    (default = ("top", "right", "bottom", "left"))
    size         -- (w,h) in pixels (default=(100, 100))

    """
    Inboxes = {"inbox"    : "Receive events from Pygame Display",
               "remoteChanges"  : "Receive messages to alter the state of the XY pad",
               "control"  : "For shutdown messages",
               "callback" : "Receive callbacks from Pygame Display",
               "newframe" : "Recieve messages indicating a new frame is to be drawn",
               "buttons" : "Recieve interrupts from the buttons"
              }
              
    Outboxes = {"outbox" : "XY positions emitted here",
                "localChanges" : "Messages indicating change in the state of the XY pad emitted here",
                "signal" : "For shutdown messages",
                "display_signal" : "Outbox used for communicating to the display surface"
               }
   
    def __init__(self, bouncingPuck=True, position=None,
                 bgcolour=(255, 255, 255), fgcolour=(0, 0, 0),
                 messagePrefix = "",
                 positionMsg="Position",
                 colours="RG",
                 selectedColour = (0,0,0),
                 saturator=False,
                 slider = False,
                 alpha = False,
                 colourSelector = False,
                 collisionMsg = ("Top", "Right", "Bottom", "Left"),
                 size=(100, 100), editable=True):
        """
        x.__init__(...) initializes x; see x.__class__.__doc__ for signature
        """

        super(XYPad, self).__init__()

        self.size = size
        
        # Does the puck bounce around
        self.bouncingPuck = bouncingPuck
        # Is the puck currently bouncing around
        self.isBouncing = False
        self.selectedColour = selectedColour
        self.mouseDown = False
        self.clickTime = None
        self.mousePositions = []
        self.lastMousePos = (0, 0)
        self.colourSelector = colourSelector
        self.saturator = saturator
        self.puckRadius = 10
        self.puckPos = [self.size[0]/2, self.size[1]/2]
        self.puckVel = [0, 0]
        
        self.alpha = alpha
        self.selectedAlpha = 255
        self.slider = slider
        self.selectedSize = 3
        self.borderWidth = 5
        self.bgcolour = bgcolour
        self.fgcolour = fgcolour
        self.colours = colours

        self.messagePrefix = messagePrefix
        self.positionMsg = positionMsg
        self.collisionMsg = collisionMsg

        self.editable = editable

        self.dispRequest = {"DISPLAYREQUEST" : True,
                            "callback" : (self,"callback"),
                            "events" : (self, "inbox"),
                            "size": self.size,
                           }

        if position:
            self.dispRequest["position"] = position
    def waitBox(self, boxName):
        """Wait for a message on boxName inbox"""
        while 1:
            if self.dataReady(boxName):
                return
            else:
                yield 1
      
    def main(self):
        """Main loop."""
    #    pgd = PygameDisplay( width=300, height=550 ).activate()
     #   PygameDisplay.setDisplayService(pgd)

        displayservice = PygameDisplay.getDisplayService()
        self.link((self,"display_signal"), displayservice)

        self.send( self.dispRequest,
                    "display_signal")

        for _ in self.waitBox("callback"): yield 1
        self.display = self.recv("callback")

        # colour buttons
        if self.colourSelector:
            rgbutton = Button(caption="Red/Green",position=(10,170), msg = ("Colour", "RG")).activate()
            rbbutton = Button(caption="Red/Blue",position=(80,170), msg = ("Colour", "RB")).activate()
            gbbutton = Button(caption="Green/Blue",position=(145,170), msg = ("Colour", "GB")).activate()
            self.link( (rgbutton,"outbox"), (self,"buttons") )
            self.link( (rbbutton,"outbox"), (self,"buttons") )
            self.link( (gbbutton,"outbox"), (self,"buttons") )
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
            SizePicker = XYPad(size=(255, 50), bouncingPuck = False, position = (10, 480),
                     bgcolour=(0, 0, 0), fgcolour=(255, 255, 255), slider = True).activate()
            self.link( (SizePicker,"outbox"), (self,"outbox"), passthrough = 2 )
            AlphaPicker = XYPad(size=(255, 20), bouncingPuck = False, position = (10, 575),
                     bgcolour=(0, 0, 0), fgcolour=(255, 255, 255), slider = True, alpha = True).activate()
            self.link( (AlphaPicker,"outbox"), (self,"outbox"), passthrough = 2 )
        
        
        #clock - don't really need this
        FPS = 60
        clock = Clock(float(1)/FPS).activate()
        self.link((clock, "outbox"), (self, "newframe"))

      


        # Initial render so we don't see a blank screen
        self.drawBG()
      #  self.render()
        if self.editable:
            self.send({"ADDLISTENEVENT" : pygame.MOUSEBUTTONDOWN,
                       "surface" : self.display},
                      "display_signal")

            self.send({"ADDLISTENEVENT" : pygame.MOUSEBUTTONUP,
                       "surface" : self.display},
                      "display_signal")

            self.send({"ADDLISTENEVENT" : pygame.MOUSEMOTION,
                       "surface" : self.display},
                      "display_signal")

        done = False
        while not done:
            if not self.anyReady():
                self.pause()
            yield 1
            while self.dataReady("buttons"):
                bmsg = self.recv("buttons")
                if bmsg[0]=="Colour":
                    self.colours = bmsg[1]
                    self.drawBG()
                    
            while self.dataReady("control"):
                cmsg = self.recv("control")
                if (isinstance(cmsg, producerFinished)):
                    self.send(cmsg, "signal")
                    done = True

            while self.dataReady("inbox"):
                for event in self.recv("inbox"):

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.clickTime = time.time()
                        if self.slider:
                            self.sliderPos = event.pos[0]
                            self.drawBG()
                        if self.display.get_rect().collidepoint(*event.pos):
                            self.mouseDown = True
                            self.isBouncing = False
                            self.mousePositions = []
                            self.puckVel = [0, 0]
                            self.puckPos = list(event.pos)
                            self.lastMousePos = event.pos
                            self.send((self.messagePrefix + self.positionMsg,
                                       (float(self.puckPos[0])/self.size[0],
                                        float(self.puckPos[1])/self.size[1])),
                                      "localChanges")

                            self.send((self.messagePrefix + "Velocity",
                                       self.puckVel), "localChanges")
                                    

                    if event.type == pygame.MOUSEBUTTONUP:
                        if self.mouseDown:
                            if self.slider:
                                self.sliderPos = event.pos[0]
                                self.drawBG()
                            if (self.bouncingPuck and
                                time.time() - self.clickTime > 0.1):
                                # Click and drag
                                self.isBouncing = True
                                if len(self.mousePositions):
                                    for i in xrange(2):
                                        # Use the average of the last 50
                                        # relative mouse positions
                                        positions = [x[i] for x in self.mousePositions]
                                        self.puckVel[i] = sum(positions)
                                        self.puckVel[i] /= float(len(positions))
                            else:
                                # Just a click
                                self.puckVel = [0, 0]
                                self.render()
                            self.send((self.messagePrefix + "Velocity",
                                      self.puckVel), "localChanges")
                        self.mouseDown = False
                    
                    if event.type == pygame.MOUSEMOTION and self.mouseDown:
                        if self.slider:
                            self.sliderPos = event.pos[0]
                            self.drawBG()
                        if self.display.get_rect().collidepoint(*event.pos):
                            # We are dragging inside the display
                            # Keep a buffer of 50 mouse positions
                            if len(self.mousePositions) > 50:
                                del self.mousePositions[0]
                            relPos = []
                            for i in xrange(2):
                                relPos.append(event.pos[i] -
                                              self.lastMousePos[i])
                            self.mousePositions.append(relPos)
                            # Move the puck to where the mouse is and remember
                            # where it is
                            self.puckPos = list(event.pos)
                            self.lastMousePos = event.pos
                            self.send((self.messagePrefix + self.positionMsg,
                                       (float(self.puckPos[0])/self.size[0],
                                       float(self.puckPos[1])/self.size[1])),
                                      "localChanges")
                            self.render()

            if self.dataReady("remoteChanges"):
                bundle = self.recv("remoteChanges")
                # The action to take is given by the last section of the
                # OSC address - this should maybe be done by a component and
                # we just listen for ("Velocity", (xVel, yVel)) tuples
                action = bundle[0].split("/")[-1]
                if action == "Velocity":
                    if self.bouncingPuck:
                        self.puckVel =  bundle[1]
                        self.isBouncing = 1
                elif action == "Position":
                    for i in xrange(2):
                        self.puckPos[i] = self.size[i] * bundle[1][i]
                self.render()

            if self.dataReady("newframe"):
                # Time to render a new frame
                # Clear any backlog of render messages
                while self.dataReady("newframe"):
                    self.recv("newframe")

                # Change the direction of the puck if it hits a wall
                if self.isBouncing:
                    self.processCollisions()

                if self.isBouncing:
                    # Update the position
                    for i in xrange(2):
                        self.puckPos[i] += self.puckVel[i]
                    self.render()

    def processCollisions(self):
        """
        Detect whether the puck has collided with a wall, and change its
        direction appropriately
        """

        if self.puckPos[0] <= 0:
            # Left wall
            self.puckVel[0] *= -1
            self.send((self.messagePrefix + self.collisionMsg[3], 1), "outbox")
        if self.puckPos[0] >= self.size[0]:
            # Right wall
            self.puckVel[0]  *= -1
            self.send((self.messagePrefix + self.collisionMsg[1], 1), "outbox")
        if self.puckPos[1] <= 0:
            # Top wall
            self.puckVel[1] *= -1
            self.send((self.messagePrefix + self.collisionMsg[0], 1), "outbox")
        if self.puckPos[1] >= self.size[1]:
            # Bottom wall
            self.puckVel[1] *= -1
            self.send((self.messagePrefix + self.collisionMsg[2], 1), "outbox") 
    
    def drawBG(self):
        if self.slider:
            self.display.fill( (255,255,255) )
            pygame.draw.rect(self.display, (0,0,0),
                             self.display.get_rect(), 2)
        elif self.saturator:
            for y in range(0, self.size[0], self.size[0]/25):
                box = pygame.Rect(self.size[0]/2, y, 10, 10)
                pygame.draw.rect(self.display, (self.selectedColour[0],self.selectedColour[1],self.selectedColour[2],y), box, 0)
        elif self.colourSelector:
            if (self.colours == "RG"):
                for y in range(0, self.size[0], self.size[0]/25):
                    for x in range(0, self.size[1], self.size[1]/25):
                        box = pygame.Rect(x, y, 10, 10)
                        pygame.draw.rect(self.display, (x,y,0), box, 0)
            elif (self.colours == "RB"):
                for y in range(0, self.size[0], self.size[0]/25):
                    for x in range(0, self.size[1], self.size[1]/25):
                        box = pygame.Rect(x, y, 10, 10)
                        pygame.draw.rect(self.display, (x,0,y), box, 0)
            elif (self.colours == "GB"):
                for y in range(0, self.size[0], self.size[0]/25):
                    for x in range(0, self.size[1], self.size[1]/25):
                        box = pygame.Rect(x, y, 10, 10)
                        pygame.draw.rect(self.display, (0,x,y), box, 0)
        self.send({"REDRAW":True, "surface":self.display}, "display_signal")
    def render(self):
        """Draw the border and puck onto the surface"""
     #                    self.display.get_rect(), self.borderWidth)
        if self.colourSelector:
            if (self.colours == "RG"):
                self.selectedColour = (self.puckPos[0], self.puckPos[1], 0)
            elif (self.colours == "RB"):
                self.selectedColour = (self.puckPos[0], 0, self.puckPos[1])
            elif (self.colours == "GB"):
                self.selectedColour = (0, self.puckPos[0], self.puckPos[1])
            pygame.draw.rect(self.display, self.selectedColour,
                            self.display.get_rect(), self.borderWidth)
            self.send((("colour",self.selectedColour),), "outbox")
        if self.slider and not self.alpha:
          #  print float(self.size[1])/float(self.size[0])*self.sliderPos
            self.selectedSize = float(self.size[1])/float(self.size[0])*self.sliderPos
            self.send((("Size",self.selectedSize),), "outbox")
            box = pygame.Rect(self.sliderPos, 0, 5, self.selectedSize)
            pygame.draw.rect(self.display, (0,0,0),
                            box, 0)
        if self.slider and self.alpha:
           # print self.sliderPos
            self.selectedAlpha = self.sliderPos
            self.send((("Alpha",self.selectedAlpha),), "outbox")
            box = pygame.Rect(self.sliderPos, 0, 5, 20)
            pygame.draw.rect(self.display, (0,0,0),
                            box, 0)
        # Puck
   #     pygame.draw.circle(self.display, self.fgcolour,
    #                       [int(x) for x in self.puckPos], self.puckRadius)
        self.send({"REDRAW":True, "surface":self.display}, "display_signal")
        

if __name__ == "__main__":
    from Kamaelia.Util.Clock import CheapAndCheerfulClock as Clock
    from Kamaelia.Util.Console import ConsoleEchoer
    from Kamaelia.Chassis.Graphline import Graphline
    

    
  #  xyPad = XYPad().activate()
    xyPad2 = XYPad(size=(255, 255), bouncingPuck = False, position = (70, 0),
                   bgcolour=(0, 0, 0), fgcolour=(255, 255, 255),
                   positionMsg="p2").activate()
    ce = ConsoleEchoer().activate()
   # clock.link((clock, "outbox"), (xyPad, "newframe"))
   # xyPad.link((xyPad, "outbox"), (ce,"inbox"))
    xyPad2.link((xyPad2, "outbox"), (ce,"inbox"))
    Axon.Scheduler.scheduler.run.runThreads()  
    
# Licensed to the BBC under a Contributor Agreement: JT/DK
