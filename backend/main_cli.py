from cn_io import load_fst, load_sym
from cn_decode import (
    list_sentence_options_by_final,
    best_path_trace_to_final,
    alternatives_for_word,
    alternatives_for_span,
)

FST_PATH = "fst_clean_i0.fst"
SYMS_PATH = "syms_i0.txt"
TOP_N = 6


def print_sentence_with_indices(tokens):
    print("\nSentence:")
    for i, t in enumerate(tokens):
        print(f"{i:>2}:{t}", end="  ")
    print("\n")


def main():
    sym = load_sym(SYMS_PATH)
    prob_fst = load_fst(FST_PATH)

    options, cost_fst = list_sentence_options_by_final(prob_fst, sym, top_n=TOP_N)

    print("\n=== Sentence options (best per final state) ===")
    for i, (sent, prob, f) in enumerate(options, 1):
        print(f"{i:>2}. p≈{prob:.4g}  (final={f})  {sent}")

    choice = input(f"\nChoose option [1-{len(options)}] (or q): ").strip()
    if choice.lower() == "q":
        return

    opt_idx = int(choice) - 1
    _sent, _prob, final_state = options[opt_idx]

    tokens, prob, trace = best_path_trace_to_final(cost_fst, sym, final_state)

    print(f"\nSelected (final={final_state}) p≈{prob:.4g}")
    print_sentence_with_indices(tokens)

    while True:
        cmd = input("Enter word index to see alternatives (or q): ").strip()
        if cmd.lower() == "q":
            break
        if not cmd.isdigit():
            print("Please enter a number or q.")
            continue

        idx = int(cmd)
        if idx < 0 or idx >= len(trace):
            print("Index out of range.")
            continue

        # 1) One-word alts (same merge state)
        one_word = alternatives_for_word(prob_fst, sym, trace[idx], require_same_nextstate=True)

        # 2) Phrase alts: can start up to 2 words to the left, max 3 tokens long
        phrase_alts = alternatives_for_span(
            prob_fst=prob_fst,
            sym=sym,
            tokens=tokens,
            trace=trace,
            idx=idx,
            max_back=3,
            max_forward=3,
            max_phrase_len=5,
            top_k=25,
        )

        print(f"\nClicked word {idx} ('{tokens[idx]}')")

        if one_word:
            print("\nOne-word alternatives:")
            for j, (tok, p, _ns) in enumerate(one_word[:20], 1):
                print(f"{j:>2}. p={p:.6g}  {tok}")
        else:
            print("\nOne-word alternatives: (none)")

        if phrase_alts:
            print("\nPhrase alternatives (may replace a span ending at this word):")
            for k, alt in enumerate(phrase_alts, 1):
                s = int(alt["start_idx"])
                e = int(alt["end_idx"])
                phr = " ".join(alt["phrase"]) if alt["phrase"] else "<delete>"
                p = float(alt["prob"])
                orig = " ".join(tokens[s:e+1])
                print(f"{k:>2}. p={p:.6g}  replace [{s}-{e}] '{orig}' -> '{phr}'")
        else:
            print("\nPhrase alternatives: (none)")

        pick = input("\nPick: 'w <num>' for one-word, 'p <num>' for phrase, Enter to cancel: ").strip()
        if pick == "":
            continue

        parts = pick.split()
        if len(parts) != 2 or parts[0] not in ("w", "p") or not parts[1].isdigit():
            print("Invalid input.")
            continue

        num = int(parts[1]) - 1

        if parts[0] == "w":
            if num < 0 or num >= len(one_word):
                print("Out of range.")
                continue
            tokens[idx] = one_word[num][0]
            print_sentence_with_indices(tokens)

        else:  # phrase
            if num < 0 or num >= len(phrase_alts):
                print("Out of range.")
                continue
            alt = phrase_alts[num]
            s = int(alt["start_idx"])
            e = int(alt["end_idx"])
            new_phrase = list(alt["phrase"])
            new_trace = list(alt["trace"])

            # Replace tokens + trace consistently
            tokens = tokens[:s] + new_phrase + tokens[e+1:]
            trace = trace[:s] + new_trace + trace[e+1:]

            print_sentence_with_indices(tokens)

    print("Bye.")


if __name__ == "__main__":
    main()