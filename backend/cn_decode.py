import math
from typing import Dict, List, Tuple

import pynini

from cn_io import lab2txt

TraceEntry = Dict[str, object]

# Kontrollib kas olek on loppolek
def is_final_state(fst: pynini.Fst, s: int) -> bool:
    return not math.isinf(float(fst.final(s)))

# Muudab arc.weight toenaosused kaaludeks cost = -log(p)
def make_cost_fst(prob_fst: pynini.Fst) -> pynini.Fst:
    wt_type = prob_fst.weight_type()
    cost_fst = prob_fst.copy()

    for s in cost_fst.states():
        arcs = list(cost_fst.arcs(s))
        cost_fst.delete_arcs(s)

        for a in arcs:
            p = float(a.weight)
            val = float("inf") if p <= 0.0 else -math.log(p)
            w = pynini.Weight(wt_type, val)
            cost_fst.add_arc(s, pynini.Arc(a.ilabel, a.olabel, w, a.nextstate))

        final_val = 0.0 if is_final_state(prob_fst, s) else float("inf")
        cost_fst.set_final(s, pynini.Weight(wt_type, final_val))

    return cost_fst

# Leiab koige suurema toenaosusega tee kindla loppoleku puhul
def best_path_trace_to_final(
    cost_fst: pynini.Fst,
    sym: pynini.SymbolTable,
    final_state: int,
) -> Tuple[List[str], float, List[TraceEntry]]:
    tmp = cost_fst.copy()

    for s in tmp.states():
        tmp.set_final(s, float("inf"))
    tmp.set_final(final_state, 0.0)

    tmp_acc = pynini.project(tmp, "input")
    tmp_acc.arcsort("ilabel")

    dist = pynini.shortestdistance(tmp_acc, reverse=True)

    cn_state = tmp_acc.start()
    start_cost = float(dist[cn_state])
    if math.isinf(start_cost):
        return [], 0.0, []

    tokens: List[str] = []
    trace: List[TraceEntry] = []

    while not is_final_state(tmp_acc, cn_state):
        best_arc = None
        best_score = float("inf")

        for a in tmp_acc.arcs(cn_state):
            if a.nextstate >= len(dist):
                continue

            next_dist = float(dist[a.nextstate])
            if math.isinf(next_dist):
                continue

            score = float(a.weight) + next_dist
            if score < best_score:
                best_score = score
                best_arc = a

        if best_arc is None:
            break

        tok = lab2txt(best_arc.ilabel, sym)
        if tok is not None:
            tokens.append(tok)
            trace.append(
                {
                    "cn_state": cn_state,
                    "nextstate": best_arc.nextstate,
                    "ilabel": best_arc.ilabel,
                    "token": tok,
                }
            )

        cn_state = best_arc.nextstate

    prob = math.exp(-start_cost) if not math.isinf(start_cost) else 0.0
    return tokens, prob, trace

# Leiab parimad laused iga loppolekuj kohta
def list_sentence_options_by_final(
    prob_fst: pynini.Fst,
    sym: pynini.SymbolTable,
    top_n: int = 10,
) -> Tuple[List[Tuple[str, float, int]], pynini.Fst]:

    cost_fst = make_cost_fst(prob_fst)
    finals = [s for s in prob_fst.states() if is_final_state(prob_fst, s)]

    candidates: List[Tuple[str, float, int]] = []
    for f in finals:
        toks, prob, _trace = best_path_trace_to_final(cost_fst, sym, f)
        sent = " ".join(toks).strip()
        if sent:
            candidates.append((sent, prob, f))

    best: Dict[str, Tuple[float, int]] = {}
    for sent, prob, f in candidates:
        if sent not in best or prob > best[sent][0]:
            best[sent] = (prob, f)

    ranked = sorted([(s, p, f) for s, (p, f) in best.items()], key=lambda x: x[1], reverse=True)
    return ranked[:top_n], cost_fst

# Leiab uhe sonalised alternatiivid etteantud sonale
def alternatives_for_word(
    prob_fst: pynini.Fst,
    sym: pynini.SymbolTable,
    trace_entry: TraceEntry,
    require_same_nextstate: bool = True,
) -> List[Tuple[str, float, int, int]]:
    s = int(trace_entry["cn_state"])
    chosen_next = trace_entry.get("nextstate")
    chosen_next = int(chosen_next) if chosen_next is not None else None

    alts: List[Tuple[str, float, int, int]] = []
    for a in prob_fst.arcs(s):
        if a.ilabel == 0:
            continue
        if require_same_nextstate and chosen_next is not None and a.nextstate != chosen_next:
            continue

        tok = lab2txt(a.ilabel, sym)
        if tok is None:
            continue

        alts.append((tok, float(a.weight), a.ilabel, a.nextstate))

    alts.sort(key=lambda x: x[1], reverse=True)
    return alts

PhraseAlt = Dict[str, object]

def _dfs_phrase_paths(
    prob_fst: pynini.Fst,
    sym: pynini.SymbolTable,
    start_state: int,
    end_state: int,
    max_tokens: int,
    max_steps: int = 50,
) -> List[Tuple[List[str], float, List[TraceEntry]]]:

    results: List[Tuple[List[str], float, List[TraceEntry]]] = []

    stack: List[Tuple[int, List[str], float, List[TraceEntry], int]] = [
        (start_state, [], 1.0, [], 0)
    ]

    while stack:
        state, toks, prob, tr, steps = stack.pop()
        if steps > max_steps:
            continue

        if state == end_state:
            results.append((toks, prob, tr))
            continue

        if len(toks) >= max_tokens:
            continue

        for a in prob_fst.arcs(state):
            next_state = a.nextstate
            p = float(a.weight)

            if a.ilabel == 0:
                stack.append((next_state, toks, prob, tr, steps + 1))
                continue

            tok = lab2txt(a.ilabel, sym)
            if tok is None:
                continue

            new_toks = toks + [tok]
            new_prob = prob * p
            new_tr = tr + [{
                "cn_state": state,
                "nextstate": next_state,
                "ilabel": a.ilabel,
                "token": tok,
            }]

            stack.append((next_state, new_toks, new_prob, new_tr, steps + 1))

    return results

def _trim_common_prefix_suffix(orig: list[str], cand: list[str]) -> tuple[int, int, list[str]]:
    """Eemaldab ühise prefiksi ja sufiksi nii, et algne vahemik ei muutuks tühjaks."""
    # Ühine prefiks
    p = 0
    while p < len(orig) and p < len(cand) and orig[p] == cand[p]:
        p += 1

    # Prefiks ei tohi katta kogu algset vahemikku
    if p >= len(orig):
        p = max(0, len(orig) - 1)

    o_rem = orig[p:]
    c_rem = cand[p:]

    # Ühine sufiks, jättes algsesse vahemikku vähemalt ühe tokeni
    s = 0
    while (
        s < len(o_rem)
        and s < len(c_rem)
        and o_rem[-1 - s] == c_rem[-1 - s]
        and (len(o_rem) - (s + 1)) >= 1
    ):
        s += 1

    trimmed = c_rem[: len(c_rem) - s] if s > 0 else c_rem
    return p, s, trimmed


def alternatives_for_span(
    prob_fst: pynini.Fst,
    sym: pynini.SymbolTable,
    tokens: List[str],
    trace: List[TraceEntry],
    idx: int,
    max_back: int = 3,
    max_forward: int = 3,
    max_phrase_len: int = 5,
    top_k: int = 25,
) -> List[PhraseAlt]:
    """Leiab fraasialternatiivid valitud sõna ümbrusest."""
    if idx < 0 or idx >= len(trace):
        return []

    start_min = max(0, idx - max_back)
    end_max = min(len(trace) - 1, idx + max_forward)

    best: Dict[Tuple[int, int, Tuple[str, ...]], PhraseAlt] = {}

    for j in range(start_min, idx + 1):
        start_state = int(trace[j]["cn_state"])

        for k in range(idx, end_max + 1):
            end_state = int(trace[k]["nextstate"])
            orig_span = tokens[j:k + 1]

            paths = _dfs_phrase_paths(
                prob_fst=prob_fst,
                sym=sym,
                start_state=start_state,
                end_state=end_state,
                max_tokens=max_phrase_len,
            )

            for phrase_toks, phrase_prob, phrase_trace in paths:
                # Tühi fraas tähendab kustutust
                pref_len, suff_len, trimmed_phrase = _trim_common_prefix_suffix(orig_span, phrase_toks)

                new_start = j + pref_len
                new_end = k - suff_len

                if new_start > new_end:
                    continue

                # Valitud sõna peab jääma muudetava vahemiku sisse
                if not (new_start <= idx <= new_end):
                    continue

                # Kärbib trace'i fraasiga samal viisil
                trimmed_trace = (
                    phrase_trace[pref_len: len(phrase_trace) - suff_len]
                    if suff_len > 0
                    else phrase_trace[pref_len:]
                )

                # Jätab muutmata fraasid vahele
                if trimmed_phrase == tokens[new_start:new_end + 1]:
                    continue

                # Mittetühja fraasi puhul peab trace'i pikkus sellega kattuma
                if len(trimmed_phrase) != len(trimmed_trace):
                    # Kustutuse puhul võivad fraas ja trace olla tühjad
                    if not (len(trimmed_phrase) == 0 and len(trimmed_trace) == 0):
                        continue

                # Ühesõnalised asendused kuvatakse sõnaalternatiivide all
                orig_len = new_end - new_start + 1
                if orig_len == 1 and len(trimmed_phrase) == 1:
                    continue

                alt: PhraseAlt = {
                    "start_idx": new_start,
                    "end_idx": new_end,
                    "phrase": trimmed_phrase,
                    "prob": phrase_prob,
                    "trace": trimmed_trace,
                }

                key = (new_start, new_end, tuple(trimmed_phrase))
                if key not in best or float(phrase_prob) > float(best[key]["prob"]):
                    best[key] = alt

    ranked = sorted(best.values(), key=lambda d: float(d["prob"]), reverse=True)
    return ranked[:top_k]