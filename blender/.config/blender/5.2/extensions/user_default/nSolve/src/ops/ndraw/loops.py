import math


def interpolate_grid_point(start_co, before_co, after_co):
    '''Interpolate a new grid point between start_co and the midpoint of before_co and after_co.'''
    mid_point = (before_co + after_co) * 0.5
    final_point = start_co + (mid_point - start_co) * 2
    return final_point  # Note: This returns a coordinate, not a vertex


def prepare_grid_points(start_vert, before_start, after_start):
    '''Prepare grid points with original points and placeholders for interpolated ones.'''
    grid_points = [(start_vert, start_vert.co)]  # Initialize with the starting vertex

    # Add after points directly
    grid_points += [(vert_info[0], vert_info[0].co) for vert_info in after_start]

    # Prepare before points and placeholders for interpolation
    for before_info in before_start:
        before_vert = before_info[0]
        grid_points.append((before_vert, before_vert.co))
        for after_info in after_start:
            after_vert = after_info[0]
            # Correct usage: pass the actual Vector coordinates to the function
            interpolated_co = interpolate_grid_point(start_vert.co, before_vert.co, after_vert.co)
            # Placeholder for interpolation; actual vertex will be created later
            grid_points.append((None, interpolated_co))

    return grid_points


def find_starting_vertex(loop):
    '''Find a suitable starting vertex ensuring that the vertex and all its selected, connected vertices do not all share the same common face.'''

    for vert_info in loop:
        vert = vert_info[0]  # The potential starting vertex
        if vert_info[1] and vert_info[1] < 135:  # Check if the vertex meets the initial condition
            # Find all vertices connected to vert by an edge
            connected_verts = [e.other_vert(vert) for e in vert.link_edges]

            # Filter those connected vertices that are selected
            selected_connected_verts = [v for v in connected_verts if v.select]

            # If there are no selected connected vertices, consider the next vertex
            if not selected_connected_verts:
                continue

            # Initialize common_faces with the faces of the starting vertex
            common_faces = set(vert.link_faces)

            # Iteratively intersect common_faces with the faces of each selected, connected vertex
            for connected_vert in selected_connected_verts:
                common_faces.intersection_update(connected_vert.link_faces)

            # If common_faces is empty after checking all selected, connected vertices, it means not all of them share a face
            # with the starting vertex, so the starting vertex is not suitable.
            if common_faces:
                # If common_faces is not empty, it means all selected connected vertices share at least one common face with the starting vertex.
                # Since the requirement is not to have all of them share the same face(s), this vertex is not suitable.
                continue

            # If we reach this point, it means the current vertex does not have all its selected, connected vertices sharing the same face,
            # making it a suitable starting vertex.
            return vert_info

    # If no vertex meets the criteria, return None
    return None


def split_loop_at_vertex(loop, start_vert_info):
    '''Split the loop at the starting vertex into before and after parts.'''
    start_index = loop.index(start_vert_info)
    before_start = loop[:start_index]
    after_start = loop[start_index + 1:]
    return before_start, after_start


def process(loop):
    '''Main processing logic: identifies starting points and prepares data for geometry creation.'''
    start_vert_info = find_starting_vertex(loop)
    if not start_vert_info:
        return None, None, None  # Exit if no suitable starting vertex found

    before_start, after_start = split_loop_at_vertex(loop, start_vert_info)
    grid_points = prepare_grid_points(start_vert_info[0], list(reversed(before_start)), after_start)

    return grid_points, before_start, after_start


def find(bm):
    '''Find loops of selected vertices and calculate angles between them.'''

    visited_verts = set()
    all_loops_with_angles = []

    loop_starts = find_loop_starts(bm)
    while loop_starts:
        start_vert = loop_starts.pop(0)  # Get and remove the first element from the list
        if start_vert not in visited_verts:
            loop_verts = traverse_and_build_loop(start_vert, visited_verts)
            if loop_verts:
                # Remove end vert of the loop from starting points if it exists
                if loop_verts[-1] in loop_starts:
                    loop_starts.remove(loop_verts[-1])
                loop_angles = get_loops_angles(loop_verts)
                loop_with_angles = [(vert, loop_angles[vert]) for vert in loop_verts]
                all_loops_with_angles.append(loop_with_angles)

    return all_loops_with_angles


def calculate_angle(vec_a, vec_b):
    """Calculate the angle between two vectors, handling zero-length vectors."""
    if vec_a.length == 0 or vec_b.length == 0:
        return None  # Return None or an appropriate value indicating an invalid angle

    angle = math.degrees(vec_a.angle(vec_b))
    return angle


def find_loop_starts(bm):
    """Find vertices that are potential starts/ends of a loop."""
    starts = []
    for vert in bm.verts:
        if vert.select and len([e for e in vert.link_edges if e.other_vert(vert).select]) == 1:
            starts.append(vert)
    return starts


def traverse_and_build_loop(start_vert, visited_verts):
    """Traverse from start vertex to build loop vertices, marking as visited."""
    loop_verts = [start_vert]
    current_vert = start_vert
    visited_verts.add(current_vert)

    while True:
        connected_selected_verts = [e.other_vert(current_vert) for e in current_vert.link_edges if e.other_vert(current_vert).select and e.other_vert(current_vert) not in visited_verts]
        if not connected_selected_verts:
            break
        next_vert = connected_selected_verts[0]
        loop_verts.append(next_vert)
        visited_verts.add(next_vert)
        current_vert = next_vert

    return loop_verts


def get_loops_angles(loop_verts):
    """Calculate angles for vertices in a loop, assigning None where not applicable."""
    loop_angles = {}
    for i, vert in enumerate(loop_verts):
        if 0 < i < len(loop_verts) - 1:
            vec_a = (loop_verts[i - 1].co - vert.co).normalized()
            vec_b = (loop_verts[i + 1].co - vert.co).normalized()
            angle = calculate_angle(vec_a, vec_b)
            loop_angles[vert] = angle
        else:
            loop_angles[vert] = None
    return loop_angles
