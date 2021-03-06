#!usr/bin/env python
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

import Axon
from Axon.Component import component
import Axon.Ipc as Ipc

class EditorLogic(Axon.Component.component):
    Inboxes = {
        "inbox" : "Recieves messages saying which item is currently selected",
        "control" : "Not listened to yet - BUG",
        "changenode" : "Inbox where we recieve messages telling us to change a component",
        "newnode" : "Inbox where we recieve messages telling us to add a node",
        "delnode" : "Inbox where we recieve messages telling us to delete a node",
        "linknode" : "Inbox where we recieve messages telling us to form links",
        "unlinknode" : "Inbox where we recieve messages telling us to break links",
        "go" : "Inbox where we receive messages telling us to start the components",
    }
    Outboxes = {
        "outbox" : "passthrough of messages received from the topology viewer",
        "signal" : "We don't do anything here yet",
        "commands" : "where messages to control a sandbox go",
        "componentedit" : "instructions to component editor",
    }
    def main(self):
        node = None
        linkstart = None
        linkmode = False
        n=1
        while 1:
            yield 1
            #
            # This really looks like a bunch of composite components operating on shared state.
            # Leads to an interesting question - how can we use this to our advantage - we
            # "clearly" can, but the question is "how" ?
            # One thing that's very clear here is this - even if these are all operating on shared
            # state, there's one thing that *must* be true - these components must NOT operate
            # concurrently.
            #
            # (Hmm... Sequential code on shared state defaulting to preclude concurrency? Makes
            # sense thinking about it)
            #
            # Hmmm. Further thought - this is akin to the idea of multiple mains run sequentially
            # inside a component. What if those "mains" are sequential sub-component mixins?
            #
            # This aspect is //similar// to the exogenous connectors idea.
            #
            if self.dataReady("inbox"):
                cmd = self.recv("inbox")
                
                if (cmd[0], cmd[1]) == ("SELECT","NODE"):
                    new_node = cmd[2]
                    if new_node is not None:
                        node = new_node
                        if linkmode and linkstart is not None:
                            if linkmode=="MAKE":
                                self.send(("LINK", linkstart, node), "commands")
                            elif linkmode=="UNMAKE":
                                self.send(("UNLINK", linkstart, node), "commands")
                            else:
                                raise "Nooo!"
                            linkmode = False
                            linkstart = None
                # forward stuff on
                self.send(cmd, "outbox")

            if self.dataReady("changenode"):
                self.recv("changenode")
                if node is not None:
                    self.send( ("GET_NAME", "NODE", node), "componentedit")

            if self.dataReady("newnode"):
                self.recv("newnode")
                self.send( ("ADD", str(n), "Axon.Component:component()"), "commands")
                self.send( ("GET_NAME", "NODE", str(n)), "componentedit")
                n=n+1

            if self.dataReady("delnode"):
                self.recv("delnode")
                if node is not None:
                    self.send(("DEL", node), "commands")

            if self.dataReady("linknode"):
                self.recv("linknode")
                if node is not None:
                    linkstart = node
                    linkmode = "MAKE"

            if self.dataReady("unlinknode"):
                self.recv("unlinknode")
                if node is not None:
                    linkstart = node
                    linkmode = "UNMAKE"

            if self.dataReady("go"):
                self.recv("go")
                self.send( ("GO",), "commands")
       