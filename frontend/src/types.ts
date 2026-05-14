export type Preset = {
    key: string;
    source_sentence: string;
};

export type TraceEntry = {
    cn_state: number;
    nextstate: number;
    ilabel: number;
    token: string;
};

export type SentenceOption = {
    sentence: string;
    prob: number;
    final_state: number;
};

export type SelectResponse = {
    preset: string;
    final_state: number;
    prob: number;
    tokens: string[];
    trace: TraceEntry[];
};

export type OneWordAlt = {
    token: string;
    prob: number;
    ilabel: number;
    nextstate: number;
};

export type PhraseAlt = {
    start_idx: number;
    end_idx: number;
    phrase: string[];
    prob: number;
    trace: TraceEntry[];
};

export type AlternativesResponse = {
    idx: number;
    clicked_token: string;
    one_word: OneWordAlt[];
    phrases: PhraseAlt[];
};

export type ApplyResponse = {
    tokens: string[];
    trace: TraceEntry[];
};

export type TokenProb = {
    idx: number;
    token: string;
    prob: number;
};

export type TokenProbResponse = {
    items: TokenProb[];
};