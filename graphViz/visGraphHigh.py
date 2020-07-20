# -*- coding: utf-8 -*-
import sys
import shutil
import os
import warnings

warnings.filterwarnings("ignore")


from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import numpy as np
import curves
import vispy.app.backends._pyqt4
from vispy import app, gloo
from vispy.visuals.collections import PointCollection, PathCollection
from vispy.visuals import ImageVisual, TextVisual
from vispy.visuals.transforms import STTransform
import vispy.io as io
from collections import Counter
import string, math
import time, codecs, json
from vispy.io import read_png
from visgraph import GraphWork


class PanZoomTransform(STTransform):
    """Pan-zoom transform

    Parameters
    ----------
    canvas : instance of Canvas | None
        The canvas to attch to.
    aspect : float | None
        The aspect ratio to apply.
    **kwargs : dict
        Keyword arguments to pass to the underlying `STTransform`.
    """

    def __init__(self, canvas=None, aspect=None, **kwargs):
        self._aspect = aspect
        self.attach(canvas)
        STTransform.__init__(self, **kwargs)
        self.on_resize(None)

    def attach(self, canvas):
        """Attach this tranform to a canvas

        Parameters
        ----------
        canvas : instance of Canvas
            The canvas.
        """
        self._canvas = canvas

        canvas.events.resize.connect(self.on_resize)
        canvas.events.mouse_wheel.connect(self.on_mouse_wheel)
        canvas.events.mouse_move.connect(self.on_mouse_move)

    @property
    def canvas_tr(self):
        return STTransform.from_mapping(
            [(0, 0), self._canvas.size],
            # [(-0.5*self._canvas.size[0], 0.5*self._canvas.size[0]), (0.5*self._canvas.size[1], -0.5*self._canvas.size[1])])
            [(-1, 1), (1, -1)],
        )

    def on_resize(self, event):
        """Resize handler

        Parameters
        ----------
        event : instance of Event
            The event.
        """
        if self._aspect is None:
            return
        w, h = self._canvas.size
        aspect = self._aspect / (w / h)
        self.scale = (self.scale[0], self.scale[0] / aspect)
        self.shader_map()

    def on_mouse_move(self, event):
        """Mouse move handler

        Parameters
        ----------
        event : instance of Event
            The event.
        """
        if event.is_dragging:
            dxy = event.pos - event.last_event.pos
            button = event.press_event.button

            if button == 2:
                dxy = self.canvas_tr.map(dxy)
                o = self.canvas_tr.map([0, 0])
                t = dxy - o
                self.move(t)
            """
            elif button == 2:
                center = self.canvas_tr.map(event.press_event.pos)
                if self._aspect is None:
                    self.zoom(np.exp(dxy * (0.01, -0.01)), center)
                else:
                    s = dxy[1] * -0.01
                    self.zoom(np.exp(np.array([s, s])), center)
            """
            self.shader_map()

    def on_mouse_wheel(self, event):
        """Mouse wheel handler

        Parameters
        ----------
        event : instance of Event
            The event.
        """

        center = self.canvas_tr.map(event.pos)
        self.zoom((1.25 ** event.delta[1],) * 2, center)
        self.shader_map()


class GraphHigh(QtWidgets.QWidget):
    """Widget defined in Qt Designer"""

    filter_signal = QtCore.Signal(object, object)
    neighbors_signal = QtCore.Signal(str, object)

    def __init__(self, parent=None):

        super(GraphHigh, self).__init__(parent)
        self.canvas = app.Canvas(size=(1800, 600), keys="interactive", show=False)
        gloo.set_viewport(0, 0, self.canvas.size[0], self.canvas.size[1])

        gloo.set_state("translucent", depth_test=False)

        # self.setObjectName("ThemeWidget")
        # self.setStyleSheet("QWidget#ThemeWidget{background:transparent;border: 0px;}")
        # self.canvas.native.setObjectName("ThemeWidget")
        # self.canvas.native.setStyleSheet("QWidget#ThemeWidget{background:transparent;border: 0px;}")
        self.filter_signal.connect(self.updateMarkerVisible)

        vbl = QtWidgets.QVBoxLayout()
        vbl.setSpacing(0)
        vbl.setContentsMargins(0, 0, 0, 0)
        vbl.addWidget(self.canvas.native)
        self.setLayout(vbl)

        gloo.clear(color="#231e1f")
        # gloo.set_state("translucent", depth_test=False,blend=True)
        self.canvas.show()
        self.pvertex = """
        varying float v_size;
varying vec4  v_color;
varying float v_linewidth;
varying float v_antialias;

// Main (hooked)
// ------------------------------------
void main (void)
{
    fetch_uniforms();

    v_size = size;
    v_color = color;

    gl_Position = $transform(vec4(position, 1));
    gl_PointSize = size + 2.0 * (1.0 + 1.5*1.0);
}
        """
        self.pfragment = """
        #include "markers/disc.glsl"
#include "antialias/filled.glsl"

// Varyings
// ------------------------------------
varying float v_size;
varying vec4  v_color;

// Main
// ------------------------------------
void main()
{
    vec2 P = gl_PointCoord.xy - vec2(0.5,0.5);
    float point_size = v_size  + 2. * (1.0 + 1.5*1.0);
    float distance = marker_disc(P*point_size, v_size);
    gl_FragColor = filled(distance, 1.0, 1.0, v_color);
}
        """
        self.lvertex = """
#include "misc/viewport-NDC.glsl"

// Externs
// ------------------------------------
// extern vec3  prev;
// extern vec3  curr;
// extern vec3  next;
// extern float id;
// extern vec4  color;
// extern float antialias;
// extern float linewidth;
// extern vec4 viewport;
//        vec4 transform(vec3 position);

// Varyings
// ------------------------------------
varying float v_antialias;
varying float v_linewidth;
varying float v_distance;
varying vec4  v_color;


// Main
// ------------------------------------
void main (void)
{
    // This function is externally generated
    fetch_uniforms();
    v_linewidth = linewidth;
    v_antialias = antialias;
    v_color     = color;

    // transform prev/curr/next
    vec4 prev_ = $transform(vec4(prev, 1));
    vec4 curr_ = $transform(vec4(curr, 1));
    vec4 next_ = $transform(vec4(next, 1));

    // prev/curr/next in viewport coordinates
    vec2 _prev = NDC_to_viewport(prev_, viewport.zw);
    vec2 _curr = NDC_to_viewport(curr_, viewport.zw);
    vec2 _next = NDC_to_viewport(next_, viewport.zw);

    // Compute vertex final position (in viewport coordinates)
    float w = linewidth/2.0 + 1.5*antialias;
    float z;
    vec2 P;
    if( curr == prev) {
        vec2 v = normalize(_next.xy - _curr.xy);
        vec2 normal = normalize(vec2(-v.y,v.x));
        P = _curr.xy + normal*w*id;
    } else if (curr == next) {
        vec2 v = normalize(_curr.xy - _prev.xy);
        vec2 normal  = normalize(vec2(-v.y,v.x));
        P = _curr.xy + normal*w*id;
    } else {
        vec2 v0 = normalize(_curr.xy - _prev.xy);
        vec2 v1 = normalize(_next.xy - _curr.xy);
        vec2 normal  = normalize(vec2(-v0.y,v0.x));
        vec2 tangent = normalize(v0+v1);
        vec2 miter   = vec2(-tangent.y, tangent.x);
        float l = abs(w / dot(miter,normal));
        P = _curr.xy + miter*l*sign(id);
    }

    if( abs(id) > 1.5 ) v_color.a = 0.0;

    v_distance = w*id;
    gl_Position = viewport_to_NDC(vec3(P, curr_.z/curr_.w), viewport.zw);

}
        """
        self.lfragment = """
#include "antialias/antialias.glsl"

// Varyings
// ------------------------------------
varying vec4  v_color;
varying float v_distance;
varying float v_linewidth;
varying float v_antialias;

// Main
// ------------------------------------
void main()
{
    if (v_color.a == 0.)  { discard; }
    gl_FragColor = stroke(v_distance, v_linewidth, v_antialias, v_color);
}
        """

    def draw_init(self, backgroundImg=False, fontsize=14, fontColor="white"):
        gloo.clear(color="#231e1f")
        # gloo.set_state("translucent", depth_test=False,blend=True)
        try:
            self.text.clear()
        except:
            pass
        self.selected_point = -1
        self.fontsize = fontsize
        panzoom = PanZoomTransform(self.canvas)

        if backgroundImg:
            self.im = read_png("timg.png")
            self.image = ImageVisual(self.im, method="subdivide")
            self.image.update = self.canvas.update
            self.image.transform = STTransform(
                scale=(2 / self.image.size[0], 2 / self.image.size[1]),
                translate=(-1, -1),
            )
        else:
            self.image = None

        self.markers = PointCollection(
            "agg",
            vertex=self.pvertex,
            fragment=self.pfragment,
            color="shared",
            size="local",
            transform=panzoom,
        )
        self.lines = PathCollection(
            mode="agg",
            vertex=self.lvertex,
            fragment=self.lfragment,
            color="shared",
            linewidth="global",
            transform=panzoom,
        )
        self.markers.update.connect(self.canvas.update)
        self.lines.update.connect(self.canvas.update)
        self.text = TextVisual(u"", color="white")

        self.text.font_size = self.fontsize
        self.text.visible = False
        self.textpos = None

        self.canvas.events.draw.connect(self.on_draw)
        self.canvas.events.resize.connect(self.on_resize)
        self.canvas.events.mouse_press.connect(self.on_mouse_press)
        self.canvas.show()

    def init_data2(self, filename):
        work = GraphWork()
        self.SubG = None
        self.G = work.readFile(filename)
        # Compute centrality measures
        work.DegreeCentrality(self.G)
        # Compute community measures
        work.LouvainCommunity(self.G)

        # Compute node sizes
        self.marksize = work.setGNodesSize(self.G)

        # Compute node colors
        self.colors = work.setGNodesColor(self.G)

        self.labels = work.getGNodesAttrList(self.G, "label")

        # Compute graph layout
        node_pos, edge_pos = work.pygraphviz_layout(self.G, prog="sfdp", bundle=False)

        # Number of nodes
        self.npts = self.G.number_of_nodes()
        # Number of edges
        self.nlinks = self.G.number_of_edges()

        print("aaaa")
        self.drawgraph(node_pos, edge_pos, self.colors, self.marksize)

    def init_data(self, G, marksize, colors, labels, node_pos, edge_pos, npts, nlinks):
        self.G = G
        self.SubG = None
        self.marksize = marksize
        self.colors = colors
        self.labels = labels
        # Number of nodes
        self.npts = npts
        # Number of edges
        self.nlinks = nlinks

        self.draw(node_pos, edge_pos, self.colors, self.marksize)

    def draw(self, pos, edges, colors, marksize):
        # Number of nodes
        self.npts = len(pos)
        # Number of edges
        self.nlinks = len(edges)

        self.colors = np.array(self.colors)
        self.marksize = marksize

        self.pos = np.array(pos)

        edges = np.array(edges)
        # Set node positions
        self.get_Range()
        self.pos = (self.pos - (self.width / 2, self.height / 2)) * (
            2 / self.width,
            2 / self.height,
        )
        self.pos = np.c_[self.pos, np.zeros(len(self.pos))]

        self.markers.append(self.pos, size=self.marksize)
        self.markers["color"] = self.colors

        # Set edge colors
        self.normal_selected_linecolor = np.array(
            [[0.86, 0.86, 0.86, 0.4], [1, 0, 0, 1], [0.86, 0.86, 0.86, 0.1]]
        )
        self.lineselected = np.zeros(self.nlinks, dtype=int)

        self.edges = []

        for i in edges:
            i = np.array(i)
            i = (i - (self.width / 2, self.height / 2)) * (
                2 / self.width,
                2 / self.height,
            )
            self.edges.append(i)
            tmp = np.c_[i, np.ones(len(i))]
            self.lines.append(tmp, itemsize=len(i))
        self.edges = np.array(self.edges)
        self.lines["color"] = (0.86, 0.86, 0.86, 0.6)
        self.lines["linewidth"] = 0.5
        self.selected_point = -1
        self.canvas.show()

    def get_Range(self):
        x = self.pos[:, 0]
        y = self.pos[:, 1]
        self.width = (x.max() - x.min()) * 1.05
        self.height = (y.max() - y.min()) * 1.05
        if x.max() == x.min():
            self.width = x.max() * 1.05
        if y.max() == y.min():
            self.height = y.max() * 1.05

    def on_draw(self, e):
        gloo.clear(color="#231e1f")
        if self.image:
            self.image.draw()

        self.lines.draw()
        self.markers.draw()
        try:
            self.text.draw()
        except:
            vp = (0, 0, self.canvas.physical_size[0], self.canvas.physical_size[1])
            self.canvas.context.set_viewport(*vp)
            self.markers["viewport"] = vp
            self.lines["viewport"] = vp
            self.text.transforms.configure(canvas=self.canvas, viewport=vp)
            self.text.draw()

        if self.textpos != None:
            npos = self.pos[self.textpos]

            npos = self.itransPos(npos)
            self.text.pos = [npos[0], npos[1]]

        self.canvas.update()

    def on_resize(self, event):
        vp = (0, 0, self.canvas.physical_size[0], self.canvas.physical_size[1])
        self.canvas.context.set_viewport(*vp)
        self.markers["viewport"] = vp
        self.lines["viewport"] = vp
        self.text.transforms.configure(canvas=self.canvas, viewport=vp)

    def transPos(self, pos):
        npos = self.markers.transform.canvas_tr.map(pos)
        npos = (npos - self.markers.transform.translate) / self.markers.transform.scale
        return npos

    def itransPos(self, pos):
        npos = [pos[0], pos[1], 0, 1]
        npos = self.markers.transform.canvas_tr.imap(
            npos * self.markers.transform.scale + self.markers.transform.translate
        )
        return npos

    def on_resize(self, event):
        vp = (0, 0, self.canvas.physical_size[0], self.canvas.physical_size[1])
        self.canvas.context.set_viewport(*vp)
        self.lines["viewport"] = vp
        self.markers["viewport"] = vp
        self.text.transforms.configure(canvas=self.canvas, viewport=vp)

    def on_mouse_press(self, event):
        if event.button == 1:
            if self.selected_point != -1:
                self.updateSubGVisible()
                self.selected_point = -1
            if self.selected_point == -1:
                width = self.canvas.physical_size[0]
                height = self.canvas.physical_size[1]
                pos = self.markers.transform.canvas_tr.map(event.pos)
                pos = (
                    pos - self.markers.transform.translate
                ) / self.markers.transform.scale
                D = self.pos - [pos[0], pos[1], 0]
                D = np.sqrt((D ** 2).sum(axis=1))
                self.selected_point = np.argmin(D)

                if D[self.selected_point] < 0.01:
                    self.colors[:, 3:4] = 1

                    nid = int(self.selected_point)
                    seleted = self.labels[nid]
                    self.updateMarkerVisible(seleted)
                else:
                    self.selected_point = -1
                    self.textpos = None
                    self.text.visible = False
                    if self.SubG is None:
                        self.neighbors_signal.emit("", None)
                    else:
                        self.neighbors_signal.emit("", [])

    def on_mouse_release(self, event):
        self.selected_point = -1

    def setSubG(self, SubG):
        self.SubG = SubG

    def updateSubGVisible(self):
        if self.SubG is None:
            self.colors[:, 3:4] = 1
            self.markers["color"] = self.colors
            self.lineselected[:] = 0
            self.lines["color"] = self.normal_selected_linecolor[self.lineselected]
            self.canvas.update()
        else:
            result = self.SubG.nodes()
            edges = self.SubG.edges()
            for i, n in enumerate(self.G.nodes()):
                if n not in result:
                    self.colors[i][3] = 0.0
                else:
                    self.colors[i][3] = 1.0

            self.markers["color"] = self.colors

            itemindex = []
            for i, edge in enumerate(self.G.edges()):
                if edge in edges:
                    itemindex.append(i)

            self.lineselected[:] = 2

            for i in itemindex:
                self.lineselected[i] = 1
            self.lines["color"] = self.normal_selected_linecolor[self.lineselected]
            self.canvas.update()

    def updateMarkerVisible(self, seleted):

        if self.SubG is None:
            G = self.G
            self.colors[:, 3:4] = 1
            self.markers["color"] = self.colors
            self.lineselected[:] = 0
            self.lines["color"] = self.normal_selected_linecolor[self.lineselected]
        else:
            G = self.SubG
            result = self.SubG.nodes()
            edges = self.SubG.edges()
            for i, n in enumerate(self.G.nodes()):
                if n not in result:
                    self.colors[i][3] = 0.0
                else:
                    self.colors[i][3] = 1.0

            self.markers["color"] = self.colors
        if seleted in G.nodes():
            nid = self.labels.index(seleted)
            self.selected_point = nid
            result = []
            nodes = G.nodes()
            for i, edge in enumerate(self.G.edges()):
                if seleted == edge[0] and edge[1] in nodes:
                    result.append(edge[1])
                if seleted == edge[1] and edge[0] in nodes:
                    result.append(edge[0])
            result = list(set(result))
            sss = self.getNodeInfo(G, seleted)
            self.neighbors_signal.emit(sss, result)
            for i, n in enumerate(self.G.nodes()):
                if n not in result:
                    self.colors[i][3] = 0.0

            self.colors[self.selected_point][3] = 1

            self.markers["color"] = self.colors
            self.text.text = seleted

            npos = self.pos[nid]
            npos = [npos[0], npos[1], 0, 1]
            npos = (
                npos * self.markers.transform.scale + self.markers.transform.translate
            )
            npos = self.markers.transform.canvas_tr.imap(npos)
            self.textpos = nid
            self.text.pos = [npos[0], npos[1]]
            self.text.visible = True

            itemindex = []
            edges = G.edges()
            for i, edge in enumerate(self.G.edges()):
                if seleted == edge[0] or seleted == edge[1]:
                    if edge in edges:
                        itemindex.append(i)

            self.lineselected[:] = 2

            for i in itemindex:
                self.lineselected[i] = 1
            self.lines["color"] = self.normal_selected_linecolor[self.lineselected]
            self.canvas.update()
        else:
            self.text.visible = False
            if self.SubG is None:
                self.neighbors_signal.emit("", None)
            else:
                self.neighbors_signal.emit("", [])

            self.selected_point = -1

    def getNodeInfo(self, G, node):
        nodesAttrs = [
            ("label", "Node name"),
            ("node_type", "Node type"),
            ("InDegree", "InDegree centrality"),
            ("OutDegree", "OutDegree centrality"),
            ("Degree", "Degree centrality"),
            ("Betweeness", "Betweenness centrality"),
            ("Closeness", "Closeness centrality"),
            ("PageRank", "PageRank centrality"),
            ("Louvain", "Louvain community"),
            ("Label propagation", "Label propagation community"),
            ("Union find", "Union find community"),
        ]
        outstr = ""
        data = G.nodes()[node]
        for attr in nodesAttrs:
            outstr = outstr + "%s: %s\n" % (attr[1], data[attr[0]])
        return outstr

    def updateMarkersColor(self, attrName):
        work = GraphWork()
        self.colors = work.setGNodesColor(self.G, attrName=attrName)
        self.colors = np.array(self.colors)
        if self.SubG is None:
            self.colors[:, 3:4] = 1
        else:
            result = self.SubG.nodes()
            for i, n in enumerate(self.G.nodes()):
                if n not in result:
                    self.colors[i][3] = 0.0
                else:
                    self.colors[i][3] = 1.0
        self.markers["color"] = self.colors
        self.canvas.update()

    def updateMarkersSize(self, attrName):
        work = GraphWork()
        self.marksize = work.setGNodesSize(self.G, attrName=attrName)
        for i in self.pos:
            self.markers.__delitem__(0)
        self.markers.append(self.pos, size=self.marksize)
        if self.SubG is None:
            self.colors[:, 3:4] = 1
        else:
            result = self.SubG.nodes()
            for i, n in enumerate(self.G.nodes()):
                if n not in result:
                    self.colors[i][3] = 0.0
                else:
                    self.colors[i][3] = 1.0
        self.markers["color"] = self.colors
        self.canvas.update()
