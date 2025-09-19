'''
from pyids import readIDS, toPydantic
ids_obj = readIDS("sample1.ids")       # needs ifctester installed (optional extra)
model = toPydantic(ids_obj)
print(model.model_dump_json(indent=2))
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