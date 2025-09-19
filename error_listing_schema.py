import xmlschema

schema = xmlschema.XMLSchema("ids.xsd")
# raises exception if totally broken; use iter_errors for detailed list
errors = list(schema.iter_errors("sample1.ids"))
if not errors:
    print("Valid ✅")
else:
    for err in errors:
        print(err)   # shows location and message


schema = xmlschema.XMLSchema("ids.xsd")

'''
for qname, elem in schema.elements.items():
    print(qname, "->", elem.type)   # high level; dive deeper if needed

for child in schema.elements['ids'].type.content.iter_elements():
    print(child.name, "->", child.type)

specs_elem = schema.elements['ids'].type.content[1]  # 0=info, 1=specifications
for child in specs_elem.type.content.iter_elements():
    print(child.name, "->", child.type)

spec_elem = specs_elem.type.content[0]  # the 'specification' element
for child in spec_elem.type.content.iter_elements():
    print(child.name, "->", child.type)
'''
specs_elem = schema.elements['ids'].type.content[1]  # 0=info, 1=specifications
spec_elem = specs_elem.type.content[0]  # the 'specification' element

req_elem = list(spec_elem.type.content.iter_elements())[1]  # second child = requirements
for child in req_elem.type.content.iter_elements():
    print(child.name, "->", child.type)
