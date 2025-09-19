from pathlib import Path
from ifctester import ids as it_ids
import json

# Input file
var = "ids_files/IDS_demo_BIM-basis-ILS.ids" # can change to any .ids file path

# Extract the stem (filename without extension)
input_path = Path(var)
output_filename = "dumped_" + input_path.stem + ".json"  # "dumped" + same name, just .json
d = it_ids.open(var, validate=False).asdict()
with open(output_filename,"w",encoding="utf8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print(f"dumped {output_filename}")
