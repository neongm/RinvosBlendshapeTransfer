# Copyright © 2024 Rinvo, All rights reserved.

import bpy
import webbrowser
import bmesh
from bpy.app.handlers import persistent

bl_info = {
    "name": "Rinvo's Blendshape Transfer",
    "blender": (4, 0, 0),
    "category": "3D View",
    "version": (0, 4, 3),
    "location": "3D View > Sidebar",
    "warning": "Plugin is still under development",  # Optional warning text
    "doc_url": "https://jinxxy.com/rinvo/RinvosBlendshapeTransfer",
    "tracker_url": "",
    "author": "Rinvo",
    "description": "Transfer blendshapes (shape keys) from one object to another using Surface Deform.\n\n"
}

# Utility Functions
def update_blendshape_list(scene, context):
    """Update the blendshape list based on the selected source object."""
    # Save the current state of the blendshape items
    saved_data = {
        item.name: {
            "select": item.select,
            "target_key_name": item.target_key_name,
            "source_key_name": item.source_key_name,
            "sync_value": item.sync_value,
        }
        for item in scene.bs_shape_keys
    }
    
    # Clear the list and repopulate it
    scene.bs_shape_keys.clear()
    source = scene.bs_source
    if source and source.data.shape_keys:
        for key in source.data.shape_keys.key_blocks:
            item = scene.bs_shape_keys.add()
            item.name = key.name
            # Restore the saved state if it exists
            if key.name in saved_data:
                item.select = saved_data[key.name]["select"]
                if(key.name in scene.bs_target.data.shape_keys.key_blocks):
                    item.target_key_name = saved_data[key.name]["target_key_name"]
                    item.source_key_name = saved_data[key.name]["source_key_name"]
                    item.sync_value = saved_data[key.name]["sync_value"]
            else:
                item.select = False  # Default to not selected if no saved state

def load_target(scene, context):
    """Load saved data from the target object when it changes."""
    target = scene.bs_target

    # If the target is None, clear the list and return
    if not target:
        scene.bs_shape_keys.clear()
        source = scene.bs_source
        if source and source.data.shape_keys:
            for key in source.data.shape_keys.key_blocks:
                item = scene.bs_shape_keys.add()
                item.name = key.name
        return

    # If the target is new (no saved data), clear the list and show default values
    if "bs_saved_data" not in target:
        scene.bs_shape_keys.clear()
        update_blendshape_list(scene, context)  # Populate the list with default values
        return

    # If the target has saved data, load it
    saved_data = target["bs_saved_data"]

    # Clear the list and repopulate it based on the source object
    scene.bs_shape_keys.clear()
    source = scene.bs_source
    target = scene.bs_target

    if source and source.data.shape_keys:
        for key in source.data.shape_keys.key_blocks:
            item = scene.bs_shape_keys.add()
            item.name = key.name

            # Restore the saved state if it exists
            if key.name in saved_data and key.name in target.data.shape_keys.key_blocks:
                item.select = saved_data[key.name]["select"]
                item.target_key_name = saved_data[key.name]["target_key_name"]
                item.source_key_name = saved_data[key.name]["source_key_name"]
                item.sync_value = saved_data[key.name]["sync_value"]
            else:
                # Reset properties for blendshapes that don't exist on the target
                item.select = False
                item.target_key_name = ""
                item.source_key_name = ""
                item.sync_value = key.value  # Set sync_value to the source object's shape key value

    # Reset blendshapes that are gone from the target
    for item in scene.bs_shape_keys:
        if item.name not in saved_data:
            # Reset properties for blendshapes that are gone from the target
            item.select = False
            item.target_key_name = ""
            item.source_key_name = ""
            item.sync_value = key.value  # Set sync_value to the source object's shape key value

def save_target(scene, context):
    """Save the current state of the blendshape list to the target object."""
    if scene.bs_target:
        current_data = {
            item.name: {
                "select": item.select,
                "target_key_name": item.target_key_name,
                "source_key_name": item.source_key_name,
                "sync_value": item.sync_value,
            }
            for item in scene.bs_shape_keys
        }
        scene.bs_target["bs_saved_data"] = current_data

# Update the target property to call load_target when the target changes
def update_target(scene, context):
    """Update the target object and load saved data if available."""
    load_target(scene, context)

def save_and_reset_shape_key_states(source):
    """Save the current values of all shape keys on the source object and reset them."""
    states = {}
    if source and source.data.shape_keys:
        for key in source.data.shape_keys.key_blocks:
            states[key.name] = key.value
            key.value = 0.0
    return states

def restore_shape_key_states(source, states):
    """Restore the values of shape keys on the source object."""
    if source and source.data.shape_keys:
        for key in source.data.shape_keys.key_blocks:
            if key.name in states:
                key.value = states[key.name]

def ensure_transfer_mask_vertex_group(target):
    """Ensure the target object has a BlendshapeTransferMask vertex group."""
    if "BlendshapeTransferMask" not in target.vertex_groups:
        transfer_mask_group = target.vertex_groups.new(name="BlendshapeTransferMask")
        # Initialize all vertices to weight 1.0
        for vertex in target.data.vertices:
            transfer_mask_group.add([vertex.index], 1.0, 'REPLACE')
    return "BlendshapeTransferMask"

def ensure_surface_deform_compatibility(obj):
    """Simply triangulate the input object"""
    bmo = bmesh.new()
    bmo.from_mesh(obj.data)

    nonmanifold = []

    for edge in bmo.edges:
        if not edge.is_manifold:
            nonmanifold.append(edge)
    
    if nonmanifold != []:
        bmesh.ops.split_edges(bmo, edges=nonmanifold)

    bmesh.ops.triangulate(bmo, faces=bmo.faces[:])

    bmo.to_mesh(obj.data)
    bmo.free()

# Property Group for Blendshapes
class BlendshapeItem(bpy.types.PropertyGroup):
    # on update sync value of the target's blendshape with the source's blendshape value
    def update_sync_value(self, context):
        target = bpy.context.scene.bs_target
        if(target):
            source_key_name = self.source_key_name
            target_key_name = self.target_key_name

            
            # Ensure the target and source shape keys exist
            if target.data.shape_keys.key_blocks.get(target_key_name) and bpy.context.scene.bs_source.data.shape_keys.key_blocks.get(source_key_name):
                # Sync the values of the target and source shape keys
                target_value = self.sync_value
                target.data.shape_keys.key_blocks[target_key_name].value = target_value
                bpy.context.scene.bs_source.data.shape_keys.key_blocks[source_key_name].value = target_value
                
                target.active_shape_key_index = target.data.shape_keys.key_blocks.find(target_key_name)



    name: bpy.props.StringProperty(name="Blendshape Name")
    select: bpy.props.BoolProperty(name="Select", default=False)
    sync_value: bpy.props.FloatProperty(name="Sync Value", default=0.0, min=0.0, max=1.0, update=update_sync_value)
    
    target_key_name: bpy.props.StringProperty(name="Target Key Name", default="")
    source_key_name: bpy.props.StringProperty(name="Source Key Name", default="")





# Custom Operator to Open Web Links
class OpenWebLinkOperator(bpy.types.Operator):
    bl_idname = "wm.open_web_link"
    bl_label = "Open Web Link"
    link: bpy.props.StringProperty()

    def execute(self, context):
        webbrowser.open(self.link)
        return {'FINISHED'}

# Custom UI List for Blendshapes
class UI_UL_BlendshapeList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_prop):
        row = layout.row()
        row.label(text=item.name, icon='SHAPEKEY_DATA')

        #row.prop(item, "select", text="", icon='CHECKBOX_HLT' if item.select else 'CHECKBOX_DEHLT')

        # add a slider that will update the sync_value of the target object
        if(item.target_key_name != ""):
            #show synced icon
            row.scale_x = 0.6
            row.label(text="", icon='LINKED')
            row.prop(item, "sync_value", text="", slider=True)
        else:
            row.scale_x = 0.6
            row.label(text="", icon='BLANK1')
            row.prop(context.scene.bs_source.data.shape_keys.key_blocks[item.name], "value", text="", slider=True)
        row.scale_x = 1
        row.prop(item, "select", text="", icon='CHECKBOX_HLT' if item.select else 'CHECKBOX_DEHLT')





# Blendshape Transfer Panel
class BlendshapeTransferPanel(bpy.types.Panel):
    bl_label = "Blendshape Transfer"
    bl_idname = "VIEW3D_PT_blendshape_transfer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Blendshape'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Source and Target Selection
        box = layout.box()
        box.label(text="Source and Target Selection")
        box.prop(scene, "bs_source", text="Source")
        box.prop(scene, "bs_target", text="Target")

        # Blendshape List
        box = layout.box()
        label_row = box.row()
        label_row.label(text="Blendshape List")
        label_row.operator("object.refresh_blendshapes", text="Refresh")
        
        box.template_list(
            "UI_UL_BlendshapeList", "blendshape_list",
            scene, "bs_shape_keys",
            scene, "bs_shape_key_index",
            rows=6
        )

        # Paint Transfer Mask Button
        box = layout.box()
        if bpy.context.active_object and bpy.context.active_object.mode == 'WEIGHT_PAINT':
            box.operator("object.exit_paint_mode", text="Exit Paint Mode", icon='X')
        else:
            box.operator("object.toggle_transfer_mask_paint", text="Paint Transfer Mask", icon='BRUSH_DATA')

        # Options
        box = layout.box()
        box.label(text="Options")
        box.prop(scene, "bs_override_existing", text="Override Existing Shape Keys")
        
        if not scene.bs_override_existing:
            box.prop(scene, "bs_key_suffix", text="Suffix")

        # Advanced Options
        advanced_box = box.box()
        advanced_box.prop(
            scene, "show_advanced",
            text="Advanced Options",
            icon='TRIA_DOWN' if scene.show_advanced else 'TRIA_RIGHT'
        )
        if scene.show_advanced:
            advanced_box.prop(scene, "bs_strength", text="Strength")
            advanced_box.prop(scene, "bs_falloff", text="Falloff")

        # Experimental settings
        experimental_box = box.box()
        experimental_box.prop(
            scene, "show_experimental",
            text="Pre-Processing Modifiers",
            icon='TRIA_DOWN' if scene.show_experimental else 'TRIA_RIGHT'
        )
        if scene.show_experimental:
            experimental_box.label(text="These settings could help. Experimental.")

            # Subdivision Parameters
            subdivision_box = experimental_box.box()
            subdivision_box.prop(scene, "bs_use_subdivision", text="Use Subdivision Modifier")
            if scene.bs_use_subdivision:
                subdivision_box.prop(scene, "bs_subdivision_levels", text="Subdivision Levels")
                subdivision_box.prop(scene, "bs_subdivision_type_simple", text="Simple Subdivision")
                subdivision_box.prop(scene, "bs_preview_subdivision", text="Preview Subdivision")

            # Displacement Parameters
            displacement_box = experimental_box.box()
            displacement_box.prop(scene, "bs_use_displace", text="Use Displace Modifier")
            if scene.bs_use_displace:
                displacement_box.prop(scene, "bs_displace_strength", text="Displace Strength")
                displacement_box.prop(scene, "bs_displace_midlevel", text="Displace Midlevel")
                displacement_box.prop(scene, "bs_displace_direction", text="Displace Direction")
                displacement_box.prop(scene, "bs_preview_displace", text="Preview Displace")

        # Transfer Operator
        button_box = layout.box()
        transfer_button = button_box.operator("object.transfer_blendshapes", text="Transfer Blendshapes", icon='ARROW_LEFTRIGHT')


# Author Links Panel
class AuthorLinksPanel(bpy.types.Panel):
    bl_label = "Author Links"
    bl_idname = "VIEW3D_PT_author_links"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Blendshape'

    def draw(self, context):
        layout = self.layout
        link_box = layout.box()
        link_box.label(text="Author: Rinvo, hope its gonna be useful:3")
        row = link_box.row(align=True)
        row.operator("wm.open_web_link", text="More Links").link = "https://rinvolinks.carrd.co/"
        row.operator("wm.open_web_link", text="Jinxxy").link = "https://jinxxy.com/rinvo/products"
        row.operator("wm.open_web_link", text="Bluesky").link = "https://bsky.app/profile/rinvo.bsky.social"
        row.operator("wm.open_web_link", text="Twitter").link = "https://x.com/rinvovrc"

# Blendshape Transfer Operator
class BlendshapeTransferOperator(bpy.types.Operator):
    bl_idname = "object.transfer_blendshapes"
    bl_label = "Transfer Blendshapes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        source = scene.bs_source.copy()
        source.data = scene.bs_source.data.copy()
        context.collection.objects.link(source)
        target = scene.bs_target

        if not source or not target:
            self.report({'ERROR'}, "Source or target object not set!")
            return {'CANCELLED'}

        if not source.data.shape_keys:
            self.report({'ERROR'}, "Source object has no shape keys!")
            return {'CANCELLED'}

        selected_keys = [shape for shape in scene.bs_shape_keys if shape.select]
        if not selected_keys:
            self.report({'ERROR'}, "No blendshapes selected!")
            return {'CANCELLED'}

        # Ensure Object Mode
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Save and reset shape key states
        saved_states = save_and_reset_shape_key_states(source)
        saved_states_target = save_and_reset_shape_key_states(target)


        # Set all the shapekeys on source to 0
        for key in source.data.shape_keys.key_blocks:
            key.value = 0.0

        bpy.context.view_layer.objects.active = source

        # Add optional Subdivision modifier
        if scene.bs_use_subdivision:
            subdiv_mod = source.modifiers.new(name="Subdivision Temp", type="SUBSURF")
            subdiv_mod.levels = scene.bs_subdivision_levels
            subdiv_mod.render_levels = scene.bs_subdivision_levels
            
            if scene.bs_subdivision_type_simple:
                subdiv_mod.subdivision_type = 'SIMPLE'

        # Add optional Displace modifier and apply it temporarily
        if scene.bs_use_displace:
            displace_mod = source.modifiers.new(name="Displace Temp", type="DISPLACE")
            displace_mod.strength = scene.bs_displace_strength
            displace_mod.mid_level = scene.bs_displace_midlevel
            displace_mod.direction = scene.bs_displace_direction
            
            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=displace_mod.name)
            source.data.shape_keys.key_blocks[-1].name = "Displace Temp"
            source.data.shape_keys.key_blocks[-1].value = 1.0
        
            source.modifiers.remove(displace_mod)

        # Making sure the source Mesh is compatible with Surface Deform
        ensure_surface_deform_compatibility(source)

        # Ensure Basis shape key exists
        if not target.data.shape_keys:
            target.shape_key_add(name="Basis", from_mix=False)

        # Ensure the transfer mask vertex group exists
        transfer_mask_group = ensure_transfer_mask_vertex_group(target)

        # Add Surface Deform modifier
        surf_mod = target.modifiers.new(name="Surface Deform", type="SURFACE_DEFORM")
        surf_mod.target = source
        surf_mod.vertex_group = transfer_mask_group
        surf_mod.strength = scene.bs_strength
        surf_mod.falloff = scene.bs_falloff

        bpy.context.view_layer.objects.active = target
        bpy.ops.object.surfacedeform_bind(modifier=surf_mod.name)

        # Transfer blendshapes
        for shape in selected_keys:
            key_name = shape.name

            key_block = source.data.shape_keys.key_blocks.get(key_name)

            if not key_block:
                self.report({'WARNING'}, f"Blendshape '{key_name}' not found, skipping.")
                continue
            
            source_key_name = f"{key_block.name}"  # Use the full name of the shape key
            sync_value = key_block.value # save for later too

            # reset on source
            key_block.value = 1.0
            
            # reset on target

            if key_name in target.data.shape_keys.key_blocks:
                if scene.bs_override_existing:
                    target.shape_key_remove(target.data.shape_keys.key_blocks[key_name])
                else:
                    key_name += scene.bs_key_suffix

            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=surf_mod.name)
            target.data.shape_keys.key_blocks[-1].name = key_name

            # shape = [shape for shape in scene.bs_shape_keys if shape.name == source_key_name][0]

            shape.target_key_name = key_name
            shape.source_key_name = source_key_name
            shape.sync_value = sync_value

            key_block.value = 0.0

        # Restore shape key states
        restore_shape_key_states(source, saved_states)
        restore_shape_key_states(target, saved_states_target)

        # Remove optional Subdivision modifier
        if scene.bs_use_subdivision:
            source.modifiers.remove(subdiv_mod)

        if scene.bs_use_displace:
            source.shape_key_remove(source.data.shape_keys.key_blocks["Displace Temp"])

        bpy.ops.object.modifier_remove(modifier=surf_mod.name)
        self.report({'INFO'}, f"Successfully transferred {len(selected_keys)} blendshapes.")

        save_target(context.scene, context)

        for ob in bpy.context.selected_objects:
            ob.select = False

        source.select = True
        bpy.context.view_layer.objects.active = source
        bpy.ops.object.delete()

        return {'FINISHED'}

# Operator to toggle weight paint mode for the transfer mask
class ToggleTransferMaskPaintOperator(bpy.types.Operator):
    bl_idname = "object.toggle_transfer_mask_paint"
    bl_label = "Toggle Transfer Mask Paint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        target = scene.bs_target

        if not target:
            self.report({'ERROR'}, "Target object not set!")
            return {'CANCELLED'}

        # Ensure the transfer mask vertex group exists
        transfer_mask_group = ensure_transfer_mask_vertex_group(target)

        # Set the target object as active
        bpy.context.view_layer.objects.active = target

        # Toggle weight paint mode
        if bpy.context.active_object.mode == 'WEIGHT_PAINT':
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            target.vertex_groups.active = target.vertex_groups[transfer_mask_group]
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

        return {'FINISHED'}


# Operator to exit paint mode
class ExitPaintModeOperator(bpy.types.Operator):
    bl_idname = "object.exit_paint_mode"
    bl_label = "Exit Paint Mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if bpy.context.active_object.mode == 'WEIGHT_PAINT':
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

# Operator to refresh the blendshape list
class BlendshapeRefreshOperator(bpy.types.Operator):
    bl_idname = "object.refresh_blendshapes"
    bl_label = "Refresh Blendshapes"

    def execute(self, context):
        update_blendshape_list(context.scene, context)
        return {'FINISHED'}

def update_preview_modifiers(scene):
    source = scene.bs_source

    if not source:
        return

    # Remove existing preview modifiers if they exist
    for mod in source.modifiers:
        if mod.name.startswith("Preview_"):
            source.modifiers.remove(mod)

    # Disable preview if modifier usage is disabled
    if scene.bs_preview_subdivision and not scene.bs_use_subdivision:
        scene.bs_preview_subdivision = False
    if scene.bs_preview_displace and not scene.bs_use_displace:
        scene.bs_preview_displace = False

    # Add preview modifiers if preview is enabled
    if scene.bs_preview_subdivision:
        subdiv_mod = source.modifiers.new(name="Preview_Subdivision", type="SUBSURF")
        subdiv_mod.levels = scene.bs_subdivision_levels
        subdiv_mod.render_levels = scene.bs_subdivision_levels
        if scene.bs_subdivision_type_simple:
            subdiv_mod.subdivision_type = 'SIMPLE'

    if scene.bs_preview_displace:
        displace_mod = source.modifiers.new(name="Preview_Displace", type="DISPLACE")
        displace_mod.strength = scene.bs_displace_strength
        displace_mod.mid_level = scene.bs_displace_midlevel
        displace_mod.direction = scene.bs_displace_direction

# Registration
classes = [
    BlendshapeItem,
    UI_UL_BlendshapeList,
    BlendshapeTransferPanel,
    BlendshapeTransferOperator,
    OpenWebLinkOperator,
    AuthorLinksPanel,
    BlendshapeRefreshOperator,
    ToggleTransferMaskPaintOperator,
    ExitPaintModeOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.bs_source = bpy.props.PointerProperty(type=bpy.types.Object, update=update_blendshape_list)
    bpy.types.Scene.bs_target = bpy.props.PointerProperty(type=bpy.types.Object, update=update_target)
    bpy.types.Scene.bs_shape_keys = bpy.props.CollectionProperty(type=BlendshapeItem)
    bpy.types.Scene.bs_shape_key_index = bpy.props.IntProperty()
    bpy.types.Scene.bs_override_existing = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.bs_key_suffix = bpy.props.StringProperty(default="_new")
    bpy.types.Scene.show_advanced = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.show_experimental = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.bs_strength = bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)
    bpy.types.Scene.bs_falloff = bpy.props.FloatProperty(default=4.0, min=0.1, max=16.0)

    # Experimental properties
    bpy.types.Scene.bs_use_subdivision = bpy.props.BoolProperty(default=False, name="Use Subdivision Modifier", update=lambda self, context: update_preview_modifiers(context.scene))
    bpy.types.Scene.bs_subdivision_type_simple = bpy.props.BoolProperty(default=False, name="Subdivision Type Simple", update=lambda self, context: update_preview_modifiers(context.scene))
    bpy.types.Scene.bs_subdivision_levels = bpy.props.IntProperty(default=1, min=0, max=6, name="Subdivision Levels", update=lambda self, context: update_preview_modifiers(context.scene))
    bpy.types.Scene.bs_use_displace = bpy.props.BoolProperty(default=False, name="Use Displace Modifier", update=lambda self, context: update_preview_modifiers(context.scene))
    bpy.types.Scene.bs_displace_strength = bpy.props.FloatProperty(default=0.01, min=0.0, name="Displace Strength", update=lambda self, context: update_preview_modifiers(context.scene))
    bpy.types.Scene.bs_displace_midlevel = bpy.props.FloatProperty(default=0.8, min=0.0, max=1.0, name="Displace Midlevel", update=lambda self, context: update_preview_modifiers(context.scene))
    bpy.types.Scene.bs_displace_direction = bpy.props.EnumProperty(
        name="Displace Direction",
        items=[
            ('X', "X", "Displace along X-axis"),
            ('Y', "Y", "Displace along Y-axis"),
            ('Z', "Z", "Displace along Z-axis"),
            ('NORMAL', "Normal", "Displace along normals")
        ],
        default='NORMAL'
    )
    bpy.types.Scene.bs_preview_subdivision = bpy.props.BoolProperty(
        default=False,
        name="Preview Subdivision",
        update=lambda self, context: update_preview_modifiers(context.scene)
    )
    bpy.types.Scene.bs_preview_displace = bpy.props.BoolProperty(
        default=False,
        name="Preview Displace",
        update=lambda self, context: update_preview_modifiers(context.scene)
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.bs_source
    del bpy.types.Scene.bs_target
    del bpy.types.Scene.bs_shape_keys
    del bpy.types.Scene.bs_shape_key_index
    del bpy.types.Scene.bs_override_existing
    del bpy.types.Scene.bs_key_suffix
    del bpy.types.Scene.show_advanced
    del bpy.types.Scene.show_experimental
    del bpy.types.Scene.bs_strength
    del bpy.types.Scene.bs_falloff

    # Experimental properties
    del bpy.types.Scene.bs_use_subdivision
    del bpy.types.Scene.bs_subdivision_levels
    del bpy.types.Scene.bs_use_displace
    del bpy.types.Scene.bs_displace_strength
    del bpy.types.Scene.bs_displace_midlevel
    del bpy.types.Scene.bs_displace_direction
    del bpy.types.Scene.bs_preview_subdivision
    del bpy.types.Scene.bs_preview_displace

if __name__ == "__main__":
    register()