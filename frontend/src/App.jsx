import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Lock, UserPlus, LogOut, FileText, Phone, ChevronDown, ChevronUp, 
  CheckCircle, MessageSquare, Mic, Volume2, Briefcase, ExternalLink, Home, User,
  Sun, Moon
} from 'lucide-react';

function App() {
  // Theme State: 'dark' | 'light'
  const [theme, setTheme] = useState('dark');

  // Navigation & Page State: 'landing' | 'login' | 'signup' | 'dashboard' | 'interview'
  const [currentPage, setCurrentPage] = useState('landing');
  
  // User Authentication State
  const [user, setUser] = useState(null);
  
  // Login Form State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginSuccess, setLoginSuccess] = useState('');

  // Signup Form State
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupError, setSignupError] = useState('');

  // Dashboard Data State
  const [sessions, setSessions] = useState([]);
  const [expandedSession, setExpandedSession] = useState(null);

  // Setup Form State
  const [resumeFile, setResumeFile] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [aptQ, setAptQ] = useState(1);
  const [techQ, setTechQ] = useState(1);
  const [commQ, setCommQ] = useState(1);
  const [resumeQ, setResumeQ] = useState(2);
  const [setupStatus, setSetupStatus] = useState('');
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [targetRole, setTargetRole] = useState('Software Engineer');
  const [candidateDomain, setCandidateDomain] = useState('Tech');
  const [selectedAptitudes, setSelectedAptitudes] = useState(['numerical', 'quantitative', 'logical', 'verbal', 'abstract']);


  // Interview Active Session State
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentRound, setCurrentRound] = useState(1);
  const [totalRounds, setTotalRounds] = useState(0);
  const [textAnswer, setTextAnswer] = useState('');
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [revealedAccordions, setRevealedAccordions] = useState({});
  const [interviewComplete, setInterviewComplete] = useState(false);

  // Audio Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  const [agentStatus, setAgentStatus] = useState('');
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);
  const statusPollRef = useRef(null);

  // Base API URL
  const API_BASE = '';

  useEffect(() => {
    // Apply Theme Class to Document Body
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [theme]);

  useEffect(() => {
    // If user changes, load their dashboard history
    if (user && user.email) {
      loadDashboard();
    }
  }, [user]);

  useEffect(() => {
    // Scroll chat to bottom on new messages
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Poll agent status while answer is being submitted
  useEffect(() => {
    if (isSubmittingAnswer && sessionId) {
      statusPollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/interview/status/${sessionId}`);
          const data = await res.json();
          if (data.status && data.status !== 'idle') {
            setAgentStatus(data.status);
          } else {
            setAgentStatus('');
          }
        } catch {}
      }, 600);
    } else {
      clearInterval(statusPollRef.current);
      setAgentStatus('');
    }
    return () => clearInterval(statusPollRef.current);
  }, [isSubmittingAnswer, sessionId]);

  const loadDashboard = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/dashboard?email=${encodeURIComponent(user.email)}`);
      const data = await response.json();
      setSessions(data || []);
    } catch (e) {
      console.error('Failed to load dashboard data', e);
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginSuccess('');
    if (!loginEmail || !loginPassword) {
      setLoginError('Please enter email and password.');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail, password: loginPassword })
      });
      const data = await response.json();
      if (response.ok && data.user) {
        setUser(data.user);
        setLoginEmail('');
        setLoginPassword('');
        setCurrentPage('dashboard');
      } else {
        setLoginError(data.detail || 'Invalid email or password.');
      }
    } catch (err) {
      setLoginError('Server connection failed.');
    }
  };

  const handleSignupSubmit = async (e) => {
    e.preventDefault();
    setSignupError('');
    if (!signupName || !signupEmail || !signupPassword) {
      setSignupError('All fields are required.');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: signupName, email: signupEmail, password: signupPassword })
      });
      const data = await response.json();
      if (response.ok) {
        setSignupName('');
        setSignupEmail('');
        setSignupPassword('');
        setLoginSuccess(`Account created for ${signupName}! Please login below.`);
        setCurrentPage('login');
      } else {
        setSignupError(data.detail || 'Registration failed.');
      }
    } catch (err) {
      setSignupError('Server connection failed.');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setSessions([]);
    setSessionId(null);
    setMessages([]);
    setCurrentPage('landing');
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setResumeFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
    }
  };

  const startInterviewSetup = async () => {
    setSetupStatus('');
    setIsSettingUp(true);
    setInterviewComplete(false);
    setMessages([]);
    setRevealedAccordions({});
    setCurrentRound(1);

    const total = (parseInt(aptQ)||0) + (parseInt(techQ)||0) + (parseInt(commQ)||0) + (parseInt(resumeQ)||0);
    setTotalRounds(total);

    const formData = new FormData();
    if (resumeFile) formData.append('resume', resumeFile);
    formData.append('phone_number', phoneNumber);
    formData.append('apt_q', aptQ);
    formData.append('tech_q', techQ);
    formData.append('comm_q', commQ);
    formData.append('resume_q', resumeQ);
    formData.append('email', user ? user.email : 'anonymous');
    formData.append('target_role', targetRole);
    formData.append('candidate_domain', candidateDomain);
    formData.append('aptitude_types', selectedAptitudes.join(','));

    try {
      const response = await fetch(`${API_BASE}/api/interview/start`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (response.ok) {
        setSessionId(data.session_id);
        setMessages([{
          role: 'assistant',
          content: data.first_q,
          explanation: data.explanation,
          ideal_answer: data.ideal_answer
        }]);
        if (data.audio_b64) setAudioUrl(`data:audio/mp3;base64,${data.audio_b64}`);
        setSetupStatus('Interview loaded successfully!');
      } else {
        setSetupStatus(data.detail || 'Failed to start interview.');
      }
    } catch (err) {
      setSetupStatus('Failed to upload and connect to backend.');
    } finally {
      setIsSettingUp(false);
    }
  };

  const toggleAccordion = (index) => {
    setRevealedAccordions(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const submitAnswer = async (audioBlob = null) => {
    if (!textAnswer.trim() && !audioBlob) return;
    setIsSubmittingAnswer(true);
    setAudioUrl(null);

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('user_message', textAnswer);
    formData.append('current_round', currentRound);
    if (audioBlob) {
      formData.append('user_audio', audioBlob, 'audio_response.webm');
    }

    // Optimistically push user message to UI
    const tempUserMessage = textAnswer || "Voice response submitted.";
    setMessages(prev => [...prev, { role: 'user', content: tempUserMessage }]);
    setTextAnswer('');

    try {
      const response = await fetch(`${API_BASE}/api/interview/chat`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (response.ok) {
        if (data.feedback) {
          setInterviewComplete(true);
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: data.feedback,
            isComplete: true
          }]);
        } else {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: data.next_question,
            explanation: data.explanation,
            ideal_answer: data.ideal_answer
          }]);
        }
        setCurrentRound(data.current_round);
        if (data.audio_b64) setAudioUrl(`data:audio/mp3;base64,${data.audio_b64}`);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Error submitting answer. Please retry.' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Please retry.' }]);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const startVoiceRecording = async () => {
    if (isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        submitAnswer(audioBlob);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      alert('Could not access microphone.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Navigation */}
      <header className="nav-container">
        <div className="nav-logo" onClick={() => setCurrentPage('landing')} style={{ cursor: 'pointer' }}>
          HireMind AI
        </div>
        <div className="nav-links">
          {/* Theme Toggle Button */}
          <button 
            className="theme-toggle-btn"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            style={{ marginRight: '8px' }}
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          {currentPage !== 'landing' && (
            <button className="btn btn-secondary btn-sm" onClick={() => setCurrentPage('landing')}>
              <Home size={16} /> Home
            </button>
          )}
          
          {!user ? (
            <>
              {currentPage !== 'login' && (
                <button className="btn btn-secondary btn-sm" onClick={() => setCurrentPage('login')}>
                  <Lock size={16} /> Login
                </button>
              )}
              {currentPage !== 'signup' && (
                <button className="btn btn-primary btn-sm" onClick={() => setCurrentPage('signup')}>
                  <UserPlus size={16} /> Sign Up
                </button>
              )}
            </>
          ) : (
            <>
              {currentPage !== 'dashboard' && (
                <button className="btn btn-secondary btn-sm" onClick={() => setCurrentPage('dashboard')}>
                  Dashboard
                </button>
              )}
              {currentPage !== 'interview' && (
                <button className="btn btn-primary btn-sm" onClick={() => setCurrentPage('interview')}>
                  Start Practice
                </button>
              )}
              <button className="btn btn-danger btn-sm" onClick={handleLogout}>
                <LogOut size={16} /> Logout
              </button>
            </>
          )}
        </div>
      </header>

      {/* Hidden Audio AutoPlay Container */}
      {audioUrl && <audio src={audioUrl} autoPlay style={{ display: 'none' }} />}

      {/* Main Content Areas */}
      <main style={{ flex: 1 }}>
        {/* Landing Page */}
        {currentPage === 'landing' && (
          <div className="landing-group-container">
            <div className="landing-hero-container">
              <h1 className="hero-title">Prepare for your next tech role with AI</h1>
              <p className="hero-subtitle">
                Ingest your resume, practice realistic technical and aptitude interview rounds, and receive detailed feedback with tailored revision resources.
              </p>
              <button 
                className="btn btn-primary btn-lg"
                onClick={() => setCurrentPage(user ? 'interview' : 'login')}
              >
                <Play size={18} fill="white" /> Start Practice Now
              </button>
            </div>

            <div className="features-summary">
              <div className="summary-item">
                <h4>Aptitude & Logic</h4>
                <p>Logic puzzles, brainteasers, and scenario analysis questions.</p>
              </div>
              <div className="summary-item">
                <h4>Technical & Resume</h4>
                <p>Coding concepts, cloud architecture, and CV-specific validation.</p>
              </div>
              <div className="summary-item">
                <h4>Voice & Reports</h4>
                <p>Real-time speech synthesis, Whisper transcription, and structured scoring.</p>
              </div>
            </div>

            <footer className="landing-footer">
              <p>© 2026 HireMind AI. All Rights Reserved.</p>
            </footer>
          </div>
        )}

        {/* Login Page */}
        {currentPage === 'login' && (
          <div className="glass-card">
            <h2>Login to HireMind</h2>
            {loginSuccess && <div className="form-success">{loginSuccess}</div>}
            {loginError && <div className="form-error">{loginError}</div>}
            
            <form onSubmit={handleLoginSubmit}>
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  className="form-control" 
                  placeholder="Enter email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input 
                  type="password" 
                  className="form-control" 
                  placeholder="Enter password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }}>
                Login
              </button>
            </form>
            <div className="switch-auth-prompt">
              Don't have an account?{' '}
              <button className="switch-auth-link" onClick={() => setCurrentPage('signup')}>
                Create an account
              </button>
            </div>
          </div>
        )}

        {/* Signup Page */}
        {currentPage === 'signup' && (
          <div className="glass-card">
            <h2>Create New Account</h2>
            {signupError && <div className="form-error">{signupError}</div>}
            
            <form onSubmit={handleSignupSubmit}>
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="John Doe"
                  value={signupName}
                  onChange={(e) => setSignupName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  className="form-control" 
                  placeholder="john@example.com"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input 
                  type="password" 
                  className="form-control" 
                  placeholder="Choose password"
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }}>
                Register & Sign Up
              </button>
            </form>
            <div className="switch-auth-prompt">
              Already have an account?{' '}
              <button className="switch-auth-link" onClick={() => setCurrentPage('login')}>
                Login here
              </button>
            </div>
          </div>
        )}

        {/* Dashboard Page */}
        {currentPage === 'dashboard' && (
          <div className="dashboard-container">
            <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h1>Candidate Dashboard</h1>
                <p style={{ color: 'var(--text-muted)', marginTop: '5px' }}>
                  Welcome back, {user ? user.name : 'Candidate'}!
                </p>
              </div>
              <button className="btn btn-primary" onClick={() => setCurrentPage('interview')}>
                Start New Interview
              </button>
            </div>

            <h2 className="session-history-title">Here is your interview performance history:</h2>
            
            {sessions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', background: 'var(--panel-bg)', borderRadius: '12px', border: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                No interview sessions recorded yet. Start a new interview to begin!
              </div>
            ) : (
              <div className="sessions-list">
                {sessions.map((session, idx) => {
                  const isExpanded = expandedSession === idx;
                  const totalScore = session.evaluations.reduce((sum, e) => sum + e.overall_score, 0);
                  const avgScore = (totalScore / Math.max(1, session.evaluations.length)).toFixed(1);

                  return (
                    <div key={idx} className="session-card">
                      <div className="session-header" onClick={() => setExpandedSession(isExpanded ? null : idx)} style={{ cursor: 'pointer' }}>
                        <div className="session-meta">
                          <h3>Target Role: {session.profile?.target_role || 'General Tech Role'}</h3>
                          <p>Session ID: {session.session_id}</p>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                          <span className="session-score">Avg Score: {avgScore}/10</span>
                          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div>
                          <div style={{ marginBottom: '20px', padding: '15px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-color)', whiteSpace: 'pre-wrap' }}>
                            <h4 style={{ color: 'var(--text-color)', marginBottom: '8px' }}>Final Report:</h4>
                            {session.feedback}
                          </div>

                          <h4 style={{ color: 'var(--text-color)', marginBottom: '10px' }}>Evaluation Breakdown:</h4>
                          <div className="evaluations-container">
                            {session.evaluations.map((evalObj, eIdx) => (
                              <div key={eIdx} className="eval-item">
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                  <span className="eval-q">Q{eIdx + 1}: {evalObj.question}</span>
                                  <span className="eval-score">Score: {evalObj.overall_score}/10</span>
                                </div>
                                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                                  <strong>Your Answer:</strong> {evalObj.candidate_answer}
                                </p>
                                <p style={{ fontSize: '0.9rem', color: 'var(--primary-color)', marginTop: '4px' }}>
                                  <strong>Feedback:</strong> {evalObj.feedback}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Live Interview Page */}
        {currentPage === 'interview' && (
          <div className="interview-split-container">
            {/* Setup Column */}
            <div className="interview-setup-column">
              <h3>1. Candidate Setup</h3>
              
              <div 
                className="file-upload-zone"
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current.click()}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }} 
                  onChange={handleFileSelect}
                  accept=".pdf,.docx"
                />
                <FileText size={32} style={{ margin: '0 auto var(--primary-color)', color: resumeFile ? 'var(--primary-color)' : 'var(--text-muted)' }} />
                {resumeFile ? (
                  <p className="uploaded-name">Selected: {resumeFile.name}</p>
                ) : (
                  <p>Click or drag to upload Resume (PDF/DOCX)</p>
                )}
              </div>

              <div className="form-group">
                <label>Phone Number for SMS (Optional)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="+1234567890"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                />
              </div>

              <div className="form-group-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px', marginBottom: '10px' }}>
                <div className="form-group">
                  <label style={{ fontSize: '0.85rem' }}>Target Job Role</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="e.g. Software Engineer"
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '0.85rem' }}>Domain</label>
                  <select 
                    className="form-control"
                    value={candidateDomain}
                    onChange={(e) => setCandidateDomain(e.target.value)}
                    style={{ background: 'var(--panel-bg)', color: 'var(--text-color)', border: '1px solid var(--border-color)', borderRadius: '6px', height: '38px', padding: '0 8px', width: '100%' }}
                  >
                    <option value="Tech">Tech / Engineering</option>
                    <option value="Business">Business / Management</option>
                    <option value="Finance">Finance / Banking</option>
                    <option value="Marketing">Marketing / Sales</option>
                    <option value="Creative">Creative / Design</option>
                    <option value="Healthcare">Healthcare / Biotech</option>
                  </select>
                </div>
              </div>

              <label style={{ fontSize: '0.9rem', fontWeight: '500' }}>Question Configuration</label>
              <div className="round-config-grid" style={{ marginBottom: '12px' }}>
                <div className="form-group">
                  <label style={{ fontSize: '0.8rem' }}>Aptitude Qs</label>
                  <input type="number" className="form-control" value={aptQ} onChange={(e) => setAptQ(parseInt(e.target.value) || 0)} min="0" />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '0.8rem' }}>Technical Qs</label>
                  <input type="number" className="form-control" value={techQ} onChange={(e) => setTechQ(parseInt(e.target.value) || 0)} min="0" />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '0.8rem' }}>Communication</label>
                  <input type="number" className="form-control" value={commQ} onChange={(e) => setCommQ(parseInt(e.target.value) || 0)} min="0" />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '0.8rem' }}>Resume Qs</label>
                  <input type="number" className="form-control" value={resumeQ} onChange={(e) => setResumeQ(parseInt(e.target.value) || 0)} min="0" />
                </div>
              </div>

              {aptQ > 0 && (
                <div style={{ marginTop: '10px', marginBottom: '18px', padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <label style={{ fontSize: '0.85rem', fontWeight: '600' }}>Select Aptitude Types</label>
                    <button 
                      type="button"
                      onClick={() => {
                        const allTypes = ['numerical', 'quantitative', 'logical', 'verbal', 'abstract'];
                        if (selectedAptitudes.length === allTypes.length) {
                          setSelectedAptitudes([]);
                        } else {
                          setSelectedAptitudes(allTypes);
                        }
                      }}
                      style={{ background: 'none', border: 'none', color: 'var(--primary-color)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: '600', padding: 0 }}
                    >
                      {selectedAptitudes.length === 5 ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {[
                      { value: 'numerical', label: 'Numerical Reasoning' },
                      { value: 'quantitative', label: 'Quantitative Aptitude' },
                      { value: 'logical', label: 'Logical Reasoning' },
                      { value: 'verbal', label: 'Verbal Reasoning' },
                      { value: 'abstract', label: 'Abstract Reasoning' }
                    ].map((type) => {
                      const isChecked = selectedAptitudes.includes(type.value);
                      return (
                        <label key={type.value} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                          <input 
                            type="checkbox" 
                            checked={isChecked}
                            onChange={() => {
                              if (isChecked) {
                                setSelectedAptitudes(selectedAptitudes.filter(x => x !== type.value));
                              } else {
                                setSelectedAptitudes([...selectedAptitudes, type.value]);
                              }
                            }}
                          />
                          {type.label}
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              <button 
                className="btn btn-primary" 
                style={{ width: '100%' }}
                onClick={startInterviewSetup}
                disabled={isSettingUp}
              >
                {isSettingUp ? 'Parsing Profile...' : 'Parse Resume & Start'}
              </button>


              {setupStatus && (
                <div style={{ marginTop: '15px', color: setupStatus.includes('Error') ? 'var(--danger-color)' : 'var(--primary-color)', fontSize: '0.9rem', textAlign: 'center' }}>
                  {setupStatus}
                </div>
              )}
            </div>

            {/* Chat Column */}
            <div className="interview-chat-column">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <MessageSquare size={20} /> Live Interview
                </h3>
                {sessionId && totalRounds > 0 && (
                  <span style={{ fontSize: '0.85rem', background: 'var(--secondary-color)', padding: '4px 10px', borderRadius: '20px', color: 'var(--text-muted)' }}>
                    {interviewComplete ? 'Complete' : `Round ${currentRound} / ${totalRounds}`}
                  </span>
                )}
              </div>
              {sessionId && totalRounds > 0 && (
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${Math.min(100, ((currentRound - 1) / totalRounds) * 100)}%` }}
                  />
                </div>
              )}

              <div className="chat-messages">
                {messages.length === 0 ? (
                  <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <MessageSquare size={40} style={{ marginBottom: '12px', opacity: 0.3 }} />
                    <p>Set up your interview on the left and click <strong>Parse Resume &amp; Start</strong> to begin.</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => {
                    const isUser = msg.role === 'user';
                    const hasDetails = !isUser && (msg.explanation || msg.ideal_answer);
                    const showAccordion = revealedAccordions[idx];

                    if (msg.isComplete) {
                      return (
                        <div key={idx} className="feedback-complete-card">
                          <div className="feedback-complete-header">Interview Complete — Your Feedback Report</div>
                          <div className="feedback-complete-body" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                          <button className="btn btn-primary" style={{ marginTop: '16px', width: '100%' }} onClick={() => { setCurrentPage('dashboard'); loadDashboard(); }}>
                            View Dashboard History
                          </button>
                        </div>
                      );
                    }

                    return (
                      <div key={idx} className={`message-bubble ${msg.role}`}>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        {isSubmittingAnswer && idx === messages.length - 1 && isUser && (
                          <div className="typing-indicator"><span/><span/><span/></div>
                        )}
                        {hasDetails && (
                          <div className="details-box">
                            <div className="details-summary-toggle" onClick={() => toggleAccordion(idx)}>
                              <span style={{ fontWeight: '700', color: 'var(--primary-color)', fontSize: '0.8rem' }}>{showAccordion ? 'HIDE' : 'SHOW'}</span>
                              <span>Reveal Explanation &amp; Ideal Answer</span>
                              {showAccordion ? <ChevronUp size={16} style={{ marginLeft: 'auto' }} /> : <ChevronDown size={16} style={{ marginLeft: 'auto' }} />}
                            </div>
                            {showAccordion && (
                              <div className="details-content">
                                {msg.ideal_answer && (
                                  <div>
                                    <div className="ideal-title">Ideal Answer</div>
                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-color)', paddingLeft: '10px', marginTop: '4px' }}>{msg.ideal_answer}</p>
                                  </div>
                                )}
                                {msg.explanation && (
                                  <div style={{ marginTop: '8px' }}>
                                    <div className="explanation-title">Concept Explanation</div>
                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-color)', paddingLeft: '10px', marginTop: '4px' }}>{msg.explanation}</p>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
                <div ref={chatEndRef} />
              </div>

              {isRecording && (
                <div className="recording-wave-container">
                  <div className="recording-wave-bar"></div>
                  <div className="recording-wave-bar"></div>
                  <div className="recording-wave-bar"></div>
                  <div className="recording-wave-bar"></div>
                  <div className="recording-wave-bar"></div>
                  <span className="recording-wave-text">Recording Audio... Click Mic to submit</span>
                </div>
              )}

              {/* Agent Processing Status Card */}
              {isSubmittingAnswer && (
                <div className="agent-status-card">
                  <div className="agent-status-header">
                    <span className="agent-pulse-dot" />
                    Processing your answer...
                  </div>
                  <div className="agent-pipeline">
                    {[
                      { label: 'Evaluation Agent', desc: 'Scoring your answer' },
                      { label: 'Question Agent',   desc: 'Generating next question' },
                      { label: 'Feedback Agent',   desc: 'Building your report' },
                      { label: 'Voice Agent',       desc: 'Synthesizing audio' },
                    ].map(({ label, desc }) => {
                      const isActive = agentStatus.toLowerCase().includes(label.toLowerCase().split(' ')[0]);
                      return (
                        <div key={label} className={`agent-step ${isActive ? 'active' : ''}`}>
                          <div className={`agent-step-dot ${isActive ? 'active' : ''}`} />
                          <div>
                            <div className="agent-step-label">{label}</div>
                            <div className="agent-step-desc">{desc}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="chat-input-row">
                <input
                  type="text"
                  className="form-control"
                  placeholder={interviewComplete ? 'Interview complete.' : 'Type your answer here...'}
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  disabled={!sessionId || isSubmittingAnswer || interviewComplete}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !isSubmittingAnswer) submitAnswer(); }}
                />
                
                <button
                  className={`btn ${isRecording ? 'btn-danger' : 'btn-secondary'}`}
                  title={isRecording ? 'Stop Recording' : 'Speak Answer'}
                  onClick={startVoiceRecording}
                  disabled={!sessionId || isSubmittingAnswer || interviewComplete}
                >
                  <Mic size={18} />
                </button>

                <button
                  className="btn btn-primary"
                  onClick={() => submitAnswer()}
                  disabled={!sessionId || isSubmittingAnswer || interviewComplete}
                >
                  {isSubmittingAnswer ? 'Sending...' : 'Submit'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
