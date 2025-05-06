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

# Generar bloque de features y registrar features declaradas
def generate_feature_block(name, values, group_type, declared_features):
    block = f"{name}\n    {group_type}\n"
    for v in values:
        sanitized_name = sanitize_feature_name(name)
        sanitized_value = sanitize_feature_name(v)
        feature_name = f"{sanitized_name}_{sanitized_value}"
        block += f"        {feature_name}\n"
        declared_features.add(feature_name)
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

# Generar UVL completo y conjunto de features declaradas
def generate_uvl(categories, constraints, root_name):
    single_valued = {'CMC', 'Rarity', 'Power', 'Toughness', 'Loyalty'}
    mandatory = {'CMC', 'Types', 'Rarity'}
    declared_features = set()

    uvl = "features\n"
    root = f"MTG_{sanitize_feature_name(root_name)}"
    uvl += f"    {root}\n"
    declared_features.add(root)

    if 'Types' in categories and 'Land' in categories['Types']:
        if 'CMC' not in categories:
            categories['CMC'] = []
        if '0' not in categories['CMC']:
            categories['CMC'].append('0')

    mand_blocks = ""
    for cat in mandatory:
        if cat in categories and categories[cat]:
            group_type = "alternative" if cat in single_valued else "or"
            block = generate_feature_block(cat, categories[cat], group_type, declared_features)
            mand_blocks += indent_block(block, level=3)
    if mand_blocks:
        uvl += "        mandatory\n" + mand_blocks

    optional_cats = [cat for cat in categories if cat not in mandatory and categories[cat]]
    if optional_cats:
        uvl += "        optional\n"
        for cat in optional_cats:
            group_type = "alternative" if cat in single_valued else "or"
            block = generate_feature_block(cat, categories[cat], group_type, declared_features)
            uvl += indent_block(block, level=3)

    if constraints:
        uvl += "\nconstraints\n"
        for c in constraints:
            uvl += f"    {translate_constraint(c)}\n"

    return uvl, declared_features


def clean_constraint_line(line, declared):
    original_line = line.strip()

    if not original_line or original_line.startswith("#"):
        return line  # conservar línea vacía o comentario

    # Separar por el primer operador de implicación
    match = re.match(r'^(.*?)\s*(=>|<=>)\s*(.*)$', original_line)
    if not match:
        # No es implicación lógica
        identifiers = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', original_line)
        if any(ident not in declared for ident in identifiers):
            return f"# INVALID: {original_line}"
        return original_line

    lhs, op, rhs = match.groups()
    lhs = lhs.strip()
    rhs = rhs.strip()

    # Verificar features del LHS
    lhs_idents = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', lhs)
    if any(ident not in declared for ident in lhs_idents):
        return f"# INVALID: {original_line}"

    # Verificar si RHS es expresión compuesta con | o &
    if '|' in rhs or '&' in rhs:
        operator = '|' if '|' in rhs else '&'
        raw_parts = [p.strip() for p in rhs.split(operator)]
        stripped_parts = [re.sub(r'[^\w_]', '', p) for p in raw_parts]
        valid_parts = [p for p in stripped_parts if p in declared]

        if not valid_parts:
            return f"# INVALID: {original_line}"
        elif len(valid_parts) == 1:
            simplified = f"{lhs} {op} {valid_parts[0]}"
            return f"# INVALID: {original_line}\n    {simplified}"
        else:
            rhs_expr = f"({f' {operator} '.join(valid_parts)})"
            simplified = f"{lhs} {op} {rhs_expr}"
            return f"# INVALID: {original_line}\n    {simplified}"

    # RHS no compuesto (ej. single feature o negación)
    rhs_idents = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', rhs)
    if all(ident in declared for ident in rhs_idents):
        return original_line
    else:
        return f"# INVALID: {original_line}"



# Aplicar limpieza sobre el UVL
def clean_uvl_constraints(uvl_text, declared):
    parts = uvl_text.split('\nconstraints\n')
    if len(parts) == 1:
        return uvl_text

    feature_section, constraint_section = parts
    constraint_lines = constraint_section.strip().split('\n')

    cleaned_constraints = []
    for line in constraint_lines:
        cleaned = clean_constraint_line(line, declared)
        if cleaned:
            cleaned_constraints.append(f"    {cleaned}")

    if not cleaned_constraints:
        return feature_section
    else:
        return feature_section + '\nconstraints\n' + '\n'.join(cleaned_constraints)

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
            uvl_text, declared_features = generate_uvl(categories, constraints, base_name)
            uvl_text_cleaned = clean_uvl_constraints(uvl_text, declared_features)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(uvl_text_cleaned)

            print(f"({idx}/{total}) UVL generado correctamente: {base_name}.uvl")

        except Exception as e:
            print(f"({idx}/{total}) Error en {filename}: {e}")

if __name__ == "__main__":
    main()
