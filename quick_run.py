'''
from pyids import readIDS, toPydantic
ids_obj = readIDS("sample1.ids")       # needs ifctester installed (optional extra)
model = toPydantic(ids_obj)
print(model.model_dump_json(indent=2))
'''

'''
from pathlib import Path
from pyids import readIDS, toPydantic

ids_obj = readIDS("ids_files/IDS_demo_BIM-basis-ILS.ids") #sample1.ids
model = toPydantic(ids_obj)
print(model.model_dump_json(indent=2))

Path("IDS_demo_BIM-basis-ILS.json").write_text(
    model.model_dump_json(indent=2),
    encoding="utf-8"
)
print("✅ JSON saved to IDS_demo_BIM-basis-ILS.json")
'''

from pyids import readIDS, toPydantic
from pathlib import Path

# Input file
var = "ids_files/IDS_demo_BIM-basis-ILS.ids" # can change to any .ids file path

# Extract the stem (filename without extension)
input_path = Path(var)
output_filename = input_path.stem + ".json"  # same name, just .json

# Read + convert
ids_obj = readIDS(var)
model = toPydantic(ids_obj)

# Save in current working directory
Path(output_filename).write_text(model.model_dump_json(indent=2), encoding="utf-8")

print(f"✅ Saved {output_filename}")
