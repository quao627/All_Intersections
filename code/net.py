import math
import os
from math import sin, cos, pi as PI
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from string import ascii_uppercase as ALPHABET

INFLOW_NODES_DISTANCE = 250
INFLOW_NODES_PREFIX = 'inflow'
JunctionDescription = List[Dict[str, any]]


def gen_net(edges_description: JunctionDescription,
            neighbor_descriptions: Optional[Dict[str, JunctionDescription]] = None,
            working_dir: Path = Path(''),
            output: Union[Path, str] = 'net.net.xml',
            open_netedit: bool = False) -> Path:
    """
    :param edges_description: description of the net, format:
            [
                {
                    'num_incoming': (counts shorter left only lanes)
                    'num_outgoing':
                    'length': (in m)
                    'speed': (in m/s)
                    'left_turn_only_length': (in m, optional)
                    'slope': (in radians, positive if incoming vehicles go uphill)
                    'incoming_TL_cycle_duration': (in s)
                    'connections': {
                        lane: [(edge, lane), (edge, lane), ...],
                        1: [(2, 0)] # ex : lane 1 will be connected only to the outgoing lane 0 of edge 2
                        ...
                    }
                },
                ...
            ]
            The index is the index in the given array, the lanes are created clockwise (starting north, but it doesn't
            make a difference).
    :param neighbor_descriptions: description of the neighbors, dict consisting of
        {
            '<junction_id in the above main intersection>': junction description in same format as above
            '<junction_id in the above main intersection>': junction description in same format as above
            ...
        }
    :param working_dir: where to store temp files
    :param output: either name of the output file (a str) or the full path (a Path). Filename in .net.xml
    :param open_netedit: opens netedit if the net is successfully generated, useful for testing.
    :return: the output path
    """

    all_nodes = Element('nodes')
    all_edges = Element('edges')

    # traffic light in the center
    tl_node = Element('node', {
        'id': 'TL',
        'x': '0',
        'y': '0',
        'z': '0',
        'type': 'traffic_light_right_on_red'
        # By default vehicles can turn right even when the TL is red (default in the USA right ?)
    })

    all_nodes.append(tl_node)
    # nodes around
    # starts by the North, goes in clockwise
    for main_node, sup_nodes, edges in _get_nodes_and_edges(edges_description,
                                                        tl_node.attrib['id'],
                                                        float(tl_node.attrib['x']),
                                                        float(tl_node.attrib['y'])):
        all_nodes.append(main_node)
        all_nodes.extend(sup_nodes)
        all_edges.extend(edges)
        if neighbor_descriptions is not None:
            for sub_node, sub_sup_nodes, sub_edges in \
                    _get_nodes_and_edges(neighbor_descriptions[main_node.attrib['id']][1:],
                                         main_node.attrib['id'],
                                         float(main_node.attrib['x']),
                                         float(main_node.attrib['y'])):
                all_nodes.append(sub_node)
                all_nodes.extend(sub_sup_nodes)
                all_edges.extend(sub_edges)

    connections = Element('connections')
    connections.extend(_get_connections(edges_description, 'TL', ''))
    if neighbor_descriptions is not None:
        for junction, neighbor_description in neighbor_descriptions.items():
            connections.extend(_get_connections(neighbor_description, junction, junction))

    for element, filename in [
        (all_nodes, 'nodes.nod.xml'),
        (all_edges, 'edges.edg.xml'),
        (connections, 'connections.con.xml')
    ]:
        ElementTree.ElementTree(element).write(working_dir / filename)

    if isinstance(output, str):
        output = working_dir / output

    res = os.system(f'netconvert -v '
                    f'--node-files={working_dir / "nodes.nod.xml"} '
                    f'--edge-files={working_dir / "edges.edg.xml"} '
                    f'--connection-files={working_dir / "connections.con.xml"} '
                    f'--output-file={output} '
                    f'--tls.minor-left.max-speed=1')  # always create left turn phases
    if res == 0:
        print('Success')
        if open_netedit:
            os.system(f'netedit {output}')
    else:
        print('Failure, try again :(')

    return output


def _get_nodes_and_edges(junction_description: JunctionDescription,
                         center_junction_id: str,
                         center_junction_x: float,
                         center_junction_y: float) -> List[Tuple[Element, List[Element], List[Element]]]:

    angle_offset = - (math.atan(center_junction_y / center_junction_x) if center_junction_x != 0 else PI / 2)
    if center_junction_x < 0 or (center_junction_x == 0 and center_junction_y < 0):
        angle_offset += PI
    if center_junction_x == 0 and center_junction_y == 0:
        angle_offset = 0

    prefix = center_junction_id if center_junction_id != 'TL' else ''
    offset = 0 if center_junction_id == 'TL' else 1

    result = []
    for i, edge in enumerate(junction_description):
        result.append((Element('node', {
                'id': prefix + ALPHABET[i],
                'x': str(center_junction_x + edge['length'] * cos(PI/2 - (
                    angle_offset + 2 * PI * i / (len(junction_description)+offset)))),
                'y': str(center_junction_y + edge['length'] * sin(PI/2 - (
                    angle_offset + 2 * PI * i / (len(junction_description)+offset)))),
                'z': str(- edge['length'] * sin(edge['slope'])),
                'type': 'traffic_light',
            }), [], [
             ]))

        if 'left_turn_only_length' in edge:
            intern_edge_x = center_junction_x + edge['left_turn_only_length'] * cos(PI / 2 - (
                            angle_offset + 2 * PI * i / (len(junction_description) + offset)))
            intern_edge_y = center_junction_y + edge['left_turn_only_length'] * sin(PI / 2 - (
                            angle_offset + 2 * PI * i / (len(junction_description) + offset)))

            result[-1][1].append(
                Element('node', {
                    'id': prefix + ALPHABET[i] + '_intern',
                    'x': str(intern_edge_x),
                    'y': str(intern_edge_y),
                    'z': str(- edge['left_turn_only_length'] * sin(edge['slope'])),
                }))
            if edge['num_incoming'] - 1 > 0:
                result[-1][2].append(
                    Element('edge', {
                        'id': f'{prefix}{ALPHABET[i]}2{center_junction_id}',
                        'from': prefix + ALPHABET[i],
                        'to': prefix + ALPHABET[i] + '_intern',
                        'speed': str(edge['speed']),
                        'numLanes': str(edge['num_incoming'] - 1),
                    }))
            if edge["num_incoming"] > 0:
                result[-1][2].append(
                    Element('edge', {
                        'id': f'{prefix}{ALPHABET[i]}2{center_junction_id}_intern',
                        'from': prefix + ALPHABET[i] + '_intern',
                        'to': center_junction_id,
                        'speed': str(edge['speed']),
                        'numLanes': str(edge['num_incoming'])
                    }))
            if edge["num_outgoing"] > 0:
                result[-1][2].append(
                    Element('edge', {
                        'id': f'{center_junction_id}2{prefix}{ALPHABET[i]}',
                        'from': center_junction_id,
                        'to': prefix + ALPHABET[i],
                        'speed': str(edge['speed']),
                        'numLanes': str(edge['num_outgoing']),
                    }))
        else:
            if edge["num_incoming"] > 0:
                result[-1][2].append(
                    Element('edge', {
                        'id': f'{prefix}{ALPHABET[i]}2{center_junction_id}',
                        'from': prefix + ALPHABET[i],
                        'to': center_junction_id,
                        'speed': str(edge['speed']),
                        'numLanes': str(edge['num_incoming'])
                    }))
            if edge["num_outgoing"] > 0:
                result[-1][2].append(
                    Element('edge', {
                        'id': f'{center_junction_id}2{prefix}{ALPHABET[i]}',
                        'from': center_junction_id,
                        'to': prefix + ALPHABET[i],
                        'speed': str(edge['speed']),
                        'numLanes': str(edge['num_outgoing']),
                    }))

    return result


def _get_connections(edges_description: JunctionDescription, junction_id: str, prefix: str) -> List[Element]:
    def name_mapping(index):
        if prefix == '':
            return ALPHABET[index]
        else:
            return 'TL' if index == 0 else (prefix + ALPHABET[index - 1])

    return [Element('connection', {
        'from': f'{name_mapping(edge_index)}2{junction_id}{"_intern" if "left_turn_only_length" in edge else ""}',
        'to': f'{junction_id}2{name_mapping(outgoing_edge)}',
        'fromLane': str(incoming_lane),
        'toLane': str(outgoing_lane),
    })
            for edge_index, edge in enumerate(edges_description)
            for incoming_lane, outgoing_connections in edge['connections'].items()
            for outgoing_edge, outgoing_lane in outgoing_connections]


