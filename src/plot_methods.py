from scipy.io import loadmat

import gravis as gv

import streamlit as st
import streamlit.components.v1 as components

import json
from os import path

from geemap import save_colorbar
import geemap.colormaps as cm
import cv2
from os.path import realpath, join, dirname
from PIL import Image

data_dir= realpath(join(dirname(__file__), 'data'))


#todo: agregar about en sidebar
#todo: agregarle un boton para que se pueda descargar el grafo como json
#todo: tomar json como entrada
#todo: investigar sobre la representacion con forma de cerebro


def load_json(file:str):
    data = json.load(open(file))
    return data

def load_mat(file:str):
    return loadmat(file)


#check: not tested
def save_json(file:str, data:dict):
    with open(file, 'w') as outfile:
        json.dump(data, outfile)


#todo: add new names
def get_math_data(data:dict, linkLag:str, valLag:str, new_names: dict):
    newdata= dict()
    count=0
    linkl= linkLag + str(count)
    vall= valLag + str(count)
    linkval= []

    while linkl in data and vall in data:
        linkval.append((linkl, vall))
        newdata[linkl]= {}
        newdata[vall]= []

        for row, data_row in enumerate(data[linkl]):
            for column, data_column in enumerate(data_row):
                if data_column != 0:
                    newdata[linkl][new_names[row + 1]]= {}
                    newdata[vall].append({'source': new_names[row + 1], 'target': new_names[column + 1], 'weight': data[vall][row][column]})
        count+=1
        linkl= linkLag + str(count)
        vall= valLag + str(count)
    
    graphdict= {
        'graph': {
            'directed': False,
            'metadata': {},

            'nodes': {},
            'edges': [],
        }
    }
    
    link, val= linkval[0]
    for node in newdata[link]:
        graphdict['graph']['nodes'][node]= {'metadata': {'label': str(node), 'title': str(node), 'opacity': 0.7, 'border_color': 'black', 'border_size': 2, 'color': 'gray'}}
    
    edges= set()
    edge_colors1= colors([c['weight'] for c in newdata[val]])
    for edge in newdata[val]:
        if not (edge['source'], edge['target']) in edges or not (edge['target'], edge['source']) in edges:
            graphdict['graph']['edges'].append({'source': edge['source'], 'target': edge['target'], 'metadata': {'color': edge_colors1[edge['weight']], 'hover': str(round(float(edge['weight']), 4))}})
            edges.add((edge['source'], edge['target']))
            edges.add((edge['target'], edge['source']))
        


    digraphdict= {
        'graph': {
            'directed': True,
            'metadata': {},

            'nodes': {},
            'edges': [],
        }
    }
    edges= dict()
    for link, val in linkval[1:]:
        for node in newdata[link]:
            digraphdict['graph']['nodes'][node]= {'metadata': {'label': str(node), 'title': str(node), 'opacity': 0.7, 'border_color': 'black', 'border_size': 2, 'color': 'gray'}}
    
        for edge in newdata[val]:
            if edges.get((edge['source'], edge['target'])):
                edges[(edge['source'], edge['target'])].append({'weight':edge['weight'], 'lags':val[len(valLag):]})
            else:
                edges[(edge['source'], edge['target'])]= [{'weight':edge['weight'], 'lags':val[len(valLag):]}]

    
    for edge in edges:

        if edge[0] != edge[1]:
            #todo: add color
            lags= ','.join([e['lags'] for e in edges[edge]])
            w= sum([e['weight'] for e in edges[edge]])/len(edges[edge])
            digraphdict['graph']['edges'].append({'source': edge[0], 'target': edge[1], 'metadata': {'color': w, 'label':lags, 'hover': str(round(float(w), 4))}})
            node = edge[1]
            digraphdict['graph']['nodes'][node]= {'metadata': {'label': str(node), 'title': str(node), 'opacity': 0.7, 'border_color': 'black', 'border_size': 2, 'color': 'gray'}}

    edge_colors2= colors([c['metadata']['color'] for c in digraphdict['graph']['edges']])
    for edge in digraphdict['graph']['edges']:
        edge['metadata']['color']= edge_colors2[edge['metadata']['color']]

    edge_colors= dict()
    edge_colors.update(edge_colors1)
    edge_colors.update(edge_colors2)
    return graphdict, digraphdict, edge_colors



def get_nodes_graph(G: dict, nodes: list):
    '''
    Get a subgraph of G containing only the nodes in nodes
    :param G: Graph
    :type G: Graph
    :param nodes: List of nodes
    :type nodes: list
    :return: Subgraph
    :rtype: Graph
    '''
    if G['graph']['directed']:
        newG = {
            'graph': {
                'metadata': {},
                'directed': True,
                'nodes': {},
                'edges': [],
            }
        }
        for node in G['graph']['nodes']:
            if node in nodes:
                newG['graph']['nodes'][node]= G['graph']['nodes'][node]

        for edge in G['graph']['edges']:
            if newG['graph']['nodes'].get(edge['source']):
                newG['graph']['edges'].append(edge)
                newG['graph']['nodes'][edge['source']]= G['graph']['nodes'][edge['source']]
                newG['graph']['nodes'][edge['target']]= G['graph']['nodes'][edge['target']]
    
    else:
        newG = {
            'graph': {
                'metadata': {},
                'directed': False,
                'nodes': {},
                'edges': [],
            }
        }
        for node in G['graph']['nodes']:
            if node in nodes:
                newG['graph']['nodes'][node]= G['graph']['nodes'][node]

        for edge in G['graph']['edges']:
            if edge['source'] in nodes:
                newG['graph']['edges'].append(edge)
                newG['graph']['nodes'][edge['source']]= G['graph']['nodes'][edge['source']]
                newG['graph']['nodes'][edge['target']]= G['graph']['nodes'][edge['target']]

    return newG



def get_new_names(rename_file: str) -> dict:
    #todo: get .mat of new names
    #todo: return a dict with {<old name>: <new name>}
    return {i:i for i in range(1, 361)}

def get_graphs(file:str, linkLag:str, valLag:str, rename_file:str=None):
    _, extension= path.splitext(file.name)

    if extension == '.mat':
        Gdict, Gdidict, edge_colors = get_math_data(load_mat(file), linkLag, valLag, get_new_names(rename_file))
        sorted_colors= sorted([(round(float(color), 4), edge_colors[color]) for color in edge_colors], key=lambda x: x[0])
        

    if extension == '.json':
        data= load_json(file)
        Gdict, Gdidict = None
        #todo: add .json input
    
    return {'Gdict': Gdict, 'Gdidict': Gdidict, 'Edge Colors': sorted_colors}


def add_colorbar(colors: list):

    colorbar_dir= realpath(join(data_dir, 'colorbar.png'))
    graph_dir= realpath(join(data_dir, 'graph.png'))

    max, min = find_max_min_w([color[0] for color in colors])

    save_colorbar(colorbar_dir,
                width= 1.5, height=15,
                tick_size= 20,
                vmin=min, vmax= max,
                palette=cm.palettes.fromkeys(['#0000ff', '#ffc8c8', '#ff0000']),
                discrete=False,
                show_colorbar=False,
                orientation='vertical')
    
    graph_img= cv2.imread(graph_dir)
    colorbar_img = cv2.imread(colorbar_dir)

    gh, gw, _ = graph_img.shape
    ch, cw, _ = colorbar_img.shape

    for a, x in zip(range(gh-ch, gh), range(0, ch)):
        for b, y in zip(range(gw- cw, gw), range(0, cw)):
            graph_img[a][b]= colorbar_img[x][y]

    cv2.imwrite(join(data_dir,'graph_colorbar.jpg'), graph_img)



def brain_3d_graph(G: dict):
    newG= {
        'graph': {
            'nodes': {},
            'edges': [],
        }
    }
    newG['graph']['metadata']= G['graph']['metadata']
    newG['graph']['directed']= G['graph']['directed']
    data= load_json(join(data_dir, 'brain_3d.json'))
    for node in G['graph']['nodes']:
        newG['graph']['nodes'][node]= G['graph']['nodes'][node]
        newG['graph']['nodes'][node]['metadata']['x']= float(data[str(node)]['x'])*3
        newG['graph']['nodes'][node]['metadata']['y']= float(data[str(node)]['y'])*3
        newG['graph']['nodes'][node]['metadata']['z']= float(data[str(node)]['z'])*3
    for edge in G['graph']['edges']:
        newG['graph']['edges'].append(edge)
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


def _int_to_hexa_rgb(n: int, pos : bool = True):  
    n = str(hex(n))[2:]  if n > 15 else "0" + str(hex(n))[2:]
    return ('#' + 'ff' + n + n) if pos else ('#' + n + n + 'ff')


def _get_posmin_posmax_neqmin_neqmax(l:list):
    '''
    Get the positive and a negative min and max of a list
    :param l: List
    :return: Position of the min, position of the max, position of the min < 0, position of the max < 0
    :rtype: tuple
    '''
    posmin= 2^31
    posmax= 0
    neqmin= 0
    neqmax = -2^32
    for i in range(len(l)):
        if l[i] >= 0:
            if l[i] < posmin:
                posmin= l[i]
            if l[i] > posmax:
                posmax= l[i]
        else:
            if l[i] < neqmin:
                neqmin= l[i]
            if l[i] > neqmax:
                neqmax= l[i]        
    return posmin, posmax, neqmin, neqmax


def colors(wlist: list):
    d = dict()
    posmin, posmax, neqmin, neqmax=_get_posmin_posmax_neqmin_neqmax(wlist)
    posrange = posmax if (abs(posmax - posmin) < 10e-10) else posmax - posmin
    neqrange = neqmax if (abs(neqmax - neqmin) < 10e-10) else neqmax - neqmin
    for w in wlist:
        if w >= 0:
            d[w] = _int_to_hexa_rgb(int((1-((w-posmin)/posrange))*200),True)
        else:
            d[w] = _int_to_hexa_rgb(int((((w-neqmin)/neqrange))*200), False)
    return d
