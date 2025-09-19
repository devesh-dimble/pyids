# pyids

PY_IDS

A lightweight Python utility for working with buildingSMART IDS
 (Information Delivery Specification) files.
This repo lets you:

Parse .ids XML files into Python objects.

Convert IDS into structured Pydantic models for validation.

Export the data to clean JSON format.

Automate batch processing of multiple IDS files.

## 📦 Installation

 Clone the repo and install dependencies:
 
 git clone https://github.com/yourusername/py_ids.git
 cd py_ids
 pip install -r requirements.txt
 
 
 Dependencies include:
 
 pydantic
  – for schema validation
 
 ifctester
  – IDS parsing utilities
 
 pyids
  – local parsing and conversion functions

## 🚀 Usage
### 1. Convert a single IDS file
 
  Use quick_run.py to parse an IDS and dump it as JSON:
  
  python quick_run.py
  
  
  Example (quick_run.py):
  
  from pyids import readIDS, toPydantic
  from pathlib import Path
  
  var = "ids_files/IDS_demo_BIM-basis-ILS.ids"
  
  ids_obj = readIDS(var)
  model = toPydantic(ids_obj)
  
  output_filename = Path(var).stem + ".json"
  Path(output_filename).write_text(model.model_dump_json(indent=2), encoding="utf-8")
  
  print(f"✅ Saved {output_filename}")
  
  
  This produces:
  
  IDS_demo_BIM-basis-ILS.json
  
 ### 2. Bulk convert all IDS files
 
  You can loop over all .ids files in a folder and export them:
  
  from pyids import readIDS, toPydantic
  from pathlib import Path
  
  input_dir = Path("ids_files")
  
  for ids_file in input_dir.glob("*.ids"):
      ids_obj = readIDS(ids_file)
      model = toPydantic(ids_obj)
  
      output_filename = ids_file.stem + ".json"
      Path(output_filename).write_text(model.model_dump_json(indent=2), encoding="utf-8")
      print(f"✅ Saved {output_filename}")
  
 ### 3. Validate IDS and convert with ifctester
 
  For raw conversion (without Pydantic), use save_ids.py:
  
  from ifctester import ids as it_ids
  import json
  
  d = it_ids.open("ids_files/IDS_demo_BIM-basis-ILS.ids", validate=False).asdict()
  with open("IDS_demo_BIM-basis-ILS.json", "w", encoding="utf8") as f:
      json.dump(d, f, indent=2, ensure_ascii=False)
  
  print("✅ dumped IDS_demo_BIM-basis-ILS.json")

## 🛠 Project Structure
 .
 ├───.pytest_cache
 │   └───v
 │       └───cache
 ├───ids_files
 ├───src
 │   ├───pyids
 │   │   └───__pycache__
 │   └───pyids.egg-info
 └───tests
     └───__pycache__
