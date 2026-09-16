import os
import zipfile
import json

bundle_dir = 'dist/thesis_references_bundle'
print('Bundle files in directory:')
for f in os.listdir(bundle_dir):
    p = os.path.join(bundle_dir, f)
    print(f'  {f}: {os.path.getsize(p):,} bytes')

zip_path = 'dist/thesis_references_bundle.zip'
print(f'\nZip file {zip_path}: {os.path.getsize(zip_path):,} bytes')
with zipfile.ZipFile(zip_path, 'r') as zf:
    print('Zip contents:')
    for info in zf.infolist():
        print(f'  {info.filename}: {info.file_size:,} bytes (compressed: {info.compress_size:,} bytes)')

data = json.load(open(os.path.join(bundle_dir, 'thesis_references.json'), encoding='utf-8'))
print(f'\nJSON verification: {len(data["topics"])} topics, {len(data["sources"])} sources')

