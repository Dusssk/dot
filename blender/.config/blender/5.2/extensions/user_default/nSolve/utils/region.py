def fixed_width(context):
    '''Calculate the fixed width of left and right regions in the current area'''
    left_fix = 0
    right_fix = 0

    # Iterate through all regions in the current area
    for r in context.area.regions:
        if r.type in {'TOOLS', 'UI'}:
            # Check the alignment of the region
            if r.alignment == 'LEFT':
                left_fix += r.width
            elif r.alignment == 'RIGHT':
                right_fix += r.width

    # Adjust for navigation gizmo
    space_data = context.space_data
    gizmo_navigate_size = 64  # Approximate size in pixels

    if space_data.type == 'VIEW_3D':
        if space_data.show_gizmo and space_data.show_gizmo_navigate:
            # The navigation gizmo is typically on the right side
            right_fix += gizmo_navigate_size

    return left_fix, right_fix
