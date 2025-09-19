import copy
from typing import Any
from pydantic import BaseModel
import importlib
# add imports at top if not present
from typing import Mapping
import json

def _extract_scalar_from_restriction(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        vals = []
        for it in obj:
            v = _extract_scalar_from_restriction(it)
            if v is None:
                continue
            if isinstance(v, list):
                vals.extend(v)
            else:
                vals.append(v)
        return vals if len(vals) > 1 else (vals[0] if vals else None)
    if isinstance(obj, dict):
        if "simpleValue" in obj:
            return obj["simpleValue"]
        if "@value" in obj:
            return obj["@value"]
        if "xs:restriction" in obj or "restriction" in obj:
            inner = obj.get("xs:restriction") or obj.get("restriction")
            return _extract_scalar_from_restriction(inner)
        if "xs:enumeration" in obj or "enumeration" in obj:
            enums = obj.get("xs:enumeration") or obj.get("enumeration")
            return _extract_scalar_from_restriction(enums)
        if "xs:pattern" in obj:
            return _extract_scalar_from_restriction(obj["xs:pattern"])
        if "xs:minExclusive" in obj or "xs:maxExclusive" in obj:
            minv = _extract_scalar_from_restriction(obj.get("xs:minExclusive"))
            maxv = _extract_scalar_from_restriction(obj.get("xs:maxExclusive"))
            return {"minExclusive": minv, "maxExclusive": maxv}
        if "xs:minInclusive" in obj or "xs:maxInclusive" in obj:
            minv = _extract_scalar_from_restriction(obj.get("xs:minInclusive"))
            maxv = _extract_scalar_from_restriction(obj.get("xs:maxInclusive"))
            return {"minInclusive": minv, "maxInclusive": maxv}
        # fallback: try children (first non-None)
        for v in obj.values():
            found = _extract_scalar_from_restriction(v)
            if found is not None:
                return found
    return None

def collapse_empty_requirements(normalized):
    for spec in normalized.get("specifications", {}).get("specification", []):
        reqs = spec.get("requirements")
        if isinstance(reqs, list):
            new = []
            for r in reqs:
                if r is None:
                    continue
                if isinstance(r, dict):
                    # skip totals with all values None/empty
                    if all((v is None or v == [] or v == "") for v in r.values()):
                        continue
                new.append(r)
            spec["requirements"] = new


# Keys we want to force-normalize (common "value carriers")
_NORMALIZE_KEYS = {"name", "baseName", "propertySet", "value", "simpleValue", "@value", "system", "predefinedType", "uri"}

def deep_normalize_values(obj):
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            v = obj[k]
            if k in _NORMALIZE_KEYS:
                ext = _extract_scalar_from_restriction(v)
                if ext is not None:
                    obj[k] = ext
                    continue
            if isinstance(v, (dict, list)):
                deep_normalize_values(v)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                deep_normalize_values(item)


# --- paste/replace these helpers in pyids/core.py ---

def _ensure_list(x):
    if x is None:
        return None
    if isinstance(x, list):
        return x
    return [x]

def _unwrap_simplevalue(maybe):
    """
    Convert shapes like {"simpleValue": "X"} or {"@value":"X"} -> "X".
    Leave other values untouched.
    """
    if isinstance(maybe, dict):
        if "simpleValue" in maybe:
            return maybe["simpleValue"]
        if "@value" in maybe:
            return maybe["@value"]
        # sometimes inner wrappers: { "name": {"simpleValue": "X"} }
        # calling code will unwrap fields explicitly.
    return maybe

def _unwrap_value(maybe):
    if isinstance(maybe, dict):
        if "simpleValue" in maybe:
            return maybe["simpleValue"]
        if "@value" in maybe:
            return maybe["@value"]

        # Handle xs:restriction with xs:pattern or xs:enumeration
        if "xs:restriction" in maybe:
            restrictions = maybe["xs:restriction"]
            if isinstance(restrictions, list):
                # if pattern exists, return its value(s)
                for r in restrictions:
                    if "xs:pattern" in r:
                        return r["xs:pattern"][0]["@value"]
                    if "xs:enumeration" in r:
                        return [e["@value"] for e in r["xs:enumeration"]]
            elif isinstance(restrictions, dict):
                if "xs:pattern" in restrictions:
                    return restrictions["xs:pattern"][0]["@value"]
                if "xs:enumeration" in restrictions:
                    return [e["@value"] for e in restrictions["xs:enumeration"]]

    return maybe

def _normalize_requirements_block(req: dict) -> dict:
    """
    Normalize a single requirements dict so nested children are lists
    and common simpleValue wrappers are unwrapped into strings.
    """
    if not isinstance(req, dict):
        return req

    # Normalize list-like children to lists
    for key in ("property", "attribute", "entity", "partOf", "classification", "material"):
        if key in req:
            req[key] = _ensure_list(req[key])

    # Unwrap nested simpleValue wrappers for common subfields
    # Handle properties
    if "property" in req and isinstance(req["property"], list):
        for p in req["property"]:
            if not isinstance(p, dict):
                continue
            # propertySet might be nested: {"propertySet": {"simpleValue": "Pset..."}}
            if "propertySet" in p:
                p["propertySet"] = _unwrap_value(p["propertySet"]) #_unwrap_simplevalue(p["propertySet"])
            # baseName might be nested similarly
            if "baseName" in p:
                p["baseName"] = _unwrap_value(p["baseName"]) #_unwrap_simplevalue(p["baseName"])
            # value could be nested restriction or simpleValue; unwrap simpleValue if present
            if "value" in p:
                p["value"] = _unwrap_value(p["value"]) #_unwrap_simplevalue(p["value"])
            # sometimes name is used instead of baseName - unwrap if present
            if "name" in p:
                # name might be {"name": {"simpleValue": "..."}}
                if isinstance(p["name"], dict):
                    p["name"] = _unwrap_value(p["name"]) #_unwrap_simplevalue(p["name"])
    # Handle attributes (they often have 'name' and 'value' children)
    if "attribute" in req and isinstance(req["attribute"], list):
        for a in req["attribute"]:
            if not isinstance(a, dict):
                continue
            if "name" in a:
                # name may be {"simpleValue": "..."} or {"name": {"simpleValue": "..."}}
                a["name"] = _unwrap_value(a["name"]) #_unwrap_simplevalue(a["name"])
            if "value" in a:
                a["value"] = _unwrap_value(a["value"]) #_unwrap_simplevalue(a["value"])

    # Handle entities (unwrap entity.name.simpleValue -> string)
    if "entity" in req and isinstance(req["entity"], list):
        for e in req["entity"]:
            if not isinstance(e, dict):
                continue
            if "name" in e and isinstance(e["name"], dict):
                # e["name"] might itself be {"simpleValue": "..."} or {"name": {"simpleValue": "..."}}
                e["name"] = _unwrap_simplevalue(e["name"])
            # if nested like {"name": {"simpleValue": "..."}}, above will return string,
            # else if deeper nesting exists, we leave it (you can extend later).

    return req

def _normalize_ids_dict(d: Mapping) -> dict:
    """
    Mutate and return a normalized copy of the ids.asdict() mapping that
    matches the Pydantic models (lists where lists expected, unwrap simpleValue).
    """
    out = dict(d)  # shallow copy

    specs = out.get("specifications")
    if not specs:
        return out

    spec_list = specs.get("specification")
    if spec_list is None:
        return out

    # ensure spec_list is a list
    if not isinstance(spec_list, list):
        spec_list = [spec_list]
        out["specifications"] = {"specification": spec_list}

    # normalize each specification's 'requirements' field and some attributes
    for spec in spec_list:
        if not isinstance(spec, dict):
            continue
        # ensure '@ifcVersion' is a list if present but is a single string
        if "@ifcVersion" in spec and not isinstance(spec["@ifcVersion"], list):
            spec["@ifcVersion"] = [spec["@ifcVersion"]]

        # Unwrap spec-level attributes that might be single values in dict form
        for attr in ("@description", "@instructions", "@name"):
            if attr in spec and isinstance(spec[attr], dict):
                spec[attr] = _unwrap_simplevalue(spec[attr])

        raw_reqs = spec.get("requirements")
        if raw_reqs is None:
            continue

        normalized_reqs = []
        # ensure we iterate a list of raw requirement blocks
        for raw in _ensure_list(raw_reqs):
            # skip garbage
            if not isinstance(raw, dict):
                continue
            # work on a fresh copy to avoid mutating the original parsed tree
            raw_copy = copy.deepcopy(raw)
            # _normalize_requirements_block should return a NEW dict (we pass a copy to be safe)
            normalized_req = _normalize_requirements_block(raw_copy)
            # only append non-empty dicts
            if isinstance(normalized_req, dict) and any(v is not None and v != [] and v != "" for v in normalized_req.values()):
                normalized_reqs.append(normalized_req)
        # always set a list (possibly empty) — avoids repeated in-place mutations
        spec["requirements"] = normalized_reqs
        # inside each requirement, ensure children are lists and unwrap nested simpleValue
        for r in spec["requirements"]:
            if isinstance(r, dict):
                for key in ("property", "attribute", "entity", "partOf", "classification", "material"):
                    if key in r:
                        r[key] = _ensure_list(r[key])
                # unwrap description attribute if present (alias '@description' might be in top-level)
                if "@description" in r and isinstance(r["@description"], dict):
                    r["@description"] = _unwrap_simplevalue(r["@description"])
                # also unwrap known nested fields if present
                if "property" in r:
                    for p in r["property"]:
                        if isinstance(p, dict):
                            if "propertySet" in p:
                                p["propertySet"] = _unwrap_simplevalue(p["propertySet"])
                            if "baseName" in p:
                                p["baseName"] = _unwrap_simplevalue(p["baseName"])
                            if "value" in p:
                                p["value"] = _unwrap_simplevalue(p["value"])
                if "attribute" in r:
                    for a in r["attribute"]:
                        if isinstance(a, dict):
                            if "name" in a:
                                a["name"] = _unwrap_simplevalue(a["name"])
                            if "value" in a:
                                a["value"] = _unwrap_simplevalue(a["value"])

    return out


def _ensure_ifctester():
    mod = importlib.util.find_spec("ifctester")
    if mod is None:
        raise ImportError(
            "ifctester is not installed. Install optional extras: `pip install pyids[ifc]` "
            "or install ifctester manually."
        )
    import ifctester.ids as it_ids
    return it_ids

def readIDS(path: str):
    """
    Parse an IDS file and return the ifctester.ids.Ids object.
    Requires the optional `ifctester` extra.
    """
    it_ids = _ensure_ifctester()
    return it_ids.open(path, validate=False)

def prune_nulls(obj):
    if isinstance(obj, dict):
        keys = list(obj.keys())
        for k in keys:
            v = obj[k]
            if v is None:
                del obj[k]
            else:
                prune_nulls(v)
    elif isinstance(obj, list):
        for item in obj:
            prune_nulls(item)


def toPydantic(ids_obj: Any) -> BaseModel:
    """
    Convert either an ifctester.ids.Ids instance or a plain dict (from asdict())
    into the pydantic IdsModel defined in models.py.
    """
    from .models import IdsModel

    # accept either an object with 'asdict' or a dict
    if hasattr(ids_obj, "asdict"):
        d = ids_obj.asdict()
    elif isinstance(ids_obj, dict):
        d = ids_obj
    else:
        raise TypeError("ids_obj must be either an ifctester.ids.Ids or a dict")
    
    # Normalize the dict so list-vs-dict shapes match Pydantic expectations
    normalized = _normalize_ids_dict(d)
    deep_normalize_values(normalized)

    return IdsModel.model_validate(normalized)
