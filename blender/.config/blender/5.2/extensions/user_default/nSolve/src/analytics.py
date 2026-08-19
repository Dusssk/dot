import datetime
import bpy
import os
from ..utils import addon

last_operator = None


def get_valid_analytics_dir():
    """Get a valid analytics directory path or None if invalid."""
    pref = addon.pref()
    if pref.analytics_path and os.path.exists(os.path.dirname(pref.analytics_path)):
        return pref.analytics_path
    return None


def logs(scene):
    """
    Track logs for operations.
    Args:
        scene (bpy.types.Scene): The scene object
    """
    pref = addon.pref()
    if not pref.analytics_logs:
        return

    analytics_dir = get_valid_analytics_dir()
    if not analytics_dir:
        return

    global last_operator

    log_file = os.path.join(analytics_dir, 'logs.txt')

    # Create file if it doesn't exist
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=== Blender Operation Log ===\n")

    if bpy.context.window_manager.operators:
        operator = bpy.context.window_manager.operators[-1]

        modals = bpy.context.window.modal_operators
        modal_operators = list(modals)
        last = last_operator

        if operator and operator not in modal_operators and operator != last:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            props = ' '.join([f"{k}:{getattr(operator.properties, k)}" for k in operator.properties.keys()])
            log_entry = f"{timestamp}  {operator.bl_idname:{40}}{props}\n"

            # Write to log file
            with open(log_file, 'a+', encoding='utf-8') as f:
                f.write(log_entry)

            last_operator = operator


def stats(operation_text):
    """
    Track usage statistics for operations.
    Args:
        operation_text (str): The text identifier for the operation (e.g. "nSolve: Join")
    """
    pref = addon.pref()
    if not pref.analytics_stats:
        return

    analytics_dir = get_valid_analytics_dir()
    if not analytics_dir:
        return

    stats_file = os.path.join(analytics_dir, 'stats.txt')

    stats_dict = {}

    # Read existing stats if file exists
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            for line in f:
                if ' - ' in line:
                    op, count = line.strip().rsplit(' - ', 1)
                    stats_dict[op] = int(count)

    # Update count for current operation
    stats_dict[operation_text] = stats_dict.get(operation_text, 0) + 1

    # Write updated stats back to file
    with open(stats_file, 'w', encoding='utf-8') as f:
        for op, count in sorted(stats_dict.items()):
            f.write(f"{op} - {count}\n")
