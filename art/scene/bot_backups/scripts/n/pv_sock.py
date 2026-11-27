S_ = {"k_back": ((-2,0,0.0),(0,0,0.0),0.3), "k_backq": ((-2,1.0,-0.6),(-0.2,0,0.0),0.3), "k_side": ((-0.2,2,0.0),(-0.2,0,0.0),0.3)}
new_shots(S_, 1000, prefix="n_")
fl = bpy.data.objects["flap"]
rot = fl.rotation_euler.y
fl.rotation_euler.y = 0.0
bpy.context.view_layer.update()
new_shots(S_, 1000, prefix="nc_")
fl.rotation_euler.y = rot
bpy.context.view_layer.update()
