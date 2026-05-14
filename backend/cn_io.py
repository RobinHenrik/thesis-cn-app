import pynini

# Laeb sumbolite tabeli failist
def load_sym(path: str):
    return pynini.SymbolTable.read_text(path)

# Laeb segadusvorgu failist
def load_fst(path: str):
    return pynini.Fst.read(path)

# Konverteerib labeli tokeniks
def lab2txt(lbl: int, syms):
    if lbl == 0:
        return None
    return syms.find(lbl) if syms is not None else str(lbl)