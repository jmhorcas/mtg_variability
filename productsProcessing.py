import os
import pandas as pd

# Directorios
input_dir = "./products"
output_dir = "./feature_models_txt"

# Crear directorio de salida si no existe
os.makedirs(output_dir, exist_ok=True)

# Campos que vamos a transformar en ramas del Feature Model
feature_fields = [
    "CMC", "Colors", "Color identity", "Rarity", "Types", "Subtypes", "Power", "Toughness"
]

# Recorremos todos los archivos CSV en ./products
for filename in os.listdir(input_dir):
    if filename.endswith(".csv"):
        csv_path = os.path.join(input_dir, filename)
        expansion_name = os.path.splitext(filename)[0].replace(" ", "_")  # sin extensión, sin espacios

        # Cargar el CSV
        df = pd.read_csv(csv_path)

        # Construcción del FM en texto
        fm_text = f"{expansion_name} :\n"

        for field in feature_fields:
            values = set()
            if field not in df.columns:
                continue
            for v in df[field].dropna():
                if field in ["Colors", "Color identity", "Types", "Subtypes"]:
                    try:
                        items = eval(v) if isinstance(v, str) and v.startswith("[") else [v]
                    except:
                        items = [v]
                else:
                    items = [v]
                values.update(map(str, items))

            fm_text += f"  {field} :\n"
            for val in sorted(values):
                val_clean = val.replace("'", "").replace('"', '').replace(",", "").strip()
                if val_clean:
                    fm_text += f"    - {val_clean}\n"

        # Guardar el archivo de salida
        output_path = os.path.join(output_dir, f"{expansion_name}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(fm_text)

        print(f"✅ Feature Model generado: {output_path}")
