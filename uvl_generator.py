import os
import re

# Carpetas de entrada y salida
variant_dir = r"C:\Users\Usuario\Desktop\TFG-Project\variants"
output_dir = r"C:\Users\Usuario\Desktop\TFG-Project\UVL"
constraint_file = r"C:\Users\Usuario\Desktop\TFG-Project\mtg_fm_restrictions_v5.txt"

def parse_variants(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    categories = {}
    for line in lines:
        if ":" in line:
            key, values = line.split(":", 1)
            key = key.strip()
            value_set = eval(values.strip())
            categories[key] = sorted(str(v).strip("'") for v in value_set if str(v).strip())
    return categories

def sanitize_feature_name(name):
    return str(name).replace("*", "star").replace(" ", "_")

def generate_feature_block(name, values):
    block = f"{name}\n    or\n"
    for v in values:
        block += f"        {sanitize_feature_name(name)}_{sanitize_feature_name(v)}\n"
    return block

def parse_constraints(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def indent_block(block, level=1):
    indent = "    " * level
    return "".join(indent + line if line.strip() else line for line in block.splitlines(True))

def translate_constraint(line):
    replacements = {
        "==": "==",
        "!=": "!=",
        "<=": "<=",
        ">=": ">=",
        "<": "<",
        ">": ">",
        "=>": "=>",
        "and": "and",
        "or": "or",
        "(": "(",
        ")": ")"
    }
    pattern = r"([A-Za-z_]+)\s*([=!<>]+)\s*'?(.*?)'?"
    def repl(match):
        left, op, right = match.groups()
        if op == "==":
            return f"{sanitize_feature_name(left)}_{sanitize_feature_name(right)}"
        elif op == "!=":
            return f"!{sanitize_feature_name(left)}_{sanitize_feature_name(right)}"
        else:
            return match.group(0)
    for k, v in replacements.items():
        line = line.replace(k, v)
    line = re.sub(pattern, repl, line)
    return line

def generate_uvl(categories, constraints):
    uvl = "features\n"
    uvl += "    MTG_2ED_Unlimited\n"
    uvl += "        optional\n"
    for cat, values in categories.items():
        if values:
            block = generate_feature_block(cat, values)
            uvl += indent_block(block, level=3)
    if constraints:
        uvl += "\nconstraints\n"
        for c in constraints:
            uvl += f"    {translate_constraint(c)}\n"
    return uvl

def main():
    files = [f for f in os.listdir(variant_dir) if f.endswith(".dat")]
    constraints = parse_constraints(constraint_file)
    total = len(files)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for idx, filename in enumerate(files, start=1):
        full_path = os.path.join(variant_dir, filename)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.uvl")

        try:
            categories = parse_variants(full_path)
            uvl_text = generate_uvl(categories, constraints)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(uvl_text)
            print(f"({idx}/{total}) Generación UVL correcta: {base_name}.uvl")
        except Exception as e:
            print(f"({idx}/{total}) Error en {filename}: {e}")

if __name__ == "__main__":
    main()
