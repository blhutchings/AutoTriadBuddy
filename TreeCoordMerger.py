from anytree import Node, RenderTree

# Converts coordinates of images within an root image to the root images coordinates
class TreeCoordMerger:
    def __init__(self, root_name, rect):
        self.root = Node(root_name, data=[1, rect])
        self.nodes = {root_name: self.root}

    def __copy_data(self, node: Node):
        return (node.data).copy

    # Adds a child image to a parent image

    def add_direct(self, name, parent_name, rect):
        self.nodes[name] = Node(name, parent=self.nodes.get(parent_name), data=[1, rect])

    def add_scale(self, name, parent_name, scale, rect):
        self.nodes[name] = Node(name, parent=self.nodes.get(parent_name), data=[scale, rect])

    def get_node(self, name):
        return self.nodes.get(name)

    def print(self):
        print(RenderTree(self.root))

    # Time complexity can be improved by saving results
    def convert_all(self):
        coords = []
        node_names = list(self.nodes.keys())

        for i in range(1, len(node_names)):  # Skip root
            coords.append(self.convert(node_names[i]))
        return coords

    def convert(self, node_name):
        _, _, coords = self.convert_rec(node_name)
        return list(map(int, coords))

    def convert_rec(self, node_name):
        current_node = self.nodes.get(node_name)  # Old 1
        current_r, current_rect = current_node.data[0], current_node.data[1].copy()
        coords = current_node.data[1].copy()

        if current_node.is_root:
            return 1, 1, coords

        parent_node = self.nodes.get(current_node.parent.name)  # New  2
        parent_r, parent_rect = parent_node.data[0], parent_node.data[1].copy()

        w_scale, h_scale, coords_recursive = self.convert_rec(parent_node.name)


        # Direct conversion
        if current_r == 1.0:
            coords[0] = (coords[0] * w_scale) + coords_recursive[0]
            coords[1] = (coords[1] * h_scale) + coords_recursive[1]
            coords[2] = (coords[2] * w_scale)
            coords[3] = (coords[3] * w_scale)
        # Scaled conversion
        else:
            current_w = current_rect[2]
            current_h = current_rect[3]
            parent_w = parent_rect[2]
            parent_h = parent_rect[3]

            # Direction: NEW / OLD
            w_scale = parent_w / current_w
            h_scale = parent_h / current_h

            coords[0] = (coords[0] * w_scale) + coords_recursive[0]
            coords[1] = (coords[1] * h_scale) + coords_recursive[1]
            coords[2] = (coords[2] * w_scale)
            coords[3] = (coords[3] * w_scale)

        return w_scale, h_scale, coords

