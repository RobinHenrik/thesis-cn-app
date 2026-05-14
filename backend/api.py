from functools import lru_cache
from typing import List, Literal, Union, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pathlib import Path

from cn_io import load_fst, load_sym
from cn_decode import (
    list_sentence_options_by_final,
    best_path_trace_to_final,
    alternatives_for_word,
    alternatives_for_span,
    make_cost_fst,
)

BASE_DIR = Path(__file__).resolve().parent

PRESETS: Dict[str, Dict[str, str]] = {
    "1": {
        "fst": str(BASE_DIR / "fst_clean_i0.fst"),
        "syms": str(BASE_DIR / "syms_i0.txt"),
        "source_sentence": "Kaks sõdurit said vigastada ja viidi Tshinvali haiglasse ravile.",
    },
    "2": {
        "fst": str(BASE_DIR / "fst_clean_i1.fst"),
        "syms": str(BASE_DIR / "syms_i1.txt"),
        "source_sentence": "See traditsioon sai alguse 14. sajandil ja jätkus kuni 1660. aastani.",
    },
    "3": {
        "fst": str(BASE_DIR / "fst_clean_i3.fst"),
        "syms": str(BASE_DIR / "syms_i3.txt"),
        "source_sentence": "Eksperdid on tuvastanud 65 inimest, kes hukkusid Malaisia lennufirma lennuõnnetuses.",
    },
    "4": {
        "fst": str(BASE_DIR / "fst_clean_testing.fst"),
        "syms": str(BASE_DIR / "syms_testing.txt"),
        "source_sentence": "Ohutusnõuded olid siis tänapäeva mõistes allpool igasugust arvestust.",
    },
}


class PresetModel(BaseModel):
    key: str
    source_sentence: str


class TraceEntryModel(BaseModel):
    cn_state: int
    nextstate: int
    ilabel: int
    token: str


class SentenceOptionModel(BaseModel):
    sentence: str
    prob: float
    final_state: int


class SelectRequest(BaseModel):
    preset: str
    final_state: int


class SelectResponse(BaseModel):
    preset: str
    final_state: int
    prob: float
    tokens: List[str]
    trace: List[TraceEntryModel]


class OneWordAltModel(BaseModel):
    token: str
    prob: float
    ilabel: int
    nextstate: int


class PhraseAltModel(BaseModel):
    start_idx: int
    end_idx: int
    phrase: List[str]
    prob: float
    trace: List[TraceEntryModel]


class AlternativesRequest(BaseModel):
    preset: str
    tokens: List[str]
    trace: List[TraceEntryModel]
    idx: int
    include_phrases: bool = True
    max_back: int = 3
    max_forward: int = 3
    max_phrase_len: int = 5
    top_k: int = 25


class AlternativesResponse(BaseModel):
    idx: int
    clicked_token: str
    one_word: List[OneWordAltModel]
    phrases: List[PhraseAltModel]


class ApplyOneWordRequest(BaseModel):
    kind: Literal["one_word"]
    tokens: List[str]
    trace: List[TraceEntryModel]
    idx: int
    token: str
    ilabel: int
    nextstate: int


class ApplyPhraseRequest(BaseModel):
    kind: Literal["phrase"]
    tokens: List[str]
    trace: List[TraceEntryModel]
    start_idx: int
    end_idx: int
    phrase: List[str]
    new_trace: List[TraceEntryModel]


ApplyRequest = Union[ApplyOneWordRequest, ApplyPhraseRequest]


class ApplyResponse(BaseModel):
    tokens: List[str]
    trace: List[TraceEntryModel]


class TokenProbRequest(BaseModel):
    preset: str
    trace: List[TraceEntryModel]


class TokenProbModel(BaseModel):
    idx: int
    token: str
    prob: float


class TokenProbResponse(BaseModel):
    items: List[TokenProbModel]


app = FastAPI(title="Confusion Network Translation API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_preset_config(preset: str) -> Dict[str, str]:
    if preset not in PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {preset}")
    return PRESETS[preset]


@lru_cache(maxsize=8)
def get_resources_for_preset(preset: str):
    cfg = get_preset_config(preset)
    sym = load_sym(cfg["syms"])
    prob_fst = load_fst(cfg["fst"])
    cost_fst = make_cost_fst(prob_fst)
    return sym, prob_fst, cost_fst


def _selected_token_prob(prob_fst, trace_entry: TraceEntryModel) -> float:
    s = trace_entry.cn_state
    ilabel = trace_entry.ilabel
    nextstate = trace_entry.nextstate

    for a in prob_fst.arcs(s):
        if a.ilabel == ilabel and a.nextstate == nextstate:
            return float(a.weight)
    return 0.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/presets", response_model=List[PresetModel])
def get_presets():
    return [
        PresetModel(key=key, source_sentence=value["source_sentence"])
        for key, value in PRESETS.items()
    ]


@app.get("/options", response_model=List[SentenceOptionModel])
def get_options(preset: str, top_n: int = 10):
    sym, prob_fst, _cost_fst = get_resources_for_preset(preset)
    options, _ = list_sentence_options_by_final(prob_fst, sym, top_n=top_n)

    return [
        SentenceOptionModel(sentence=sent, prob=prob, final_state=final_state)
        for sent, prob, final_state in options
    ]


@app.post("/select", response_model=SelectResponse)
def select_sentence(req: SelectRequest):
    sym, _prob_fst, cost_fst = get_resources_for_preset(req.preset)

    tokens, prob, trace = best_path_trace_to_final(cost_fst, sym, req.final_state)
    if not tokens:
        raise HTTPException(status_code=404, detail="Could not decode sentence for this final state.")

    return SelectResponse(
        preset=req.preset,
        final_state=req.final_state,
        prob=prob,
        tokens=tokens,
        trace=[TraceEntryModel(**t) for t in trace],
    )


@app.post("/alternatives", response_model=AlternativesResponse)
def get_alternatives(req: AlternativesRequest):
    sym, prob_fst, _cost_fst = get_resources_for_preset(req.preset)

    if req.idx < 0 or req.idx >= len(req.trace):
        raise HTTPException(status_code=400, detail="Index out of range.")

    trace = [t.model_dump() for t in req.trace]

    one_word_raw = alternatives_for_word(
        prob_fst=prob_fst,
        sym=sym,
        trace_entry=trace[req.idx],
        require_same_nextstate=True,
    )

    one_word = [
        OneWordAltModel(token=tok, prob=prob, ilabel=ilabel, nextstate=nextstate)
        for tok, prob, ilabel, nextstate in one_word_raw
    ]

    phrases: List[PhraseAltModel] = []
    if req.include_phrases:
        phrase_raw = alternatives_for_span(
            prob_fst=prob_fst,
            sym=sym,
            tokens=req.tokens,
            trace=trace,
            idx=req.idx,
            max_back=req.max_back,
            max_forward=req.max_forward,
            max_phrase_len=req.max_phrase_len,
            top_k=req.top_k,
        )

        phrases = [
            PhraseAltModel(
                start_idx=int(alt["start_idx"]),
                end_idx=int(alt["end_idx"]),
                phrase=list(alt["phrase"]),
                prob=float(alt["prob"]),
                trace=[TraceEntryModel(**t) for t in alt["trace"]],
            )
            for alt in phrase_raw
        ]

    return AlternativesResponse(
        idx=req.idx,
        clicked_token=req.tokens[req.idx],
        one_word=one_word,
        phrases=phrases,
    )


@app.post("/apply", response_model=ApplyResponse)
def apply_replacement(req: ApplyRequest):
    if req.kind == "one_word":
        if req.idx < 0 or req.idx >= len(req.tokens):
            raise HTTPException(status_code=400, detail="Index out of range.")

        new_tokens = list(req.tokens)
        new_trace = list(req.trace)

        new_tokens[req.idx] = req.token
        new_trace[req.idx] = TraceEntryModel(
            cn_state=req.trace[req.idx].cn_state,
            nextstate=req.nextstate,
            ilabel=req.ilabel,
            token=req.token,
        )

        return ApplyResponse(tokens=new_tokens, trace=new_trace)

    if req.kind == "phrase":
        if req.start_idx < 0 or req.end_idx >= len(req.tokens) or req.start_idx > req.end_idx:
            raise HTTPException(status_code=400, detail="Invalid span.")

        new_tokens = req.tokens[:req.start_idx] + req.phrase + req.tokens[req.end_idx + 1 :]
        new_trace = req.trace[:req.start_idx] + req.new_trace + req.trace[req.end_idx + 1 :]

        return ApplyResponse(tokens=new_tokens, trace=new_trace)

    raise HTTPException(status_code=400, detail="Unknown replacement type.")


@app.post("/token-probs", response_model=TokenProbResponse)
def get_token_probs(req: TokenProbRequest):
    _sym, prob_fst, _cost_fst = get_resources_for_preset(req.preset)

    items = []
    for idx, t in enumerate(req.trace):
        prob = _selected_token_prob(prob_fst, t)
        items.append(TokenProbModel(idx=idx, token=t.token, prob=prob))

    return TokenProbResponse(items=items)