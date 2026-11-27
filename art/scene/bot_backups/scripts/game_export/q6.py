import bpy
q = bpy.context.scene.qremesher
print({p.identifier: getattr(q, p.identifier) for p in q.bl_rna.properties if p.identifier != "rna_type"})
