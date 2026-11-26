import bpy
G = "C:/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad/g"
node = bpy.data.materials["bot_game_mat"].node_tree.nodes["bake"]
on = node.image
off = bpy.data.images.get("bot_off.jpg") or bpy.data.images.load(G + "/bot_off.jpg")
off.reload(); node.image = off
exec(open(G + "/e_views.py", encoding="utf-8").read().replace('"/view_"', '"/off_view_"'))
node.image = on
