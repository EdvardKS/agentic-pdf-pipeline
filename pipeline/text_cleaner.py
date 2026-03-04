import re


def clean_text(text: str) -> str:

    # eliminar espacios duplicados
    text = re.sub(r"[ \t]+", " ", text)

    # eliminar saltos múltiples
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # eliminar espacios al inicio/final de línea
    text = "\n".join(line.strip() for line in text.splitlines())

    return text.strip()