import json
from pathlib import Path
import shutil

# Paths
notebook_path = Path(__file__).parent / "sf_business_risk_prediction.ipynb"
backup_path = Path(__file__).parent / "sf_business_risk_prediction_backup.ipynb"

print("🔧 Applying fix to notebook...")
print("="*60)

# Create backup
print(f"📦 Creating backup: {backup_path.name}")
shutil.copy2(notebook_path, backup_path)

# Read notebook
print(f"📖 Reading notebook...")
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Find and fix the cell
print("🔍 Searching for the problematic code...")
fixed = False

for i, cell in enumerate(notebook['cells']):
    if cell['cell_type'] == 'code' and 'source' in cell:
        # Check if this is the download function cell
        source_text = ''.join(cell['source'])
        if 'def download_sf_data' in source_text and '"$order": "record_id DESC"' in source_text:
            print(f"✅ Found Cell #{i} with the issue")
            
            # Fix the source - remove the $order line
            new_source = []
            skip_next = False
            
            for j, line in enumerate(cell['source']):
                if '"$order": "record_id DESC"' in line:
                    print(f"   Removing line: {line.strip()}")
                    continue
                elif line.strip() == '"$limit": limit,' and j+1 < len(cell['source']) and '"$order"' in cell['source'][j+1]:
                    # Change the comma to no comma since $order is being removed
                    new_source.append(line.replace('"$limit": limit,', '"$limit": limit'))
                    print(f"   Updating line: {line.strip()} -> {new_source[-1].strip()}")
                else:
                    new_source.append(line)
            
            cell['source'] = new_source
            fixed = True
            print("✅ Fixed the cell!")
            break

if not fixed:
    print("⚠️ Could not find the issue. It may already be fixed.")
    exit(1)

# Save the fixed notebook
print(f"💾 Saving fixed notebook...")
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2, ensure_ascii=False)

print("\n" + "="*60)
print("✅ SUCCESS! Notebook has been fixed!")
print("="*60)
print("\n📋 What was changed:")
print("   - Removed: \"$order\": \"record_id DESC\"")
print("   - This parameter was causing the 400 Bad Request error")
print("\n🎯 Next steps:")
print("   1. Reload the notebook in Jupyter (or VS Code)")
print("   2. Restart the kernel")
print("   3. Run all cells")
print(f"\n💾 Backup saved to: {backup_path.name}")
print("\nThe API should now work correctly! 🎉")
