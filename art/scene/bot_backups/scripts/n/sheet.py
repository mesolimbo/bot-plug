import sys
from PIL import Image
out = sys.argv[1]; cols = int(sys.argv[2]); size = int(sys.argv[3]); files = sys.argv[4:]
ims = [Image.open(f).convert("RGB").resize((size, size)) for f in files]
rows = (len(ims) + cols - 1) // cols
sh = Image.new("RGB", (cols * size, rows * size), (255, 255, 255))
for i, im in enumerate(ims):
    sh.paste(im, ((i % cols) * size, (i // cols) * size))
sh.save(out)
