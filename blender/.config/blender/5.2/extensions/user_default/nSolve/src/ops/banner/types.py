

class DrawCleanup():
    def exit(self, context, force=False):
        pixels = []
        for attr in dir(self):
            if hasattr(getattr(self, attr), 'handle'):
                pixels.append(getattr(self, attr))

                area = pixels[-1].area
                pixels[-1].remove(force)
                if area.type != 'EMPTY':
                    area.tag_redraw()

                if force or not pixels[-1].elements:
                    pixels[-1].remove_timer()

        if not force and pixels and any(dp.elements for dp in pixels):
            return {'PASS_THROUGH'}

        return {'CANCELLED' if force else 'FINISHED'}


