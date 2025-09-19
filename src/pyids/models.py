from __future__ import annotations
from pydantic import BaseModel, Field
from pydantic import model_validator, field_validator
from typing import List, Optional, Any, Union

class InfoModel(BaseModel):
    title: Optional[str] = None
    copyright: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    purpose: Optional[str] = None

class EntityNameModel(BaseModel):
    simpleValue: str

def _ensure_list_of_str(x) -> List[str]:
    """Return a list of strings extracted from x (str, list, dict wrappers)."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        # unwrap common wrappers
        if "simpleValue" in x:
            return [str(x["simpleValue"])]
        if "@value" in x:
            return [str(x["@value"])]
        # xs:restriction / enumeration shape: try to collect enumerated @value children
        enums = x.get("xs:restriction") or x.get("restriction") or x.get("xs:enumeration") or x.get("enumeration")
        if isinstance(enums, list):
            vals = []
            for e in enums:
                if isinstance(e, dict):
                    # enumeration inside restriction
                    for k in ("xs:enumeration", "enumeration"):
                        if k in e and isinstance(e[k], list):
                            vals.extend([str(it.get("@value")) for it in e[k] if isinstance(it, dict) and "@value" in it])
                    # direct enumeration list
                    if "@value" in e:
                        vals.append(str(e["@value"]))
            if vals:
                return vals
        # fallback: collect the first textual child
        for v in x.values():
            if isinstance(v, str):
                return [v]
        return [str(x)]
    # fallback
    return [str(x)]


class EntityModel(BaseModel):
    # canonical: always a list of allowed names
    name: List[str]

    @model_validator(mode="before")
    def normalize_name(cls, v):
        """
        Accept:
         - {"name": {"simpleValue": "IFC..."}}
         - {"name": ["IFC1", "IFC2"]}
         - {"name": "IFC..."}
         or even raw "IFC..." in some odd cases
        and return {"name": [...]}
        """
        # case: we get the whole mapping for an EntityModel
        if isinstance(v, dict):
            if "name" in v:
                names = _ensure_list_of_str(v["name"])
                return {"name": names}
            # maybe already normalized with string/list directly under v
            # try to coerce if top-level dict contains single str/list
            if len(v) == 1:
                key, val = next(iter(v.items()))
                if key in ("name", "simpleValue", "@value"):
                    return {"name": _ensure_list_of_str(val)}
            return v
        # case: a string or list passed straight in
        if isinstance(v, (str, list)):
            return {"name": _ensure_list_of_str(v)}
        return v


class PropertyModel(BaseModel):
    # canonical: baseName/propertySet are single strings (or None)
    baseName: Optional[str] = None
    propertySet: Optional[str] = None

    # value may be a scalar, a list of scalars (enumeration), or a dict for numeric bounds
    value: Optional[Union[str, List[str], dict]] = None

    # keep these flexible, but validators could coerce them too if you want
    dataType: Optional[Union[str, List[str]]] = None
    cardinality: Optional[Union[str, List[str]]] = None
    instructions: Optional[Union[str, List[str]]] = None
    uri: Optional[Union[str, List[str]]] = None

    @model_validator(mode="before")
    def normalize_property(cls, v):
        """
        Normalize incoming property dict shapes to a canonical form:
        - propertySet/baseName -> first scalar string (or None)
        - value -> either str, list[str] (enumeration), or dict for ranges
        """
        if not isinstance(v, dict):
            return v

        out = dict(v)  # copy so we don't mutate caller data

        def _first_scalar(x):
            if x is None:
                return None
            if isinstance(x, list):
                x = x[0] if x else None
            if isinstance(x, dict):
                if "simpleValue" in x:
                    return x["simpleValue"]
                if "@value" in x:
                    return x["@value"]
                # try enumeration inside restriction
                enums = x.get("xs:restriction") or x.get("restriction") or x.get("xs:enumeration") or x.get("enumeration")
                if isinstance(enums, list):
                    vals = []
                    for e in enums:
                        if isinstance(e, dict):
                            if "@value" in e:
                                vals.append(e["@value"])
                            # enumeration nested under keys
                            for k in ("xs:enumeration", "enumeration"):
                                if k in e and isinstance(e[k], list):
                                    vals.extend([it.get("@value") for it in e[k] if isinstance(it, dict) and "@value" in it])
                    if vals:
                        return vals[0]
                # xs:pattern -> try to return the pattern string
                pat = x.get("xs:pattern") or x.get("pattern")
                if isinstance(pat, list) and pat:
                    first = pat[0]
                    if isinstance(first, dict) and "@value" in first:
                        return first["@value"]
                # fallback to stringifying
                return str(x)
            return x

        out["propertySet"] = _first_scalar(out.get("propertySet"))
        out["baseName"] = _first_scalar(out.get("baseName"))

        # normalize value into either a single string, list of strings, or dict
        val = out.get("value")
        if isinstance(val, list) and val and isinstance(val[0], dict) and "@value" in val[0]:
            # list of {"@value": "..."} -> list[str]
            out["value"] = [str(i.get("@value")) for i in val if isinstance(i, dict) and "@value" in i]
        elif isinstance(val, dict):
            # common simple wrappers
            if "simpleValue" in val:
                out["value"] = val["simpleValue"]
            elif "@value" in val:
                out["value"] = val["@value"]
            else:
                # complex restriction object: try enum extraction first
                restr = val.get("xs:restriction") or val.get("restriction")
                if isinstance(restr, list):
                    # find enumerations
                    for r in restr:
                        enums = r.get("xs:enumeration") or r.get("enumeration")
                        if isinstance(enums, list):
                            out["value"] = [str(e.get("@value")) for e in enums if isinstance(e, dict) and "@value" in e]
                            break
                    else:
                        # no enumerations -> try numeric bounds
                        r0 = restr[0]
                        mn = r0.get("xs:minInclusive") or r0.get("xs:minExclusive")
                        mx = r0.get("xs:maxInclusive") or r0.get("xs:maxExclusive")
                        dd = {}
                        if isinstance(mn, list) and mn and isinstance(mn[0], dict) and "@value" in mn[0]:
                            dd["min"] = mn[0]["@value"]
                        if isinstance(mx, list) and mx and isinstance(mx[0], dict) and "@value" in mx[0]:
                            dd["max"] = mx[0]["@value"]
                        if dd:
                            out["value"] = dd
        # final cleanup: if propertySet/baseName ended up empty, set to None
        if out.get("propertySet") == "":
            out["propertySet"] = None
        if out.get("baseName") == "":
            out["baseName"] = None

        return out

class ApplicabilityModel(BaseModel):
    entity: List[EntityModel]
    # these are stored as attributes in the dict; we provide aliases
    minOccurs: Optional[int] = Field(None, alias='@minOccurs')
    maxOccurs: Optional[str] = Field(None, alias='@maxOccurs')

class RequirementModel(BaseModel):
    # a requirement might be property-checks or other checks; allow both
    description: Optional[str] = Field(None, alias='@description')
    entity: Optional[List[EntityModel]] = None
    partOf: Optional[List[Any]] = None
    classification: Optional[List[Any]] = None
    attribute: Optional[List[Any]] = None
    property: Optional[List[PropertyModel]] = None
    material: Optional[List[Any]] = None
    # fallback to raw data if unknown
    raw: Optional[Any] = None

    '''
    @classmethod
    def model_validate(cls, value):
        # Accept multiple shapes; if dict contains 'property' map to PropertyModel
        if isinstance(value, dict) and 'property' in value:
            props = value.get('property')
            if isinstance(props, dict):
                props = [props]
            prop_objs = [PropertyModel.model_validate(p) if not isinstance(p, PropertyModel) else p for p in props]
            return cls(property=prop_objs)
        return super().model_validate(value)
    '''
    @classmethod
    def model_validate(cls, value):
        # Wrap single requirement dict into a list (if needed)
        if isinstance(value, dict):
            # Convert property if present
            props = value.get('property')
            if props:
                if isinstance(props, dict):
                    props = [props]
                value['property'] = [PropertyModel.model_validate(p) if not isinstance(p, PropertyModel) else p for p in props]
            return cls(**value)
        return super().model_validate(value)

class SpecificationModel(BaseModel):
    name: str = Field(..., alias='@name')
    ifcVersion: Optional[List[str]] = Field(None, alias='@ifcVersion')
    applicability: Optional[ApplicabilityModel] = None
    #requirements: Optional[Any] = None  # refine later to List[RequirementModel]
    requirements: Optional[List[RequirementModel]] = None

    @model_validator(mode="before")
    def ensure_requirements_list(cls, values):
        req = values.get("requirements")
        if req and not isinstance(req, list):
            values["requirements"] = [req]
        return values

class SpecificationsContainer(BaseModel):
    specification: List[SpecificationModel]

class IdsModel(BaseModel):
    xmlns: Optional[str] = Field(None, alias='@xmlns')
    xmlns_xs: Optional[str] = Field(None, alias='@xmlns:xs')
    xmlns_xsi: Optional[str] = Field(None, alias='@xmlns:xsi')
    xsi_schemaLocation: Optional[str] = Field(None, alias='@xsi:schemaLocation')
    info: Optional[InfoModel] = None
    specifications: Optional[SpecificationsContainer] = None

    model_config = {"extra": "allow"}  # accept fields we haven't modeled yet
