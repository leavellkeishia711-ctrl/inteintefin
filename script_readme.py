import re

file_path = '02-product-docs/README.md'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure STAGE2_STATUS.md is annotated as source of truth.
if 'Source of truth for Stage 2' not in content:
    content = content.replace('- **[STAGE2_STATUS.md](./STAGE2_STATUS.md)**', '- **[STAGE2_STATUS.md](./STAGE2_STATUS.md)** (Source of truth for Stage 2 status)')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

file_path2 = 'README.md'
if os.path.exists(file_path2):
    with open(file_path2, 'r', encoding='utf-8') as f:
        content2 = f.read()
    if 'STAGE2_STATUS.md' not in content2:
        content2 = content2.replace('02-product-docs/ROADMAP.md', '02-product-docs/ROADMAP.md (See [STAGE2_STATUS.md](02-product-docs/STAGE2_STATUS.md) for Stage 2 source of truth)')
        with open(file_path2, 'w', encoding='utf-8') as f:
            f.write(content2)
