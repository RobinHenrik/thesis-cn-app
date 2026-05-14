import type {
    AlternativesResponse,
    ApplyResponse,
    Preset,
    SelectResponse,
    SentenceOption,
    TraceEntry,
    TokenProbResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed with status ${res.status}`);
    }
    return res.json() as Promise<T>;
}

export async function fetchPresets(): Promise<Preset[]> {
    const res = await fetch(`${API_BASE}/presets`);
    return handleResponse<Preset[]>(res);
}

export async function fetchOptions(preset: string, topN = 10): Promise<SentenceOption[]> {
    const res = await fetch(`${API_BASE}/options?preset=${encodeURIComponent(preset)}&top_n=${topN}`);
    return handleResponse<SentenceOption[]>(res);
}

export async function selectSentence(preset: string, finalState: number): Promise<SelectResponse> {
    const res = await fetch(`${API_BASE}/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset, final_state: finalState }),
    });
    return handleResponse<SelectResponse>(res);
}

export async function fetchAlternatives(params: {
    preset: string;
    tokens: string[];
    trace: TraceEntry[];
    idx: number;
    includePhrases: boolean;
    maxBack: number;
    maxForward: number;
    maxPhraseLen: number;
    topK: number;
}): Promise<AlternativesResponse> {
    const res = await fetch(`${API_BASE}/alternatives`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            preset: params.preset,
            tokens: params.tokens,
            trace: params.trace,
            idx: params.idx,
            include_phrases: params.includePhrases,
            max_back: params.maxBack,
            max_forward: params.maxForward,
            max_phrase_len: params.maxPhraseLen,
            top_k: params.topK,
        }),
    });
    return handleResponse<AlternativesResponse>(res);
}

export async function applyOneWord(params: {
    tokens: string[];
    trace: TraceEntry[];
    idx: number;
    token: string;
    ilabel: number;
    nextstate: number;
}): Promise<ApplyResponse> {
    const res = await fetch(`${API_BASE}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            kind: "one_word",
            tokens: params.tokens,
            trace: params.trace,
            idx: params.idx,
            token: params.token,
            ilabel: params.ilabel,
            nextstate: params.nextstate,
        }),
    });
    return handleResponse<ApplyResponse>(res);
}

export async function applyPhrase(params: {
    tokens: string[];
    trace: TraceEntry[];
    startIdx: number;
    endIdx: number;
    phrase: string[];
    newTrace: TraceEntry[];
}): Promise<ApplyResponse> {
    const res = await fetch(`${API_BASE}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            kind: "phrase",
            tokens: params.tokens,
            trace: params.trace,
            start_idx: params.startIdx,
            end_idx: params.endIdx,
            phrase: params.phrase,
            new_trace: params.newTrace,
        }),
    });
    return handleResponse<ApplyResponse>(res);
}

export async function fetchTokenProbs(preset: string, trace: TraceEntry[]): Promise<TokenProbResponse> {
    const res = await fetch(`${API_BASE}/token-probs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset, trace }),
    });
    return handleResponse<TokenProbResponse>(res);
}