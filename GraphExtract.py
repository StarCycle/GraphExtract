import re
import json
import networkx as nx
import matplotlib.pyplot as plt
import pydot

def AddNode(graph, nodeID, myType, methodName, fileName, codeCountID = None):
    # Compute features of nodes
    methodNameFeature = [0]*26
    fileNameFeature = [0]*26
    if myType == 'Method':
        typeFeature = [0]
    elif myType == 'MethodReturn':
        typeFeature = [0.5]
    elif myType == 'CodeCount':
        typeFeature = [1]
    for char in methodName.lower():
        if ord(char) >= 97 and ord(char) <= 122:    # A character from 'a' to 'z'
            methodNameFeature[ord(char)-97] = 1
    for char in re.split(r'[\/\.]', fileName.lower())[-2]:
        if ord(char) >= 97 and ord(char) <= 122:    # A character from 'a' to 'z'
            fileNameFeature[ord(char)-97] = 1
    feature = typeFeature + methodNameFeature + fileNameFeature

    # Add the node to the graph
    graph.add_node(nodeID, feature=feature, myType=myType, methodName=methodName, fileName=fileName, codeCountID=codeCountID)

def DFS(startNodeID, methodGraph, programGraph, methodsByID, methodIndexByName):
    '''
    Looks for method and CodeCount nodes in the methodGraph, and add them (and their relations) to programGraph. 
    Directed edges between such nodes and other nodes are called "virtual edges", even if they are not directly connected in the methodGraph. 
    Input:
        startNodeID
        methodGraph         control flow graph of a single method
        methodsByID
        methodIndexByName   {'method name': [method node id1, method node id2, ...]}
                            Multiple methods may share the same name
    Output:
        programGraph        (part of) control flow graph of the whole program.
                            It contains 2 types of nodes, i.e., method and CodeCount
    '''
    visitedVirtualEdges = []
    virtualEdgesToVisit = [(startNodeID, startNodeID)]
    while True:
        if virtualEdgesToVisit == []:
            break
        lastNodeID, nodeID = virtualEdgesToVisit.pop()    # pop(-1) for depth first search
        visitedVirtualEdges.append((lastNodeID, nodeID))
        m = re.match(r'\"\(([\s\S]+?)\,([\s\S]+)\)\"', methodGraph.nodes[nodeID]['label'])
        head = m.group(1)
        code = m.group(2)
        if head == 'CodeCount':
            m = re.match(r'CodeCount\((\d+)\)', code)
            AddNode(programGraph, nodeID, 'CodeCount', methodsByID[startNodeID]['name'], methodsByID[startNodeID]['fileName'], codeCountID = int(m.group(1)))
            programGraph.add_edge(lastNodeID, nodeID)
            lastNodeID = nodeID
        elif head == 'METHOD_RETURN':
            programGraph.add_edge(lastNodeID, nodeID)
            lastNodeID = nodeID
        else:
            # Are you a method call?
            if r'::' in head:
                m = re.match(r'(.+)\:\:(.+)', head)
                head = m.group(2)
            if r'.' in head:
                m = re.match(r'(.+)\.(.+)', head)
                head = m.group(2)
            if head in methodIndexByName: 
                # I am a call
                for methodID in methodIndexByName[head]:
                    AddNode(programGraph, methodID, 'Method', head, methodsByID[methodID]['fileName'])
                    AddNode(programGraph, methodsByID[methodID]['returnID'], 'MethodReturn', head, methodsByID[methodID]['fileName'])
                    # connect the starts of the external methods
                    programGraph.add_edge(lastNodeID, methodID)
                lastNodeID = []
                for methodID in methodIndexByName[head]:
                    # connect the ends of the external methods
                    lastNodeID.append(methodsByID[methodID]['returnID'])
        for neighbor in list(methodGraph.adj[nodeID]):
            if isinstance(lastNodeID, list):
                for lastID in lastNodeID:
                    virtualEdge = (lastID, neighbor)
                    if virtualEdge not in visitedVirtualEdges:
                        virtualEdgesToVisit.append(virtualEdge)
            else:
                virtualEdge = (lastNodeID, neighbor)
                if virtualEdge not in visitedVirtualEdges:
                    virtualEdgesToVisit.append(virtualEdge)

# Load data from Joern
codeCountNum = 630	# Set it manuelly!
with open('methods.txt', 'r') as file:
    methods = json.load(file)
methodsByID = {}
methodIndexByName = {}
for index in range(len(methods)):
    dotGraph = pydot.graph_from_dot_data(methods[index]['_6'][0])[0]
    methodGraph = nx.drawing.nx_pydot.from_pydot(dotGraph)
    if methodGraph.number_of_nodes() <= 2:
        continue		# I dont need method declarations
    methodID = str(methods[index]['_1'])
    methodReturnID = str(methods[index]['_2'])
    name = methods[index]['_3']

    # set methodIndexByName
    if name in methodIndexByName:
        methodIndexByName[name].append(methodID)
    else:
        methodIndexByName[name] = [methodID]

    # set methodsByID
    methodsByID[methodID] = {}
    methodsByID[methodID]['name'] = name
    methodsByID[methodID]['returnID'] = methodReturnID
    methodsByID[methodID]['fileName'] = methods[index]['_4']
    methodsByID[methodID]['lineNumber'] = methods[index]['_5']
    methodsByID[methodID]['graph'] = methodGraph
    print('\rGraphExtract: import ', index+1, '/', len(methods), 'methods', end='')
print('')

# Build a graph for the whole program
programGraph = nx.DiGraph()
for methodID in methodsByID:
    methodGraph = methodsByID[methodID]['graph']
    AddNode(programGraph, methodID, 'Method', methodsByID[methodID]['name'], methodsByID[methodID]['fileName'])
    AddNode(programGraph, methodsByID[methodID]['returnID'], 'MethodReturn', methodsByID[methodID]['name'], methodsByID[methodID]['fileName'])
    DFS(methodID, methodGraph, programGraph, methodsByID, methodIndexByName)

# Print the result
jsonData = {'features':[], 'edges':[], 'codeCount2Label':[0]*codeCountNum}
for nodeID in programGraph.nodes:
    programGraph.nodes[nodeID]['label'] = len(jsonData['features'])
    jsonData['features'].append(programGraph.nodes[nodeID]['feature'])
    if programGraph.nodes[nodeID]['myType'] == 'CodeCount':
        jsonData['codeCount2Label'][ programGraph.nodes[nodeID]['codeCountID']-1 ] = programGraph.nodes[nodeID]['label']
jsonData['edges'] = [[programGraph.nodes[edge[0]]['label'], programGraph.nodes[edge[1]]['label']] for edge in programGraph.edges]
with open('graph.json', 'w') as f:
    json.dump(jsonData, f)
nx.draw_kamada_kawai(programGraph, with_labels=False, node_size=5, arrows=True, arrowsize=3) 
plt.show()
