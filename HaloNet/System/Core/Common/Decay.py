import re


def decay_stripall(docstring):
    if docstring is None:
        return None
    lines = docstring.split("\n")
    for index, line in enumerate(lines):
        lines[index] = line.strip()

    lines = [line.strip() for line in lines if line]

    description = "\n".join(lines)
    return description


def decay_simple(spec_name, docstring):
    if docstring is None:
        return None, ""

    specs_string = re.findall(f"@{spec_name}.*", docstring)
    if specs_string:
        specs_string = specs_string[0]
    else:
        specs_string = ""
    docstring = docstring.replace(specs_string, "")

    res_str = (specs_string.replace(f"@{spec_name}:", "") + " ").strip()
    res_str = (res_str.replace(f"@{spec_name}", "") + " ").strip()


    return docstring, res_str


def decay_multiple(spec_name, docstring):
    if docstring is None:
        return None, {}
    specs_string = re.findall(f"@{spec_name}.*", docstring)

    specs_descrs = dict()
    for spec_str in specs_string:
        p_str = spec_str.replace(f"@{spec_name} ", "") + " "
        spec_name_raw = re.findall("((^[^\s]*\s)|(.*:))", p_str)[0][0]
        spec_name_in = spec_name_raw.replace(":", "").replace(" ", "").strip()
        spec_descr = p_str.replace(spec_name_raw, "")
        # print(param_name, " - ",  param_descr)
        specs_descrs[spec_name_in] = spec_descr.strip()
        docstring = docstring.replace(spec_str, "")




    return docstring, specs_descrs


def get_decayed_docstring(docstring, simples=list(), multiples=list()):
    decayed_simples = list()
    for simple in simples:
        docstring, simple_decayed = decay_simple(simple, docstring)
        decayed_simples.append(simple_decayed)

    decayed_multiples = list()
    for multiple in multiples:
        docstring, multiple_decayed = decay_multiple(multiple, docstring)
        decayed_multiples.append(multiple_decayed)

    description = decay_stripall(docstring)

    return description, decayed_simples, decayed_multiples
