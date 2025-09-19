from ifctester import ids as it_ids
import json
d = it_ids.open("IDS_ArcDox.ids", validate=False).asdict()
with open("IDS_ArcDox.json","w",encoding="utf8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print("dumped IDS_ArcDox.json")
