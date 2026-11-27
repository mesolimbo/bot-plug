import json, struct, sys
for f in sys.argv[1:]:
    d = open(f, 'rb').read()
    n = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + n])
    per = {m['name']: sum(j['accessors'][p['indices']]['count'] // 3 for p in m['primitives']) for m in j['meshes']}
    print(f, len(d), per, 'TOTAL', sum(per.values()), 'anims', [(a.get('name'), len(a['channels'])) for a in j.get('animations', [])], 'images', [(i.get('name'), i.get('mimeType')) for i in j.get('images', [])],
          'mats', [m['name'] for m in j['materials']], 'skins', [len(s['joints']) for s in j.get('skins', [])])
