#!/usr/bin/python

import networkx as nx
import collections
import random
import math
import operator
import logging
import sys





def Estrangement(G, label_dict, Zgraph, gap_proof):
    """ compute Q-tauE """
    consort_edge_set =  set(Zgraph.edges()) & set(G.edges())
    logging.info("Estrangement(): Z edges: %s", str(Zgraph.edges(data=True)))   
    logging.info("Estrangement(): G edges: %s", str(G.edges(data=True)))   
    logging.info("Estrangement(): consort_edge_set: %s", str(consort_edge_set))   
    if len(consort_edge_set) == 0:
        estrangement = 0
    else:    
        if gap_proof is True:
            estrangement = sum([ math.sqrt(float(Zgraph[e[0]][e[1]]["weight"]) * G[e[0]][e[1]]['weight']) 
                for e in consort_edge_set if label_dict[e[0]] != label_dict[e[1]]]) / float(G.size(weight='weight'))
        else:    
            estrangement = sum([e[2]['weight'] for e in Zgraph.edges(data=True) if label_dict[e[0]] !=
            label_dict[e[1]]]) / float(G.size(weight='weight'))
    return estrangement




def match_labels(label_dict, prev_label_dict):
    """ match labels using Sameet's bipartitie graph based algorithm

    We start by representing the communities at t-1 and t as nodes of a
    bipartite graph.

    from each node at t-1 draw a directed link to the node at t with which it has
    maximum overlap.

    from each node at t draw a directed link to the node at t-1 with which it has
    maximum overlap.

        Basically x,y and z choose who they are most similar to among a and b
    and denote this by arrows directed outward from them. Similarly a and
    b, choose who they are most similar to among x, y and z. Then the rule
    is that labels on the t-1 side of every bidirected (symmetric) link is
    preserved - all other labels on the t-1 side die.

    """
    
    # corner case for the first snapshot
    if prev_label_dict == {}:
        return label_dict

    nodesets_per_label_t = collections.defaultdict(set) # key = label, val = set
                                                    # of nodes with that label

    nodesets_per_label_t_minus_1 = collections.defaultdict(set) # key = label, val = set
                                                    # of nodes with that label
    
    for n,l in label_dict.items():
        nodesets_per_label_t[l].add(n)


    for n,l in prev_label_dict.items():
        nodesets_per_label_t_minus_1[l].add(n)


    #logging.debug("nodesets_per_label_t_minus_1: %s",
    #    str(nodesets_per_label_t_minus_1))
    #logging.debug("nodesets_per_label_t: %s", str(nodesets_per_label_t))

    overlap_dict = {} # key = (prev_label, new_label), value = jaccard overlap

    overlap_graph = nx.Graph() # store jaccard overlap between all pairs of
    # labels between t and t-1. Undirected bi-partite graph
    # compute jaccard between all possible directed pairs of labels between
    # snapshopts t and t-1
    for l_t, nodeset_t in nodesets_per_label_t.items():
        for l_t_minus_1, nodeset_t_minus_1 in nodesets_per_label_t_minus_1.items():
            jaccard =  len(nodeset_t_minus_1 & nodeset_t)/float(len((nodeset_t_minus_1 | nodeset_t))) 
            overlap_graph.add_edge(l_t_minus_1, l_t, weight=jaccard)

    #logging.debug("overlap_graph nodes: %s", overlap_graph.nodes())
    #logging.debug("overlap_graph edges: %s", overlap_graph.edges(data=True))

    max_overlap_digraph = nx.DiGraph() # each label at t-1  and at t is a vertex in
        # this bi-partite graph and a directed edge implies the max overlap with the
        # other side (see comment at the beg of this function)

    for v in overlap_graph.nodes():
        # find the nbr with max weight
        maxwt_nbr = max([(nbrs[0],nbrs[1]['weight']) for nbrs in overlap_graph[v].items()],
            key=operator.itemgetter(1))[0]
        max_overlap_digraph.add_edge(v, maxwt_nbr)

    
    #logging.debug("max_overlap_digraph nodes: %s", max_overlap_digraph.nodes())
    #logging.debug("max_overlap_digraph edges %s", max_overlap_digraph.edges())


    #logging.debug("out_degrees in max_overlap_digraph: %s",
    #    str(max_overlap_digraph.out_degree()))

    #logging.debug("in_degrees in max_overlap_digraph: %s",
    #    str(max_overlap_digraph.in_degree()))

    matched_label_dict = {} # key = node, value = new label
    for l_t in nodesets_per_label_t.keys():
        match_l_t_minus_1 = max_overlap_digraph.successors(l_t)[0]
        # match if it is a bi-directional edge
        if max_overlap_digraph.successors(match_l_t_minus_1)[0] == l_t:
            best_matched_label = match_l_t_minus_1
        else:
            best_matched_label = l_t

        for n in nodesets_per_label_t[l_t]:
            matched_label_dict[n] = best_matched_label

    #logging.debug("matched_label_dict %s", str(matched_label_dict))
    return matched_label_dict



def graph_distance(g0, g1, weighted=True):

    # Tanimoto distance between the set of edges
    # this is defined as    (a.b - (aUb - a.b)) /aUb
    # weighted case; a.b is dot product and aUb = a^2 + b^2 - a.b
    #   so distance = (3a.b - a^2 - b ^2)/(a^2+b^2 = a.b)
    intersection = set(g1.edges_iter()) & set(g0.edges_iter())
    if weighted is False:
        union = set(g1.edges_iter()) | set(g0.edges_iter())
        graph_distance = (len(union) - len(intersection))/float(len(union))
    else:
        g0weights = nx.get_edge_attributes(g0,'weight')
        g1weights = nx.get_edge_attributes(g1,'weight')
        dot_product = sum((g0weights[i]*g1weights[i] for i in intersection))
        e1_norm = sum((g1weights[i]**2 for i in g1.edges_iter()))
        e0_norm = sum((g0weights[i]**2 for i in g0.edges_iter()))
        graph_distance = 1 - dot_product/float(e0_norm + e1_norm - dot_product)

    return graph_distance



def node_graph_distance(g0, g1):

    # Jaccard distance between the set of nodes
    # this is defined as    (a.b - (aUb - a.b)) /aUb
    g1_nodes = set(g1.nodes())
    g0_nodes = set(g0.nodes())
    graph_distance = 1 - len(g0_nodes & g1_nodes)/float(len(g0_nodes | g1_nodes)) 
    
    return graph_distance

