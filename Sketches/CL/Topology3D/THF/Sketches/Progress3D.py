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
"""\
=====================
General 3D Object
=====================
TODO
"""


import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from Display3D import Display3D
from Util3D import *
from Intersect3D import *
import Axon


class Progress3D(Axon.Component.component):
    Inboxes = {
       "inbox": "not used",
       "control": "ignored",
       "control3d": "receive Control3D commands here",
       "progress": "reveice progress updates here (float values)",
       
    }
    
    Outboxes = {
        "outbox": "not used",
        "display_signal" : "Outbox used for communicating to the display surface",
        # 3D status
        "position" : "send position status when updated",
        "rotation": "send rotation status when updated",
        "scaling": "send scaling status when updated"
    }
    
    def __init__(self, caption=None, position=None, margin=8, bgcolour = (244,244,244), fgcolour = (0,0,0), msg=None,
                key = None, transparent = False,
                fontsize = 50, pixelscaling = 100, thickness = 0.2, sidecolour = (200,200,244),
                size=None, pos = Vector(0,0,0), rot = Vector(0,0,0), scaling = Vector(1,1,1)):
        super(Progress3D, self).__init__()
        # 3D object initialisation
        self.size = size
        self.pos = pos
        self.rot = rot
        self.scaling = scaling
        self.transform = Transform()

        self.oldrot = Vector()
        self.oldpos = Vector()
        self.oldscaling = Vector()

        self.grabbed = 0

        # appearance        
        self.backgroundColour = bgcolour
        self.foregroundColour = fgcolour
        self.margin = margin
        self.key = key
        self.caption = caption
 
        self.sideColour = sidecolour

        #progress (1.0 is full)
        self.progress = 0.0        
                
        # variables for movement
        self.wiggle = Vector(0.1,0.1,0.1)
        self.wiggleadd = Vector(0.001, 0.001, 0.001)

        # prepare vertices for intersection test
        self.vertices = [ Vector(1, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1) ]

        # similar to Pygame component registration
        self.disprequest = { "3DDISPLAYREQUEST" : True,
#                                          "callback" : (self,"callback"),
                                          "events" : (self, "inbox"),
#                                          "size": self.size,
#                                          "pos": self.pos,
                                          "object": self }
                                          

    # Ray intersection test
    # returns the distance of the origin o to the point of intersection
    # if no intersection occurs, 0 is returned
    # Algorithm from "Realtime Rendering"
    def intersectRay(self, o, d):
        transformed = [self.transform.transformVector(v) for v in self.vertices]
        halfwidths = [float(self.size.x/2), float(self.size.y/2), float(self.size.z/2)]
        return Intersect3D.ray_OBB(o, d, self.pos, transformed, halfwidths)


    def applyTransforms(self):
        # generate new transformation matrix if needed
        if self.oldscaling != self.scaling or self.oldrot != self.rot or self.oldpos != self.pos:
            self.transform.reset()
            self.transform.applyScaling(self.scaling)
            self.transform.applyRotation(self.rot)
            self.transform.applyTranslation(self.pos)

            if self.oldscaling != self.scaling:
                self.send(self.scaling, "scaling")
                self.oldscaling = self.scaling.copy()

            if self.oldrot != self.rot:
                self.send(self.rot, "rotation")
                self.oldrot = self.rot.copy()

            if self.oldpos != self.pos:
                self.send(self.pos, "position")
                self.oldpos = self.pos.copy()


    def draw(self):
        glMatrixMode(GL_MODELVIEW)

        # set generated matrix
        glPushMatrix()
        glLoadMatrixf(self.transform.getMatrix())

        hs = self.size/2.0
        # draw faces 
#        glDisable(GL_DEPTH_TEST)
#        glDisable(GL_BLEND)

        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        # draw envelope
        glBegin(GL_QUADS)
        glColor4f(self.foregroundColour[0]/256.0, self.foregroundColour[1]/256.0, self.foregroundColour[2]/256.0, 0.8)
        # right
        glVertex3f(hs.x,hs.y,hs.z)
        glVertex3f(hs.x,-hs.y,hs.z)
        glVertex3f(hs.x,-hs.y,-hs.z)
        glVertex3f(hs.x,hs.y,-hs.z)
        # left
        glVertex3f(-hs.x,hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,-hs.z)
        glVertex3f(-hs.x,hs.y,-hs.z)
        # top
        glVertex3f(hs.x,hs.y,hs.z)
        glVertex3f(-hs.x,hs.y,hs.z)
        glVertex3f(-hs.x,hs.y,-hs.z)
        glVertex3f(hs.x,hs.y,-hs.z)
        # bottom
        glVertex3f(hs.x,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,-hs.z)
        glVertex3f(hs.x,-hs.y,-hs.z)
        glEnd()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        
        progw = self.size.x * self.progress
        
        # draw progress
        glBegin(GL_QUADS)
        glColor4f(self.sideColour[0]/256.0, self.sideColour[1]/256.0, self.sideColour[2]/256.0, 0.8)
        
        # front
        glVertex3f(-hs.x+progw,hs.y,hs.z)
        glVertex3f(-hs.x+progw,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,hs.z)
        glVertex3f(-hs.x,hs.y,hs.z)
        # back
        glVertex3f(-hs.x+progw,hs.y,-hs.z)
        glVertex3f(-hs.x+progw,-hs.y,-hs.z)
        glVertex3f(-hs.x,-hs.y,-hs.z)
        glVertex3f(-hs.x,hs.y,-hs.z)
        # right
        glVertex3f(-hs.x+progw,hs.y,hs.z)
        glVertex3f(-hs.x+progw,-hs.y,hs.z)
        glVertex3f(-hs.x+progw,-hs.y,-hs.z)
        glVertex3f(-hs.x+progw,hs.y,-hs.z)
        # left
        glVertex3f(-hs.x,hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,-hs.z)
        glVertex3f(-hs.x,hs.y,-hs.z)
        # top
        glVertex3f(-hs.x+progw,hs.y,hs.z)
        glVertex3f(-hs.x,hs.y,hs.z)
        glVertex3f(-hs.x,hs.y,-hs.z)
        glVertex3f(-hs.x+progw,hs.y,-hs.z)
        # bottom
        glVertex3f(-hs.x+progw,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,hs.z)
        glVertex3f(-hs.x,-hs.y,-hs.z)
        glVertex3f(-hs.x+progw,-hs.y,-hs.z)
        glEnd()

        glEnable(GL_BLEND)
#        glEnable(GL_DEPTH_TEST)

        glPopMatrix()
#        glEnable(GL_BLEND)
   
    
    def handleEvents(self):
        while self.dataReady("inbox"):
            for event in self.recv("inbox"):
                if event.movementMode:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button in [1,3] and self.intersectRay(Vector(0,0,0), event.dir) > 0:
                            self.grabbed = event.button
                        if event.button == 4 and self.intersectRay(Vector(0,0,0), event.dir) > 0:
                            self.pos.z -= 1
                        if event.button == 5 and self.intersectRay(Vector(0,0,0), event.dir) > 0:
                            self.pos.z += 1
                    if event.type == pygame.MOUSEBUTTONUP:
                        if event.button in [1,3]:
                            self.grabbed = 0
                    if event.type == pygame.MOUSEMOTION:
                        if self.grabbed == 1:
                            self.rot.y += float(event.rel[0])
                            self.rot.x += float(event.rel[1])
                            self.rot %= 360
                        if self.grabbed == 3:
                            self.pos.x += float(event.rel[0])/10.0
                            self.pos.y -= float(event.rel[1])/10.0
                            
                        
    def handleMovementCommands(self):
        while self.dataReady("control3d"):
            cmd = self.recv("control3d")
            if cmd.type == Control3D.POSITION:
                self.pos = cmd.amount
            if cmd.type == Control3D.REL_POSITION:
                self.pos += cmd.amount
            if cmd.type == Control3D.ROTATION:
                self.rot = cmd.amount
            if cmd.type == Control3D.REL_ROTATION:
                self.rot = (self.rot+cmd.amount)%360
            if cmd.type == Control3D.SCALING:
                self.scaling = cmd.amount
            if cmd.type == Control3D.REL_SCALING:
                self.scaling += cmd.amount


    def steadyMovement(self):
        self.rot += self.wiggle
        if self.wiggle.x >= 0.1 or self.wiggle.x <=-0.1:
            self.wiggleadd *= -1
        self.wiggle += self.wiggleadd


    def handleProgress(self):
         while self.dataReady("progress"):
            self.progress = self.recv("progress")
            if self.progress < 0.0: self.progress = 0.0
            if self.progress > 1.0: self.progress = 1.0
            

    def main(self):
        displayservice = Display3D.getDisplayService()
        self.link((self,"display_signal"), displayservice)
        self.send(self.disprequest, "display_signal");

        while 1:
#            for _ in self.waitBox("callback"): yield 1
#            self.display = self.recv("callback")

# There is no need for a callback yet
            
            yield 1
            self.handleProgress()
#            self.steadyMovement()
            
            self.handleEvents()
            self.handleMovementCommands()
            self.applyTransforms()
            self.draw()

# Later it might be a good idea to provide a set of drawing functions
# so the component developer does not need to know about opengl
# This way opengl could later easily be replaced by an other mechanism
# for drawing
# e.g. TOGRA


if __name__=='__main__':
    from Kamaelia.Util.ConsoleEcho import consoleEchoer
    from Display3D import *
    from Button3D import *
    from Scrollbar3D import *
    from Movement3D import *
    path1 = LinearPath3D([Vector(3,3,-20), Vector(4,0,-20), Vector(3,-3,-20), Vector(0,-4,-20), Vector(-3,-3,-20),Vector(-4,0,-20),  Vector(-3,3,-20),Vector(0,4,-20),  Vector(3,3,-20)], 1000)
    
    Display3D.overridePygameDisplay()

    PROGRESS = Progress3D(size = Vector(3, 0.5, 0.5), pos=Vector(0,-1,-10)).activate()    
    SCROLL = Scrollbar3D(size = Vector(3, 0.5, 0.5), pos=Vector(0,-2,-10)).activate()    
    
    SCROLL.link((SCROLL,"scroll"), (PROGRESS, "progress"))
        
    Axon.Scheduler.scheduler.run.runThreads()  
