import pickle
import re
from functions import *
import os
import itertools
import geopandas as gpd
import networkx as nx
from shapely.ops import cascaded_union
import osmnx.projection as projection

def find_neighbors(nodes, index, G, df_group):
    lengths = [min([G.shortest_path_length(node1, node2, weight="length") for node1 in nodes for node2 in group]) for i, group in enumerate(df_group["group"]) if i != index]
    return np.argsort()

if __name__ == "__main__":
    with open("../data/salt-lake-city/intersections.pkl", "rb") as f:
        intersection_dict = pickle.load(f)
    with open("../data/salt-lake-city/salt-lake-city.pkl", "rb") as f:
        data = pickle.load(f)
    G = data["G"]
    df_group = data["df_group"]
    df_group = df_group[list(intersection_dict.keys())]
    for index, row in df_group.iterrows():
        find_neighbors(row["nodes"])