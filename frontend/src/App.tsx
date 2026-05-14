import { useEffect, useState } from "react";
import "./index.css";
import {
  applyOneWord,
  applyPhrase,
  fetchAlternatives,
  fetchOptions,
  fetchPresets,
  fetchTokenProbs,
  selectSentence,
} from "./api";
import type {
  AlternativesResponse,
  PhraseAlt,
  Preset,
  SentenceOption,
  TraceEntry,
} from "./types";

function formatProb(prob: number): string {
  if (prob >= 0.001) return prob.toFixed(6);
  return prob.toExponential(3);
}

function sentenceToDisplay(sentence: string): string {
  return sentence.replace(/\s*<\/s>\s*$/, "").trim();
}

function tokenClass(token: string, isClickable: boolean): string {
  let cls = "token";
  if (isClickable) cls += " token-clickable";
  if (token === "." || token === "," || token === "</s>") cls += " token-punct";
  return cls;
}

export default function App() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [sourceSentence, setSourceSentence] = useState<string>("");

  const [options, setOptions] = useState<SentenceOption[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  const [selectedFinalState, setSelectedFinalState] = useState<number | null>(null);
  const [selectedProb, setSelectedProb] = useState<number | null>(null);
  const [tokens, setTokens] = useState<string[] | null>(null);
  const [trace, setTrace] = useState<TraceEntry[] | null>(null);

  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [alts, setAlts] = useState<AlternativesResponse | null>(null);
  const [altsLoading, setAltsLoading] = useState(false);
  const [altsError, setAltsError] = useState<string | null>(null);

  const [includePhrases, setIncludePhrases] = useState(true);
  const [highlightThreshold, setHighlightThreshold] = useState(0.02);
  const [tokenProbs, setTokenProbs] = useState<number[]>([]);

  useEffect(() => {
    void loadPresets();
  }, []);

  async function loadPresets() {
    try {
      const data = await fetchPresets();
      setPresets(data);
    } catch (err) {
      setOptionsError(err instanceof Error ? err.message : "Failed to load presets");
    }
  }

  function resetTranslationState() {
    setTokens(null);
    setTrace(null);
    setAlts(null);
    setActiveIdx(null);
    setTokenProbs([]);
    setSelectedFinalState(null);
    setSelectedProb(null);
  }

  function resetToSourceSelection() {
    setSelectedPreset(null);
    setSourceSentence("");
    setOptions([]);
    setOptionsError(null);
    resetTranslationState();
  }

  async function handleChoosePreset(preset: Preset) {
    try {
      setSelectedPreset(preset.key);
      setSourceSentence(preset.source_sentence);
      setOptionsError(null);
      resetTranslationState();

      setLoadingOptions(true);
      const data = await fetchOptions(preset.key, 10);
      setOptions(data);
    } catch (err) {
      setOptionsError(err instanceof Error ? err.message : "Failed to load options");
    } finally {
      setLoadingOptions(false);
    }
  }

  async function refreshTokenProbs(currentTrace: TraceEntry[], preset: string) {
    try {
      const data = await fetchTokenProbs(preset, currentTrace);
      setTokenProbs(data.items.map((item) => item.prob));
    } catch (err) {
      console.error("Failed to load token probabilities", err);
      setTokenProbs([]);
    }
  }

  async function handleSelectOption(option: SentenceOption) {
    if (!selectedPreset) return;

    try {
      setAlts(null);
      setActiveIdx(null);
      setAltsError(null);

      const selected = await selectSentence(selectedPreset, option.final_state);
      setSelectedFinalState(selected.final_state);
      setSelectedProb(selected.prob);
      setTokens(selected.tokens);
      setTrace(selected.trace);
      await refreshTokenProbs(selected.trace, selectedPreset);
    } catch (err) {
      setOptionsError(err instanceof Error ? err.message : "Failed to select sentence");
    }
  }

  async function handleTokenClick(idx: number) {
    if (!tokens || !trace || !selectedPreset) return;
    if (idx < 0 || idx >= trace.length) return;

    try {
      setActiveIdx(idx);
      setAltsLoading(true);
      setAltsError(null);

      const data = await fetchAlternatives({
        preset: selectedPreset,
        tokens,
        trace,
        idx,
        includePhrases,
        maxBack: 3,
        maxForward: 3,
        maxPhraseLen: 5,
        topK: 25,
      });

      setAlts(data);
    } catch (err) {
      setAltsError(err instanceof Error ? err.message : "Failed to load alternatives");
    } finally {
      setAltsLoading(false);
    }
  }

  async function handleApplyOneWord(alt: { token: string; ilabel: number; nextstate: number }) {
    if (!tokens || !trace || activeIdx === null || !selectedPreset) return;

    try {
      const updated = await applyOneWord({
        tokens,
        trace,
        idx: activeIdx,
        token: alt.token,
        ilabel: alt.ilabel,
        nextstate: alt.nextstate,
      });
      setTokens(updated.tokens);
      setTrace(updated.trace);
      await refreshTokenProbs(updated.trace, selectedPreset);
      setAlts(null);
      setActiveIdx(null);
    } catch (err) {
      setAltsError(err instanceof Error ? err.message : "Failed to apply one-word replacement");
    }
  }

  async function handleApplyPhrase(alt: PhraseAlt) {
    if (!tokens || !trace || !selectedPreset) return;

    try {
      const updated = await applyPhrase({
        tokens,
        trace,
        startIdx: alt.start_idx,
        endIdx: alt.end_idx,
        phrase: alt.phrase,
        newTrace: alt.trace,
      });
      setTokens(updated.tokens);
      setTrace(updated.trace);
      await refreshTokenProbs(updated.trace, selectedPreset);
      setAlts(null);
      setActiveIdx(null);
    } catch (err) {
      setAltsError(err instanceof Error ? err.message : "Failed to apply phrase replacement");
    }
  }

  return (
      <div className="app-shell">
        <header className="topbar">
          <div>
            <h1>Confusion Network Translator</h1>
          </div>
        </header>

        <main className="layout">
          <section className="panel left-panel">
            <div className="panel-header">
              <h2>Source sentence</h2>
            </div>

            {!selectedPreset && (
                <div className="option-list">
                  {presets.map((preset) => (
                      <button
                          key={preset.key}
                          className="option-card"
                          onClick={() => void handleChoosePreset(preset)}
                      >
                        <div className="option-sentence">{preset.source_sentence}</div>
                        <div className="option-meta">preset: {preset.key}</div>
                      </button>
                  ))}
                </div>
            )}

            {selectedPreset && <div className="source-box">{sourceSentence}</div>}
          </section>

          <section className="panel right-panel">
            <div className="panel-header row-between">
              <h2>Candidate translations</h2>
              <label className="toggle">
                <input
                    type="checkbox"
                    checked={includePhrases}
                    onChange={(e) => setIncludePhrases(e.target.checked)}
                />
                <span>Show phrase alternatives</span>
              </label>
            </div>

            {loadingOptions && <div className="info-box">Loading options...</div>}
            {optionsError && <div className="error-box">{optionsError}</div>}

            {!loadingOptions && selectedPreset && !tokens && (
                <>
                  <div style={{ marginBottom: "12px" }}>
                    <button className="secondary-btn" onClick={resetToSourceSelection}>
                      Change source sentence
                    </button>
                  </div>

                  <div className="option-list">
                    {options.map((option) => (
                        <button
                            key={option.final_state}
                            className="option-card"
                            onClick={() => void handleSelectOption(option)}
                        >
                          <div className="option-sentence">
                            {sentenceToDisplay(option.sentence)}
                          </div>
                          <div className="option-meta">
                            <span>p ≈ {formatProb(option.prob)}</span>
                          </div>
                        </button>
                    ))}
                  </div>
                </>
            )}

            {tokens && trace && (
                <>
                  <div className="selected-card">
                    <div className="selected-header row-between">
                      <div>
                        <strong>Selected translation</strong>
                        {selectedFinalState !== null && (
                            <div className="selected-meta">
                              final: {selectedFinalState}
                              {selectedProb !== null && ` · p ≈ ${formatProb(selectedProb)}`}
                            </div>
                        )}
                      </div>

                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                            className="secondary-btn"
                            onClick={() => {
                              resetTranslationState();
                            }}
                        >
                          Back to options
                        </button>

                        <button
                            className="secondary-btn"
                            onClick={() => {
                              resetToSourceSelection();
                            }}
                        >
                          Change source sentence
                        </button>
                      </div>
                    </div>

                    <div className="threshold-box">
                      <label htmlFor="threshold-slider" className="threshold-label">
                        Highlight words with probability below:{" "}
                        <strong>{highlightThreshold.toFixed(3)}</strong>
                      </label>
                      <input
                          id="threshold-slider"
                          type="range"
                          min="0"
                          max="0.3"
                          step="0.001"
                          value={highlightThreshold}
                          onChange={(e) => setHighlightThreshold(Number(e.target.value))}
                          className="threshold-slider"
                      />
                    </div>

                    <div className="translation-box">
                      {tokens.map((token, idx) => {
                        if (token === "</s>") return null;

                        const isClickable = idx < trace.length;
                        const prob = tokenProbs[idx];
                        const isLowProb =
                            typeof prob === "number" &&
                            prob < highlightThreshold &&
                            token !== "." &&
                            token !== ",";

                        let classes =
                            idx === activeIdx
                                ? `${tokenClass(token, isClickable)} token-active`
                                : tokenClass(token, isClickable);

                        if (isLowProb) {
                          classes += " token-lowprob";
                        }

                        return (
                            <button
                                key={`${idx}-${token}`}
                                className={classes}
                                onClick={() => void handleTokenClick(idx)}
                                type="button"
                                title={typeof prob === "number" ? `p = ${formatProb(prob)}` : undefined}
                            >
                              {token}
                            </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="alts-panel">
                    <div className="alts-header">
                      <h3>Alternatives</h3>
                      {activeIdx !== null && tokens[activeIdx] && (
                          <span className="alts-subtitle">
                      clicked: <strong>{tokens[activeIdx]}</strong>
                    </span>
                      )}
                    </div>

                    {altsLoading && <div className="info-box">Loading alternatives...</div>}
                    {altsError && <div className="error-box">{altsError}</div>}

                    {!altsLoading && !alts && (
                        <div className="info-box">
                          Click a token in the selected translation to see alternatives.
                        </div>
                    )}

                    {!altsLoading && alts && (
                        <div className="alts-content">
                          <div className="alt-group">
                            <h4>One-word alternatives</h4>
                            {alts.one_word.length === 0 ? (
                                <div className="muted">No one-word alternatives.</div>
                            ) : (
                                <div className="alt-grid">
                                  {alts.one_word.map((alt, i) => (
                                      <button
                                          key={`${alt.token}-${i}`}
                                          className="alt-item alt-item-compact alt-item-inline"
                                          onClick={() => void handleApplyOneWord(alt)}
                                      >
                                        <span className="alt-main">{alt.token}</span>
                                        <span className="alt-prob">p = {formatProb(alt.prob)}</span>
                                      </button>
                                  ))}
                                </div>
                            )}
                          </div>

                          {includePhrases && (
                              <div className="alt-group">
                                <h4>Phrase alternatives</h4>
                                {alts.phrases.length === 0 ? (
                                    <div className="muted">No phrase alternatives.</div>
                                ) : (
                                    <div className="alt-grid">
                                      {alts.phrases.map((alt, i) => {
                                        const replacement =
                                            alt.phrase.length > 0 ? alt.phrase.join(" ") : "<delete>";

                                        const original =
                                            tokens
                                                .slice(alt.start_idx, alt.end_idx + 1)
                                                .filter((t) => t !== "</s>")
                                                .join(" ");

                                        return (
                                            <button
                                                key={`${alt.start_idx}-${alt.end_idx}-${i}`}
                                                className="alt-item alt-item-compact phrase-item"
                                                onClick={() => void handleApplyPhrase(alt)}
                                            >
                                              <div className="alt-topline">
                                                <span className="alt-main">{replacement}</span>
                                                <span className="alt-prob">p = {formatProb(alt.prob)}</span>
                                              </div>
                                              <span className="alt-replace">
                                                [{alt.start_idx}-{alt.end_idx}] “{original}”
                                              </span>
                                            </button>
                                        );
                                      })}
                                    </div>
                                )}
                              </div>
                          )}
                        </div>
                    )}
                  </div>
                </>
            )}

            {!loadingOptions && selectedPreset && !tokens && options.length === 0 && (
                <div className="info-box">No sentence options returned by backend.</div>
            )}
          </section>
        </main>
      </div>
  );
}