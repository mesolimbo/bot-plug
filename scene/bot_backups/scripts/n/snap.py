# Save the working file and a numbered snapshot copy; keep the newest 8 snapshots; turn on Blender's auto-save.
import bpy, os, re
WORK = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\scene\bot.blend"
BK = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\scene\bot_backups"
assert bpy.data.filepath.lower() == WORK.lower(), bpy.data.filepath
os.makedirs(BK, exist_ok=True)
fp = bpy.context.preferences.filepaths
fp.use_auto_save_temporary_files = True
fp.auto_save_time = 2
fp.save_version = 3
bpy.ops.wm.save_mainfile()
nums = sorted(int(m.group(1)) for m in (re.match(r"bot_(\d+)\.blend$", f) for f in os.listdir(BK)) if m)
n = (nums[-1] + 1) if nums else 1
dst = os.path.join(BK, "bot_%03d.blend" % n)
bpy.ops.wm.save_as_mainfile(filepath=dst, copy=True)
for old in nums[:-7]:
    os.remove(os.path.join(BK, "bot_%03d.blend" % old))
print("snapshot", dst, os.path.getsize(dst), "working file still", bpy.data.filepath, "objects", len(bpy.data.objects))
