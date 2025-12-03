#https://github.khronos.org/glTF-MaterialX-Converter/
#https://www.google.com/search?q=maya+materialx+to+glTF&sca_esv=2da0fcebb3bfa148&rlz=1C1ONGR_enUS1121US1121&ei=T5IoaeivDaLIptQPmuXrqAk&ved=0ahUKEwiok4WU9ZKRAxUipIkEHZryGpUQ4dUDCBM&uact=5&oq=maya+materialx+to+glTF&gs_lp=Egxnd3Mtd2l6LXNlcnAiFm1heWEgbWF0ZXJpYWx4IHRvIGdsVEYyBxAhGKABGAoyBxAhGKABGAoyBxAhGKABGAoyBxAhGKABGAoyBxAhGKABGAoyBRAhGJ8FMgUQIRifBTIFECEYnwUyBRAhGJ8FMgUQIRifBUjMHFAAWMwZcAB4AZABAJgBcKABuQyqAQQxNi4zuAEDyAEA-AEB-AECmAIToAL9DMICCxAAGIAEGJECGIoFwgIREC4YgAQYsQMY0QMYgwEYxwHCAgUQLhiABMICCBAAGIAEGLEDwgIOEAAYgAQYsQMYgwEYigXCAgsQLhiABBixAxiDAcICChAAGIAEGEMYigXCAgoQLhiABBhDGIoFwgIOEC4YgAQYsQMY0QMYxwHCAhEQLhiABBixAxiDARjHARivAcICBRAAGIAEwgILEAAYgAQYsQMYgwHCAggQLhiABBixA8ICCxAAGIAEGIYDGIoFwgIIEAAYFhgKGB7CAgYQABgWGB7CAgcQABiABBgNwgIGEAAYDRgewgIIEAAYBRgNGB7CAggQABgIGA0YHsICCBAAGIAEGKIEwgIFEAAY7wWYAwCSBwQxNC41oAfm6AGyBwQxNC41uAf9DMIHBjAuMTUuNMgHMg&sclient=gws-wiz-serp
import pathlib


import pymel.core as pm



def get_textures(objs, export_nodes=[]):
    materials = {}

    def _get_best_file_node(color_input):
        nonlocal export_nodes
        matches = []
        for texture in color_input:
            for export_node in export_nodes:
                if texture in export_node.members(True):
                    matches.append(texture)

        if matches:
            return matches

        #No matches were found so just return the original input
        return color_input
    
    
    shapes = pm.listRelatives(objs, s=True)
    shapes += pm.ls(objs, shapes=True)
    for shape in shapes:
        sgs = pm.listConnections(shape, type='shadingEngine' )
        for sg in sgs:
            shaders = pm.listConnections("%s.surfaceShader" % sg, s=True)
            for shader in shaders:
                color_attr = None
                if hasattr(shader, 'color'):
                    color_attr = getattr(shader, 'color')
                elif hasattr(shader, 'diffuse'):
                    color_attr = getattr(shader, 'diffuse')
                elif hasattr(shader, 'baseColor'):
                    color_attr = getattr(shader, 'baseColor')
                    
                if not color_attr:
                    continue
                
                color_input = pm.listConnections(color_attr, s=True, d=False)
                if not color_input:
                    continue
            
                color_input = pm.findType(color_input, type='file', forward=False,deep =True)
                if not color_input:
                    continue
                
                if len(color_input) > 1:
                    color_input = _get_best_file_node(color_input)
                    
                if len(color_input) != 1:
                    pm.warning(f"Found multiple textures for '{color_attr}' skipping texture. Note: You can add the preferred file node to your export set to fix this.")
                    continue

                color_input = pm.PyNode(color_input[0])
                filepath = color_input.fileTextureName.get()
                file = pathlib.Path(filepath)
                if file.suffix.lower() != '.png':
                    png = file.parent.joinpath(f"{file.stem}.png")
                    if png.exists():

                        filepath = str(png).replace("\\", "/")

                        
                if filepath:
                    materials.setdefault(shape.getParent().name(), set()).add(filepath)
                    

    for key, value in materials.items():
        materials[key] = list(value)

    return materials