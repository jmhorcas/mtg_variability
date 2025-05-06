import os
import re

# Carpetas de entrada y salida
variant_dir = r"C:\Users\Usuario\Desktop\TFG-Project\variants"
output_dir = r"C:\Users\Usuario\Desktop\TFG-Project\UVL"
constraint_file = r"C:\Users\Usuario\Desktop\TFG-Project\mtg_fm_restrictions_v7.txt"

# Leer restricciones externas
def parse_constraints(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Parsear variantes desde .dat
def parse_variants(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    categories = {}
    for line in lines:
        if ":" in line:
            key, values = line.split(":", 1)
            value_set = eval(values.strip())
            categories[key.strip()] = sorted(str(v).replace("'", "").strip() for v in value_set)
    return categories

# Sanitizar nombres de características
def sanitize_feature_name(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name.replace("*", "star").replace(".", "_").replace(" ", "_"))

# Generar bloque de features
def generate_feature_block(name, values, group_type):
    block = f"{name}\n    {group_type}\n"
    for v in values:
        sanitized_name = sanitize_feature_name(name)
        sanitized_value = sanitize_feature_name(v)
        block += f"        {sanitized_name}_{sanitized_value}\n"
    return block

# Indentar bloques correctamente
def indent_block(block, level=1):
    indent = "    " * level
    return "".join(indent + line if line.strip() else line for line in block.splitlines(True))

# Traducir restricciones externas
def translate_constraint(line):
    tokens = re.split(r'(\W)', line)
    translated = [sanitize_feature_name(token) if re.match(r'[A-Za-z]', token) else token for token in tokens]
    return ''.join(translated)

# Generar UVL correcto
def generate_uvl(categories, constraints, root_name):
    single_valued = {'CMC', 'Rarity', 'Power', 'Toughness', 'Loyalty'}
    mandatory = {'CMC', 'Types', 'Rarity'}

    uvl = "features\n"
    uvl += f"    MTG_{sanitize_feature_name(root_name)}\n"

    # Añadir automáticamente CMC_0 si hay tierras
    if 'Types' in categories and 'Land' in categories['Types']:
        if 'CMC' not in categories:
            categories['CMC'] = []
        if '0' not in categories['CMC']:
            categories['CMC'].append('0')

    # Bloques obligatorios
    mand_blocks = ""
    for cat in mandatory:
        if cat in categories and categories[cat]:
            group_type = "alternative" if cat in single_valued else "or"
            block = generate_feature_block(cat, categories[cat], group_type)
            mand_blocks += indent_block(block, level=3)
    if mand_blocks:
        uvl += "        mandatory\n" + mand_blocks

    # Bloques opcionales
    optional_cats = [cat for cat in categories if cat not in mandatory and categories[cat]]
    if optional_cats:
        uvl += "        optional\n"
        for cat in optional_cats:
            group_type = "alternative" if cat in single_valued else "or"
            block = generate_feature_block(cat, categories[cat], group_type)
            uvl += indent_block(block, level=3)

    # Agregar restricciones comunes
    if constraints:
        uvl += "\nconstraints\n"
        for c in constraints:
            uvl += f"    {translate_constraint(c)}\n"

    return uvl
import re

def extract_declared_features(uvl_text):
    declared = set()

    # Features: lines like 'Subtypes_Angel', 'Types_Creature'
    for match in re.finditer(r'^\s+(?:mandatory|optional)?\s*(\w+_\w+)', uvl_text, re.MULTILINE):
        declared.add(match.group(1))

    # Attributes: lines like 'Power : int [...]'
    for match in re.finditer(r'^\s*(\w+)\s*:\s*', uvl_text, re.MULTILINE):
        declared.add(match.group(1))

    return declared

def clean_constraint_line(line, declared):
    # Replace features not declared with placeholder to remove them
    tokens = re.split(r'(\W+)', line)  # keep operators
    cleaned = []
    for token in tokens:
        token_stripped = token.strip()
        if token_stripped == '':
            cleaned.append(token)
        elif re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', token_stripped):
            if token_stripped not in declared:
                continue  # skip undeclared
            else:
                cleaned.append(token)
        else:
            cleaned.append(token)

    cleaned_line = ''.join(cleaned).strip()

    # Remove invalid expressions like empty parenthesis or implication without LHS or RHS
    if not cleaned_line or re.match(r'^[()|&! ]*$', cleaned_line):
        return None

    return cleaned_line

# Función principal
def main():
    files = [f for f in os.listdir(variant_dir) if f.endswith(".dat")]
    constraints = parse_constraints(constraint_file)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    total = len(files)
    for idx, filename in enumerate(files, start=1):
        full_path = os.path.join(variant_dir, filename)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.uvl")

        try:
            categories = parse_variants(full_path)
            uvl_text = generate_uvl(categories, constraints, base_name)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(uvl_text)

            print(f"({idx}/{total}) UVL generado correctamente: {base_name}.uvl")
            
        except Exception as e:
            print(f"({idx}/{total}) Error en {filename}: {e}")

if __name__ == "__main__":
    main()