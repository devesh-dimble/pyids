from ifctester import ids as it_ids
import json
d = it_ids.open("ids_files/IDS_demo_BIM-basis-ILS.ids", validate=False).asdict()
with open("IDS_demo_BIM-basis-ILS.json","w",encoding="utf8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print("dumped IDS_demo_BIM-basis-ILS.json")
