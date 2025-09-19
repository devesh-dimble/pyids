from pyids.core import toPydantic

def test_to_pydantic_accepts_dict():
    sample = {
        "@xmlns": "http://standards.buildingsmart.org/IDS",
        "info": {"title": "t"},
        "specifications": {"specification": []}
    }
    model = toPydantic(sample)
    assert model.info.title == "t"
