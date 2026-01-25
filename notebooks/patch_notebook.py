"""
Automated Notebook Patcher
This script automatically fixes the API download issue in the Jupyter notebook
"""

import json
import sys
from pathlib import Path


def fix_notebook(notebook_path):
    """Fix the API download function in the notebook"""
    
    print("🔧 Automated Notebook Patcher")
    print("="*60)
    
    # Read the notebook
    print(f"📖 Reading notebook: {notebook_path}")
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find and fix Cell 3 (Download Data Functions)
    fixed = False
    for i, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            
            # Check if this is the download function cell
            if 'def download_sf_data' in source and '"$order": "record_id DESC"' in source:
                print(f"✅ Found the problematic cell (Cell #{i})")
                
                # Fix the source code
                old_params = '''    params = {
        "$limit": limit,
        "$order": "record_id DESC"
    }'''
                
                new_params = '''    params = {
        "$limit": limit
    }'''
                
                # Replace in the source
                new_source = source.replace(old_params, new_params)
                
                # Update the cell
                cell['source'] = new_source.split('\n')
                # Add newlines back
                cell['source'] = [line + '\n' if i < len(cell['source'])-1 else line 
                                 for i, line in enumerate(cell['source'])]
                
                fixed = True
                print("✅ Fixed the $order parameter issue")
                break
    
    if not fixed:
        print("⚠️ Could not find the problematic code. It may have already been fixed.")
        return False
    
    # Create backup
    backup_path = notebook_path.parent / f"{notebook_path.stem}_backup{notebook_path.suffix}"
    print(f"\n💾 Creating backup: {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2)
    
    # Save the fixed notebook
    print(f"💾 Saving fixed notebook: {notebook_path}")
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2)
    
    print("\n✅ Notebook fixed successfully!")
    print("\n📋 What was changed:")
    print("  - Removed the invalid '$order': 'record_id DESC' parameter")
    print("  - The API will now work without ordering")
    print("\n🎯 Next steps:")
    print("  1. Open the notebook in Jupyter")
    print("  2. Restart the kernel (Kernel → Restart)")
    print("  3. Run all cells (Cell → Run All)")
    print(f"\n💡 A backup was saved to: {backup_path.name}")
    
    return True


if __name__ == "__main__":
    # Path to the notebook
    notebook_path = Path(__file__).parent / "sf_business_risk_prediction.ipynb"
    
    if not notebook_path.exists():
        print(f"❌ Error: Notebook not found at {notebook_path}")
        sys.exit(1)
    
    try:
        success = fix_notebook(notebook_path)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
