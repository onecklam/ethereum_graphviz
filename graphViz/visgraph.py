import networkx as nx
from networkx.algorithms import community
import community as community_louvain
from unionfind import UnionFind
import datetime
import os
import curves
import numpy as np
import pygraphviz
from networkx.drawing.nx_agraph import to_agraph
from matplotlib import cm
from pymongo import MongoClient

# Convert string time into datetime
def timeStrToTime(timestr):
    try:
        return datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S")
    except:
        return datetime.datetime.strptime(timestr, "%Y-%m-%d")


# Determine start and end of time period
def compareTime(time1, time2):
    return time1.__ge__(time2)


def getRangeValue(value, v_range):
    tmpvalue = sorted(list(set(value)))
    values = np.linspace(v_range[0], v_range[1], len(tmpvalue) + 1)
    temdic = {}
    for i, val in enumerate(tmpvalue):
        temdic[val] = values[i]
    return np.asarray([temdic[i] for i in value])


class GraphWork:
    def readFile(self, fileName):
        G = nx.read_gexf(fileName, node_type=None, relabel=False, version="1.2draft")
        return G, G.number_of_nodes()

    def get_from_db(self, form_data):
        db = MongoClient()["ethereum_tx"]
        query = {
            "time_stamp": {
                "$gte": form_data["start_date"],
                "$lte": form_data["end_date"],
            },
            "$or": [
                {"from_name": {"$in": form_data["exchange_nodes"]}},
                {"to_name": {"$in": form_data["exchange_nodes"]}},
            ],
        }
        G = nx.DiGraph()
        graph_type = form_data["graph_type"]
        graph_type = graph_type.split("(")[1].split(")")[0].lower()
        if graph_type == "mfg":
            for edge in db["mfg_edges"].find(query):
                G.add_edge(
                    edge["from_name"],
                    edge["to_name"],
                    time_stamp=edge["time_stamp"].strftime("%Y-%m-%d"),
                    value_in_ether=edge["value_in_ether"],
                )
        elif graph_type == "cig":
            for edge in db["cig_edges"].find(query):
                G.add_edge(
                    edge["from_name"],
                    edge["to_name"],
                    time_stamp=edge["time_stamp"].strftime("%Y-%m-%d"),
                    value_in_ether=edge["number_of_calls"],
                )
        elif graph_type == "ccg":
            for edge in db["ccg_edges"].find(query):
                G.add_edge(
                    edge["from_name"],
                    edge["to_name"],
                    time_stamp=edge["time_stamp"].strftime("%Y-%m-%d"),
                    value_in_ether=0,
                )
        node_attr = {}
        for node in db["%s_nodes" % graph_type].find({"node_name": {"$in": list(G)}}):
            node_attr[node["node_name"]] = {"node_type": node["node_type"]}
        nx.set_node_attributes(G, values=node_attr)

        nx.write_gexf(G, "tmp.gexf")
        G, num = self.readFile("tmp.gexf")
        os.remove("tmp.gexf")
        return G, num

    # Set node attributes
    def addGNodesAttr(self, G, Attrs, attrName):
        Nodes = G.nodes()
        for i, values in enumerate(Attrs):
            for key in values:
                Nodes[key][attrName] = i

    # Get node attributes
    def getGNodesAttr(self, G, attrName):
        Attrs = nx.get_node_attributes(G, attrName)
        return Attrs

    # Get node attribute values
    def getGNodesAttrList(self, G, attrName):
        Attrs = [data[attrName] for node, data in G.nodes(data=True)]
        return Attrs

    # Get ranges of node attribute values
    def getGNodesAttrRange(self, G, attrName):
        Attrs = [data[attrName] for node, data in G.nodes(data=True)]
        return min(Attrs), max(Attrs)

    # Get ranges of edge attribute values
    def getGEdgesAttrRange(self, G, attrName):
        Attrs = [data[attrName] for source, target, data in G.edges(data=True)]
        return min(Attrs), max(Attrs)

    def getNodesData(self, G, nodesAttrs):
        nodesData = []
        for node, data in G.nodes(data=True):

            tmp = []
            for at in nodesAttrs:
                tmp.append(data[at])
            nodesData.append(tmp)
        return nodesData

    def getEdgesData(self, G, edgesAttrs):
        edgesData = []
        for source, target, data in G.edges(data=True):
            tmp = [source, target]
            for at in edgesAttrs:
                tmp.append(data[at])
            edgesData.append(tmp)
        return edgesData

    def InDegreeCentrality(self, G):
        score = nx.in_degree_centrality(G)
        nx.set_node_attributes(G, score, "InDegree")

    def OutDegreeCentrality(self, G):
        score = nx.out_degree_centrality(G)
        nx.set_node_attributes(G, score, "OutDegree")

    def DegreeCentrality(self, G):
        score = nx.degree_centrality(G)
        nx.set_node_attributes(G, score, "Degree")

    def BetweenessCentrality(self, G):
        score = nx.betweenness_centrality(G)
        nx.set_node_attributes(G, score, "Betweeness")

    def ClosenessCentrality(self, G):
        score = nx.closeness_centrality(G)
        nx.set_node_attributes(G, score, "Closeness")

    def PagerankCentrality(self, G):
        score = nx.pagerank(G, alpha=0.85)
        nx.set_node_attributes(G, score, "PageRank")

    def LouvainCommunity(self, G):
        score = community_louvain.best_partition(G.to_undirected())
        nx.set_node_attributes(G, score, "Louvain")

    def LabelPropagationCommunity(self, G):
        score = list(community.label_propagation_communities(G.to_undirected()))
        self.addGNodesAttr(G, score, "Label propagation")

    def UnionFindCommunity(self, G):
        Nodes = G.nodes()
        uf = UnionFind(Nodes)
        for source, target in G.edges():
            uf.union(source, target)
        components = uf.components()
        score = []
        for nodes in components:
            score.append(nodes)
        self.addGNodesAttr(G, score, "Union find")

    def setGNodesSize(self, G, attrName="InDegree", ranges=[5, 20]):
        value = self.getGNodesAttrList(G, attrName)
        value = getRangeValue(value, ranges)
        Nodes = G.nodes()
        sizes = []
        for n, v in zip(Nodes, value):
            Nodes[n]["Size"] = v
            sizes.append(v)
        return sizes

    def setGNodesColor(self, G, attrName="Louvain"):
        value = self.getGNodesAttrList(G, attrName)
        colorh = cm.Set1(np.arange(max(value) + 1) / float(max(value) + 1))
        Nodes = G.nodes()
        colors = []
        for n, v in zip(Nodes, value):
            color = colorh[v]
            Nodes[n]["Color"] = color
            colors.append(color)
        return colors

    def getNodesAttrNames(self, G):
        for node, data in G.nodes(data=True):
            keys = list(data.keys())
            break
        if "pos" in keys:
            keys.remove(pos)
        return keys

    def getEdgesAttrNames(self, G):
        for source, target, data in G.edges(data=True):
            keys = list(data.keys())
            break
        if "pos" in keys:
            keys.remove(pos)
        return keys

    def getNodeInfo(self, G, node, nodesAttrs):
        outstr = ""
        data = G.nodes()[node]
        for attr in nodesAttrs:
            outstr = outstr + "%s:%s\n" % (attr[1], data[attr[0]])
        return outstr

    # Get neighbors of a node
    def getSubGraphByNode(self, G, node):
        nodes = nx.dfs_preorder_nodes(G, node)
        SubG = G.subgraph(nodes)
        print("Nodes in sub graph:", type(SubG.nodes()))

        print("Number of nodes in sub graph:", SubG.number_of_nodes())

        print("Number of edges in sub graph:", SubG.number_of_edges())

    # Get neighbors of a node in a time range
    def getSubGraphByTimeRange(self, G, starttime, endtime, attrName="time_stamp"):
        nodes = np.array([])
        starttime = datetime.datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S")
        endtime = datetime.datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S")
        for source, target, data in G.edges(data=True):
            nowtime = timeStrToTime(data["time_stamp"])
            if compareTime(nowtime, starttime) and compareTime(endtime, nowtime):
                nodes = np.append(nodes, source)
                nodes = np.append(nodes, target)
        SubG = G.subgraph(np.unique(nodes))
        print("Nodes in sub graph:", type(SubG.nodes()))

        print("Number of nodes in sub graph:", SubG.number_of_nodes())

        print("Number of edges in sub graph:", SubG.number_of_edges())

    def graphFilter(self, data, dic):
        state = True
        for key, value in dic.items():
            v = value["value"]
            t = value["type"]
            d = data[key]
            if type(v) == list:
                if t == "time":
                    starttime = datetime.datetime.strptime(v[0], "%Y-%m-%d %H:%M:%S")
                    endtime = datetime.datetime.strptime(v[1], "%Y-%m-%d %H:%M:%S")
                    nowtime = timeStrToTime(d)
                    if compareTime(nowtime, starttime) and compareTime(
                        endtime, nowtime
                    ):
                        state = True
                    else:
                        state = False
                        return state
                elif t == "float":
                    if d >= v[0] and d <= v[1]:
                        state = True
                    else:
                        state = False
                        return state
                else:
                    if d not in v:
                        state = True
                    else:
                        state = False
                        return state
            else:
                if d == v:
                    state = True
                else:
                    state = False
                    return state
        return state

    # Get neighbors of a node by multiple filters
    def getSubGraphByFilter(self, G, filter_dic):
        if filter_dic == {"edges": {}}:
            return None
        filter_edges = filter_dic["edges"]

        # Filter by edge weight
        nodes = np.array([])
        if filter_edges != {}:

            for source, target, data in G.edges(data=True):
                state1 = True
                if "time_stamp" in filter_edges:
                    value = filter_edges["time_stamp"]
                    v = value["value"]
                    t = value["type"]
                    d = data["time_stamp"]
                    starttime = datetime.datetime.strptime(v[0], "%Y-%m-%d %H:%M:%S")
                    endtime = datetime.datetime.strptime(v[1], "%Y-%m-%d %H:%M:%S")
                    nowtime = timeStrToTime(d)
                    if compareTime(nowtime, starttime) and compareTime(
                        endtime, nowtime
                    ):
                        state1 = True
                    else:
                        state1 = False
                state2 = True
                if "value_in_ether" in filter_edges:
                    value = filter_edges["value_in_ether"]
                    v = value["value"]
                    t = value["type"]
                    d = data["value_in_ether"]
                    if d >= v[0] and d <= v[1]:
                        state2 = True
                    else:
                        state2 = False
                state3 = True
                if "label" in filter_edges:
                    value = filter_edges["label"]
                    v = value["value"]
                    t = value["type"]
                    if source in v or target in v:
                        state3 = True
                    else:
                        state3 = False
                if state1 and state2 and state3:
                    nodes = np.append(nodes, source)
                    nodes = np.append(nodes, target)
            SubG = G.subgraph(np.unique(nodes)).copy()

            print("Number of nodes in sub graph:", SubG.number_of_nodes())

            print("Number of edges in sub graph:", SubG.number_of_edges())

            return SubG
        else:
            return None

    def getNodesByType(self, G):
        return [
            [node]
            for node, data in G.nodes(data=True)
            if data["node_type"] == "exchange"
        ]

    def getGDatas(self, G):
        NodesData = [data for node, data in G.nodes(data=True)]
        EdgesData = [data for source, target, data in G.edges(data=True)]

    def pygraphviz_layout(self, G, prog="neato", bundle=False, root=None, args=""):
        if root is not None:
            args += "-Groot=%s" % root
        A = to_agraph(G)
        A.layout(prog=prog, args=args)
        node_pos = []
        node_pos_dic = {}
        edge_pos = []
        Nodes = G.nodes()
        Edges = G.edges()
        for n in G:

            node = pygraphviz.Node(A, n)
            try:
                xs = node.attr["pos"].split(",")
                npos = tuple(float(x) for x in xs)
            except:
                npos = (0.0, 0.0)
            node_pos_dic[n] = npos
            Nodes[n]["pos"] = npos
            node_pos.append(npos)
        if bundle:
            A.layout(prog="mingle")
            for source, target in Edges:
                edge = pygraphviz.Edge(A, source, target)
                edgepos = edge.attr["pos"]
                edgepos = edgepos.replace(u"\\", "")
                edgepos = edgepos.replace(u"\r", u"")
                edgepos = edgepos.replace(u"\n", u"")
                edgepos = edgepos.split(" ")
                tmp = []
                for i in edgepos:
                    if i != u"":
                        ss = i.split(",")
                        x = float(ss[0])
                        y = float(ss[1])
                        tmp.append((x, y))
                edge_pos.append(tmp)
                Edges[(source, target)]["pos"] = tmp
        else:
            for source, target in Edges:
                posb = node_pos_dic[source]
                pose = node_pos_dic[target]
                posmx = (posb[0] + pose[0]) / 2 + (pose[1] - posb[1]) / 4
                posmy = (posb[1] + pose[1]) / 2 + (posb[0] - pose[0]) / 4
                tmp = curves.curve3_bezier(
                    (posb[0], posb[1]), (posmx, posmy), (pose[0], pose[1])
                )
                edge_pos.append(tmp)
                Edges[(source, target)]["pos"] = tmp
        return node_pos, edge_pos
