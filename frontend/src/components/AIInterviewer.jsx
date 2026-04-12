import React, { useState, useRef, useCallback } from 'react';
import {
  UploadCloud, FileText, Mic, MicOff, ChevronRight,
  CheckCircle, XCircle, TrendingUp, RotateCcw, Send,
  Award, Brain, MessageSquare, Target
} from 'lucide-react';

// ─── Constants ───────────────────────────────────────────────────────────────

const TOTAL_QUESTIONS = 5;

const SCORE_THRESHOLDS = {
  high: 75,
  mid: 50,
};

const getScoreColor = (score) => {
  if (score >= SCORE_THRESHOLDS.high) return 'var(--success)';
  if (score >= SCORE_THRESHOLDS.mid) return 'var(--warning)';
  return 'var(--error)';
};

const getScoreLabel = (score) => {
  if (score >= SCORE_THRESHOLDS.high) return 'Excellent';
  if (score >= SCORE_THRESHOLDS.mid) return 'Good';
  return 'Needs Improvement';
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function ScoreCircle({ score, size = 'lg' }) {
  const color = getScoreColor(score);
  const isLarge = size === 'lg';
  return (
    <div
      className="score-circle"
      style={{
        '--score': score,
        '--score-color': color,
        width: isLarge ? '110px' : '72px',
        height: isLarge ? '110px' : '72px',
      }}
    >
      <span className="score-text" style={{ color, fontSize: isLarge ? '1.7rem' : '1.1rem' }}>
        {Math.round(score)}%
      </span>
    </div>
  );
}

function FeedbackCard({ evaluation, questionText }) {
  if (!evaluation) return null;
  const color = getScoreColor(evaluation.score);
  return (
    <div className="glass-panel" style={{ padding: '1.25rem', marginTop: '1rem', borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
        <ScoreCircle score={evaluation.score} size="sm" />
        <div>
          <div style={{ color, fontWeight: 700, fontSize: '1rem' }}>
            {getScoreLabel(evaluation.score)}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Answer Score</div>
        </div>
      </div>

      {evaluation.feedback && (
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.6, marginBottom: '0.75rem' }}>
          {evaluation.feedback}
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        {evaluation.strengths?.length > 0 && (
          <div>
            <div className="field-label success" style={{ marginBottom: '0.4rem' }}>
              <CheckCircle size={11} /> Strengths
            </div>
            {evaluation.strengths.map((s, i) => (
              <div key={i} className="tag strength" style={{ marginBottom: '0.25rem', display: 'block' }}>
                {s}
              </div>
            ))}
          </div>
        )}
        {evaluation.improvements?.length > 0 && (
          <div>
            <div className="field-label error" style={{ marginBottom: '0.4rem' }}>
              <XCircle size={11} /> To Improve
            </div>
            {evaluation.improvements.map((s, i) => (
              <div key={i} className="tag missing" style={{ marginBottom: '0.25rem', display: 'block' }}>
                {s}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

function AIInterviewer({ token }) {
  // Stage: 'upload' | 'interview' | 'report'
  const [stage, setStage] = useState('upload');

  // Upload stage
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const fileInputRef = useRef(null);

  // Interview stage
  const [resumeData, setResumeData] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [answer, setAnswer] = useState('');
  const [evaluations, setEvaluations] = useState([]); // [{question, answer, score, ...}]
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [currentEval, setCurrentEval] = useState(null); // evaluation for current Q
  const [answerSubmitted, setAnswerSubmitted] = useState(false);

  // Voice
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);
  const voiceSupported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  // Report stage
  const [report, setReport] = useState(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // ── File Handling ─────────────────────────────────────────────────────────

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) { setFile(f); setStartError(''); }
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) { setFile(f); setStartError(''); }
  };

  // ── Start Interview ───────────────────────────────────────────────────────

  const handleStartInterview = async () => {
    if (!file) { setStartError('Please upload a PDF resume first.'); return; }
    setIsStarting(true);
    setStartError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/interview/start', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start interview');
      }
      const data = await res.json();
      setResumeData(data.resume_data);
      setQuestions(data.questions);
      setCurrentQIdx(0);
      setAnswer('');
      setEvaluations([]);
      setCurrentEval(null);
      setAnswerSubmitted(false);
      setStage('interview');
    } catch (err) {
      setStartError(err.message);
    } finally {
      setIsStarting(false);
    }
  };

  // ── Voice Input ───────────────────────────────────────────────────────────

  const startListening = useCallback(() => {
    if (!voiceSupported) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setAnswer((prev) => prev ? prev + ' ' + transcript : transcript);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [voiceSupported]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  // ── Submit Answer ─────────────────────────────────────────────────────────

  const handleSubmitAnswer = async () => {
    if (!answer.trim()) return;
    setIsEvaluating(true);
    setCurrentEval(null);

    const question = questions[currentQIdx];
    try {
      const res = await fetch('http://localhost:8000/api/interview/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question, answer }),
      });
      if (!res.ok) throw new Error('Evaluation failed');
      const evalData = await res.json();

      setCurrentEval(evalData);
      setEvaluations((prev) => [
        ...prev,
        { question, answer, ...evalData },
      ]);
      setAnswerSubmitted(true);
    } catch (err) {
      setCurrentEval({
        score: 0,
        feedback: 'Could not evaluate answer. Saved for final report.',
        strengths: [],
        improvements: [],
        suggestions: [],
      });
      setEvaluations((prev) => [
        ...prev,
        { question, answer, score: 0 },
      ]);
      setAnswerSubmitted(true);
    } finally {
      setIsEvaluating(false);
    }
  };

  // ── Next Question / Finish ────────────────────────────────────────────────

  const handleNext = async () => {
    const nextIdx = currentQIdx + 1;
    if (nextIdx >= TOTAL_QUESTIONS) {
      // Generate final report
      await generateReport();
    } else {
      setCurrentQIdx(nextIdx);
      setAnswer('');
      setCurrentEval(null);
      setAnswerSubmitted(false);
    }
  };

  const generateReport = async () => {
    setIsGeneratingReport(true);
    setStage('report');

    try {
      const res = await fetch('http://localhost:8000/api/interview/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ qa_pairs: evaluations }),
      });
      if (!res.ok) throw new Error('Report generation failed');
      const reportData = await res.json();
      setReport(reportData);
    } catch (err) {
      // Fallback: compute from evaluations
      const scores = evaluations.map((e) => e.score || 0);
      const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
      setReport({
        overall_score: avg,
        technical_skills: avg,
        communication: Math.round(avg * 0.9),
        problem_solving: Math.round(avg * 0.95),
        summary: 'Interview completed. See per-question scores for detailed feedback.',
        strengths: ['Completed all interview questions'],
        areas_for_improvement: ['Review your answers for more specific examples'],
      });
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // ── Reset ─────────────────────────────────────────────────────────────────

  const handleReset = () => {
    setStage('upload');
    setFile(null);
    setStartError('');
    setResumeData(null);
    setQuestions([]);
    setCurrentQIdx(0);
    setAnswer('');
    setEvaluations([]);
    setCurrentEval(null);
    setAnswerSubmitted(false);
    setReport(null);
  };

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  // ── Stage 1: Upload ───────────────────────────────────────────────────────
  if (stage === 'upload') {
    return (
      <div className="parser-layout">
        {/* Left: Upload panel */}
        <div className="glass-panel parser-input-panel">
          <div className="panel-header">
            <Mic size={19} style={{ color: 'var(--accent)' }} />
            <h2>AI Interview</h2>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.25rem', lineHeight: 1.6 }}>
            Upload your resume and the AI will generate <strong>5 personalized interview questions</strong> based on your skills, experience, and projects.
          </p>

          {/* Drop Zone */}
          <div
            id="interview-drop-zone"
            className={`file-drop-area${isDragging ? ' dragging' : ''}${file ? ' has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              id="interview-file-input"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              accept=".pdf"
            />
            <UploadCloud className="drop-icon" size={38} />
            {file ? (
              <div>
                <p className="drop-filename">📄 {file.name}</p>
                <p className="drop-sub">Click or drag to replace</p>
              </div>
            ) : (
              <div>
                <p className="drop-title">Drop your resume here</p>
                <p className="drop-sub">PDF only</p>
              </div>
            )}
          </div>

          {startError && <div className="error-message" style={{ marginTop: '0.75rem' }}>{startError}</div>}

          <button
            id="start-interview-btn"
            className="btn-primary"
            style={{ marginTop: '1.25rem' }}
            onClick={handleStartInterview}
            disabled={isStarting || !file}
          >
            {isStarting ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <div className="spinner" /> Generating Questions…
              </span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <Mic size={16} /> Start Interview
              </span>
            )}
          </button>
        </div>

        {/* Right: Info panel */}
        <div className="parser-results-panel">
          <div className="glass-panel empty-state">
            <div className="empty-icon"><Mic size={44} /></div>
            <h3>How It Works</h3>
            <div style={{ textAlign: 'left', width: '100%', maxWidth: '340px', margin: '0 auto' }}>
              {[
                { icon: '📄', text: 'Upload your PDF resume' },
                { icon: '🧠', text: 'AI reads your skills, experience & projects' },
                { icon: '❓', text: '5 personalized questions are generated' },
                { icon: '🎤', text: 'Answer by typing or speaking (mic button)' },
                { icon: '📊', text: 'Get scored feedback after each answer' },
                { icon: '🏆', text: 'Receive a full evaluation report at the end' },
              ].map(({ icon, text }, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.65rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  <span style={{ fontSize: '1.1rem' }}>{icon}</span>
                  <span>{text}</span>
                </div>
              ))}
            </div>
            {voiceSupported && (
              <div style={{ marginTop: '1rem', padding: '0.6rem 1rem', background: 'var(--accent-muted, rgba(99,102,241,0.1))', borderRadius: '8px', color: 'var(--accent)', fontSize: '0.8rem' }}>
                🎤 Voice input supported in your browser
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── Stage 2: Interview ────────────────────────────────────────────────────
  if (stage === 'interview') {
    const currentQuestion = questions[currentQIdx];
    const progress = ((currentQIdx) / TOTAL_QUESTIONS) * 100;

    return (
      <div className="parser-layout">
        {/* Left: Question & Answer */}
        <div className="glass-panel parser-input-panel">
          {/* Progress */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Question {currentQIdx + 1} of {TOTAL_QUESTIONS}
              </span>
              <span style={{ color: 'var(--accent)', fontSize: '0.8rem', fontWeight: 600 }}>
                {Math.round(progress)}% complete
              </span>
            </div>
            <div style={{ height: '4px', background: 'var(--border)', borderRadius: '99px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${progress}%`,
                background: 'var(--accent)',
                borderRadius: '99px',
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>

          {/* Question Card */}
          <div style={{
            background: 'var(--bg-card, rgba(255,255,255,0.03))',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '1.1rem 1.25rem',
            marginBottom: '1.25rem',
          }}>
            <div style={{ color: 'var(--accent)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Interview Question
            </div>
            <p style={{ color: 'var(--text-primary)', fontSize: '0.95rem', lineHeight: 1.65, margin: 0 }}>
              {currentQuestion}
            </p>
          </div>

          {/* Answer Input */}
          <div className="form-group">
            <label htmlFor="interview-answer-input" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <MessageSquare size={13} /> Your Answer
              </span>
              {voiceSupported && !answerSubmitted && (
                <button
                  id="voice-btn"
                  onClick={isListening ? stopListening : startListening}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.35rem',
                    background: isListening ? 'var(--error)' : 'var(--accent)',
                    color: '#fff', border: 'none', borderRadius: '6px',
                    padding: '0.3rem 0.65rem', fontSize: '0.75rem', cursor: 'pointer',
                    fontWeight: 600, transition: 'all 0.2s',
                  }}
                >
                  {isListening ? <><MicOff size={13} /> Stop</> : <><Mic size={13} /> Speak</>}
                </button>
              )}
            </label>
            <textarea
              id="interview-answer-input"
              rows={7}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder={isListening ? '🎤 Listening… speak your answer…' : 'Type your answer here, or click Speak to use voice input…'}
              disabled={answerSubmitted || isListening}
              style={{ opacity: answerSubmitted ? 0.7 : 1 }}
            />
          </div>

          {!answerSubmitted ? (
            <button
              id="submit-answer-btn"
              className="btn-primary"
              onClick={handleSubmitAnswer}
              disabled={isEvaluating || !answer.trim()}
            >
              {isEvaluating ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                  <div className="spinner" /> Evaluating…
                </span>
              ) : (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                  <Send size={15} /> Submit Answer
                </span>
              )}
            </button>
          ) : (
            <button
              id="next-question-btn"
              className="btn-primary"
              onClick={handleNext}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}
            >
              {currentQIdx + 1 >= TOTAL_QUESTIONS
                ? <><Award size={15} /> Finish & See Report</>
                : <><ChevronRight size={15} /> Next Question</>
              }
            </button>
          )}
        </div>

        {/* Right: Feedback / Previous answers */}
        <div className="parser-results-panel">
          {/* Feedback for current answer */}
          {isEvaluating && (
            <div className="glass-panel loading-panel">
              <h3 className="loading-title">AI is evaluating…</h3>
              <p className="loading-sub">Analyzing your answer with Gemini</p>
            </div>
          )}

          {!isEvaluating && currentEval && (
            <FeedbackCard evaluation={currentEval} questionText={currentQuestion} />
          )}

          {/* Previous question scores */}
          {evaluations.length > 1 && (
            <div className="glass-panel" style={{ padding: '1rem', marginTop: '1rem' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
                Previous Scores
              </div>
              {evaluations.slice(0, -1).map((ev, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    Q{i + 1}
                  </div>
                  <div style={{ color: getScoreColor(ev.score), fontWeight: 700, fontSize: '0.9rem', minWidth: '40px', textAlign: 'right' }}>
                    {Math.round(ev.score)}%
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isEvaluating && !currentEval && evaluations.length === 0 && (
            <div className="glass-panel empty-state">
              <div className="empty-icon"><Brain size={44} /></div>
              <h3>Ready for Your Answer</h3>
              <p>Type or speak your answer, then click Submit to get AI feedback.</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Stage 3: Final Report ─────────────────────────────────────────────────
  if (stage === 'report') {
    return (
      <div className="parser-layout">
        {/* Left: Overall score + sub-scores */}
        <div className="glass-panel parser-input-panel">
          <div className="panel-header">
            <Award size={19} style={{ color: 'var(--accent)' }} />
            <h2>Interview Report</h2>
          </div>

          {isGeneratingReport || !report ? (
            <div style={{ textAlign: 'center', padding: '2rem 0' }}>
              <div className="spinner" style={{ margin: '0 auto', width: '36px', height: '36px' }} />
              <p style={{ color: 'var(--text-secondary)', marginTop: '1rem', fontSize: '0.875rem' }}>
                Generating your final evaluation…
              </p>
            </div>
          ) : (
            <>
              {/* Overall score */}
              <div className="score-section" style={{ marginBottom: '1.5rem' }}>
                <ScoreCircle score={report.overall_score} />
                <div>
                  <div className="score-label" style={{ color: getScoreColor(report.overall_score) }}>
                    {getScoreLabel(report.overall_score)}
                  </div>
                  <div className="score-sub">Overall Interview Score</div>
                </div>
              </div>

              <hr className="divider" />

              {/* Sub-scores */}
              <div style={{ marginBottom: '1.25rem' }}>
                {[
                  { label: 'Technical Skills', icon: Brain, value: report.technical_skills },
                  { label: 'Communication', icon: MessageSquare, value: report.communication },
                  { label: 'Problem Solving', icon: Target, value: report.problem_solving },
                ].map(({ label, icon: Icon, value }) => (
                  <div key={label} style={{ marginBottom: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Icon size={13} /> {label}
                      </span>
                      <span style={{ color: getScoreColor(value), fontWeight: 700, fontSize: '0.9rem' }}>
                        {value}%
                      </span>
                    </div>
                    <div style={{ height: '5px', background: 'var(--border)', borderRadius: '99px', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: `${value}%`,
                        background: getScoreColor(value),
                        borderRadius: '99px', transition: 'width 0.8s ease',
                      }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Summary */}
              {report.summary && (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.65, background: 'var(--bg-card, rgba(255,255,255,0.03))', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  {report.summary}
                </p>
              )}

              <button
                id="new-interview-btn"
                className="btn-primary"
                style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}
                onClick={handleReset}
              >
                <RotateCcw size={15} /> Start New Interview
              </button>
            </>
          )}
        </div>

        {/* Right: Strengths + Improvements + Per-Q scores */}
        <div className="parser-results-panel">
          {report && !isGeneratingReport && (
            <>
              {/* Strengths */}
              <div className="result-card glass-panel">
                <div className="result-field full-width">
                  <span className="field-label success">
                    <CheckCircle size={13} /> Key Strengths
                  </span>
                  <div className="tag-list" style={{ marginTop: '0.5rem' }}>
                    {report.strengths?.length > 0
                      ? report.strengths.map((s, i) => <span key={i} className="tag strength">{s}</span>)
                      : <span className="empty-label">None identified</span>}
                  </div>
                </div>

                <hr className="divider" />

                <div className="result-field full-width">
                  <span className="field-label error">
                    <XCircle size={13} /> Areas to Improve
                  </span>
                  <div className="tag-list" style={{ marginTop: '0.5rem' }}>
                    {report.areas_for_improvement?.length > 0
                      ? report.areas_for_improvement.map((s, i) => <span key={i} className="tag missing">{s}</span>)
                      : <span className="empty-label">Nothing major — great interview!</span>}
                  </div>
                </div>

                <hr className="divider" />

                {/* Per-question scores */}
                <div className="result-field full-width">
                  <span className="field-label">
                    <TrendingUp size={13} /> Question Breakdown
                  </span>
                  <div style={{ marginTop: '0.75rem' }}>
                    {evaluations.map((ev, i) => (
                      <div key={i} style={{ marginBottom: '0.85rem', padding: '0.75rem', background: 'var(--bg-card, rgba(255,255,255,0.02))', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.4rem' }}>
                          <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.4, flex: 1 }}>
                            <strong style={{ color: 'var(--accent)' }}>Q{i + 1}:</strong> {ev.question}
                          </span>
                          <span style={{ color: getScoreColor(ev.score), fontWeight: 700, fontSize: '1rem', whiteSpace: 'nowrap' }}>
                            {Math.round(ev.score)}%
                          </span>
                        </div>
                        {ev.feedback && (
                          <p style={{ color: 'var(--text-muted)', fontSize: '0.76rem', margin: 0, lineHeight: 1.5 }}>
                            {ev.feedback}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return null;
}

export default AIInterviewer;
