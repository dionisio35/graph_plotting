import networkx as nx
from networkx import Graph

from scipy.io import loadmat

import gravis as gv

import streamlit as st
import streamlit.components.v1 as components



#fix: escala de colores de to_hexa_rgb
#todo: agregar colormap(se puede tomar la foto guardada y agregarselo despues en una opcion extra)

#todo: agregarle nombre a los nodos
#todo: separar el grafo dirigido en subgrafos(el no dirigido ya está separado, pero esa funcion no es valida para los dirigidos)
#todo: compactar el grafo para que sea mas legible
#todo: agregar metodos para separar los grafos en subgrafos

#fix: ajustar el gravis_vis para que se vea bien en streamlit
#fix: ajustar gravis three para que se vea bien en streamlit
#todo: tomar diferentes tipos de archivos de entrada

#todo: agregar about en sidebar

#todo: graficar solo un nodo y todos sus enlaces(recibir nombre de nodo)


def get_data_linkLag(datalink, dataval):
    '''
    Create a dictionary from two lists
    :param datalink: List of links
    :type datalink: list
    :param dataval: List of values
    :type dataval: list
    :return: Dictionary
    :rtype: dict
    '''
    rowcount=0
    newdata= dict()

    for row in datalink:
        rowcount+=1
        columncount=0

        for column in row:
            columncount+=1

            if column != 0:
                if newdata.get(rowcount):
                    newdata[rowcount][columncount]= dataval[rowcount-1][columncount-1]
                else:
                    newdata[rowcount] = {columncount: dataval[rowcount-1][columncount-1]}

    return newdata


def load_dict(file: str, linkLag: str, valLag: str):
    """
    Load a dictionary from a .mat file
    :param file: Path to the .mat file
    :type file: str
    :param linkLag: Name of the dictionary in the .mat file
    :type linkLag: str
    :param valLag: Name of the dictionary in the .mat file
    :type valLag: str
    :return: Dictionary
    :rtype: dict
    """
    data = loadmat(file)
    datalink = []

    for i in data[linkLag]:
        temp=[]
        for j in i:
            temp.append(j)
        datalink.append(temp)
    
    dataval = []
    for i in data[valLag]:
        temp=[]
        for j in i:
            temp.append(round(j, 4))
        dataval.append(temp)

    return get_data_linkLag(datalink, dataval)


def merge_lags(lags: list, n: int):
    newlag= dict()
    for i in range(n):
        for j in range(n):
            count= 1
            edge= []
            avg= 0
            for lag in lags:
                if lag.get(i) and lag[i].get(j) and i != j:
                    avg+= lag[i][j]
                    edge.append(str(count))
                count+=1
            if edge != []:
                if newlag.get(i) == None:
                    newlag[i]= {j: {'text': ','.join(edge), 'avg': avg/len(edge)}}
                else:
                    newlag[i][j]= {'text': ','.join(edge), 'avg': avg/len(edge)}
    return newlag


def make_directed_graph(file):
    G= nx.DiGraph()
    vallag_list= []
    elements= list(loadmat(file).keys())

    n=1
    while 'vallag'+str(n) in elements and 'linkLag'+str(n) in elements:
        vallag_list.append(('linkLag'+str(n), 'vallag'+str(n)))
        n+=1
    
    lag_dicts= []
    for lag in vallag_list:
        lag_dicts.append(load_dict(file, lag[0], lag[1]))

    lags_merged= merge_lags(lag_dicts, len(loadmat(file)[vallag_list[0][0]]))

    wlist=[]
    for node in lags_merged:
        for xnode in lags_merged[node]:
            wlist.append(lags_merged[node][xnode]['avg'])
    max, min= find_max_min_w(wlist)
    print(max, min)

    for node in lags_merged:
        G.add_node(node,
                label= str(node),
                title= str(node),
                opacity=0.7,
                border_color='black',
                border_size=2,
                color= 'gray')
        for xnode in lags_merged[node]:
            G.add_node(xnode,
                label= str(node),
                title= str(node),
                opacity=0.7,
                border_color='black',
                border_size=2,
                color= 'gray')
            
            G.add_edge(node, xnode,
                    color= to_hexa_rgb(lags_merged[node][xnode]['avg'], max, min),
                    label= lags_merged[node][xnode]['text'],
                    arrow_color= to_hexa_rgb(lags_merged[node][xnode]['avg'], max, min))
    return G


def make_graph_lag0(file: str):
    '''
    Create a graph from a .mat file
    :param file: Path to the .mat file
    :type file: str
    :return: Graph
    :rtype: Graph
    '''
    G:Graph= Graph()
    linkl= load_dict(file, 'linkLag0', 'vallag0')

    wlist=[]
    for node in linkl:
        for xnode in linkl[node]:
            wlist.append(linkl[node][xnode])
    max, min= find_max_min_w(wlist)
    print(max, min)

    for node in linkl:
        G.add_node(node,
                label= str(node),
                title= str(node),
                opacity=0.7,
                border_color='black',
                border_size=2,
                color= 'gray')
        for xnode in linkl[node]:
            G.add_edge(node, xnode, color= to_hexa_rgb(linkl[node][xnode], max, min))
    return G


def make_separated_graphs(G: Graph):
    '''
    Separate the graph G in subgraphs and return a list of graphs
    :param G: Graph created with networkx
    :type G: Graph
    :return: List of subgraphs
    :rtype: list
    '''
    Glist = separate_graphs(G)
    biggest_graph: Graph = find_biggest_graph(Glist)
    if biggest_graph.number_of_nodes() > G.number_of_nodes() / 2:
        for graph in Glist:
            if graph == biggest_graph:
                Glist.remove(graph)
        Gnew= merge_graphs(Glist)
        return [biggest_graph, Gnew]
    
    return G


def separate_graphs(G: Graph):
    '''
    Separate the graph G in subgraphs
    :param G: Graph created with networkx
    :type G: Graph
    :return: List of subgraphs
    :rtype: list
    '''
    return [G.subgraph(c).copy() for c in nx.connected_components(G)]


def merge_graphs(Glist: list):
    '''
    Merge a list of graphs into one graph
    :param Gs: List of graphs
    :type Gs: list
    :return: Graph
    :rtype: Graph
    '''
    G = nx.Graph()
    for g in Glist:
        G = nx.compose(G, g)
    return G


def find_biggest_graph(Glist: list):
    '''
    Find the biggest graph in a list of graphs
    :param Gs: List of graphs
    :type Gs: list
    :return: Graph
    :rtype: Graph
    '''
    Glist.sort(key=lambda x: len(x.nodes), reverse=True)
    return Glist[0]


def get_nodes_graph(G: Graph, nodes: list):
    '''
    Get a subgraph of G containing only the nodes in nodes
    :param G: Graph
    :type G: Graph
    :param nodes: List of nodes
    :type nodes: list
    :return: Subgraph
    :rtype: Graph
    '''
    newG= Graph()
    for node in nodes:
        newG.add_node(node)

    for edge in G.edges:
        if edge[0] in nodes or edge[1] in nodes:
            newG.add_edge(edge[0], edge[1])
    return newG

def find_max_min_w(wlist: list):
    max= 0
    min= 0
    for w in wlist:
        if w >= max:
            max= w
        if w <= min:
            min=w
    return max, min

def _to_hexa_rgb(n: int):    
    n= str(hex(n))[2:]
    return '#' + 'ff' + n + n


def to_hexa_rgb(n: int, max, min):
    '''
    Convert a number to a hexa color
    :param number: Number to convert
    :type number: int
    :return: Hexa color
    :rtype: str
    '''
    if(min < 0):
        max=max-min
        n=n-min
        min=0        
    range=max-min 
    colors = []
    color=int(abs(n-min)/range *200)+25
    colors.append(_to_hexa_rgb(color))
    return colors


# def to_hexa_rgb(number: int, max: int, min: int):
#     '''
#     Convert a number to a hexa color
#     :param number: Number to convert
#     :type number: int
#     :return: Hexa color
#     :rtype: str
#     '''
#     if number >= 0:
#         color= 255/max
#         n= int(abs(255 - color * number))
#         n= str(hex(n))[2:]
#         return '#' + 'ff' + n + n
#     else:
#         color= 255/min
#         n= int(abs(255 - color * number))
#         n= str(hex(n))[2:]
#         return '#' + n + 'ff' + n