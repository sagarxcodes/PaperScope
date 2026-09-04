import './App.css'

function App() {
  return (
    <main className="page">
      {/* Navigation */}
      <nav className="navbar">
        <div className="brand">
          <span className="brand-logo">P</span>
          <span>PaperScope</span>
        </div>

        <div className="nav-links">
          <a href="/about">About Us</a>
          <button
            className="nav-button"
            onClick={() => (window.location.href = '/login')}
          >
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-content">
          <p className="eyebrow">AI-POWERED</p>

          <h1>
            <span className="hero-highlight">
              COMPETENCY
              <br />
              INTELLIGENCE
            </span>
          </h1>

          <p className="hero-description">
            Identify gaps.
            <br />
            Personalize learning.
            <br />
            Strengthen capability.
          </p>

          <button
            className="primary-button"
            onClick={() => (window.location.href = '/login')}
          >
            Get Started <span>→</span>
          </button>
        </div>

        {/* 3D PaperScope Book */}
        <div className="book-stage">
          <div className="book-shadow"></div>

          <div className="real-book">
            <div className="book-spine"></div>
            <div className="book-back-cover"></div>
            <div className="book-paper-stack"></div>

            <div className="book-page book-page-1">
              <div className="page-inner">
                <span className="page-number">01</span>
                <h2>Introduction</h2>
                <div className="page-line"></div>
                <p>Understanding learning through intelligence.</p>
              </div>
            </div>

            <div className="book-page book-page-2">
              <div className="page-inner center-page">
                <span className="page-number">02</span>
                <h3>THE NXT-GEN</h3>
                <h2>LEARNING SOFTWARE</h2>
                <strong>PAPERSCOPE.</strong>
              </div>
            </div>

            <div className="book-page book-page-3">
              <div className="page-inner">
                <span className="page-number">03</span>
                <h2>Especially built</h2>
                <p>for self-paced learning.</p>
                <div className="page-line"></div>
                <strong>Impacting the education culture.</strong>
              </div>
            </div>

            <div className="book-front-cover">
              <div className="cover-inner">
                <span className="cover-small">AI POWERED</span>
                <h2>PaperScope</h2>
                <span className="cover-main">
                  AI POWERED
                  <br />
                  INTELLIGENCE
                </span>
              </div>
            </div>
          </div>

          <p className="book-label">AI LEARNING INTELLIGENCE</p>
        </div>
      </section>

      {/* Stats */}
      <section className="stats">
        <div className="stat">
          <strong>10K+</strong>
          <span>Data Points</span>
        </div>

        <div className="stat">
          <strong>AI-Driven</strong>
          <span>Assessment</span>
        </div>

        <div className="stat">
          <strong>6+</strong>
          <span>Intelligence Modules</span>
        </div>
      </section>

      {/* PaperScope AI 3D Experience */}
      <section className="ai-experience">
        <div className="ai-experience-heading">
          <p className="ai-eyebrow">PAPERSCOPE AI</p>
          <h2>
            From learning material
            <br />
            to <span>competency intelligence.</span>
          </h2>
          <p>
            See how PaperScope transforms learning content into personalized,
            actionable intelligence.
          </p>
        </div>

        <div className="ai-stage">
          <div className="ai-orbit orbit-one"></div>
          <div className="ai-orbit orbit-two"></div>
          <div className="ai-core">
            <span className="core-p">Paper</span>
            <span className="core-label">Scope</span>
          </div>

          <div className="ai-card ai-card-material">
            <span className="ai-card-index">01</span>
            <span className="ai-card-icon">▤</span>
            <strong>Learning Material</strong>
            <small>Uploaded content</small>
          </div>

          <div className="ai-card ai-card-analysis">
            <span className="ai-card-index">02</span>
            <span className="ai-card-icon">⌁</span>
            <strong>AI Analysis</strong>
            <small>Processing knowledge</small>
          </div>

          <div className="ai-card ai-card-competency">
            <span className="ai-card-index">03</span>
            <span className="ai-card-icon">◈</span>
            <strong>Competency Map</strong>
            <small>Capability analysis</small>
          </div>

          <div className="ai-card ai-card-gap">
            <span className="ai-card-index">04</span>
            <span className="ai-card-icon">△</span>
            <strong>Gap Detection</strong>
            <small>3 gaps identified</small>
          </div>

          <div className="ai-card ai-card-learning">
            <span className="ai-card-index">05</span>
            <span className="ai-card-icon">↗</span>
            <strong>Learning Path</strong>
            <small>Personalized for you</small>
          </div>

          <div className="ai-card ai-card-assessment">
            <span className="ai-card-index">06</span>
            <span className="ai-card-icon">✓</span>
            <strong>AI Assessment</strong>
            <small>Adaptive practice</small>
          </div>

          <div className="ai-scan-line"></div>
        </div>

        <div className="ai-caption">
          <span>01</span>
          <p>UNDERSTAND</p>
          <span>02</span>
          <p>ANALYZE</p>
          <span>03</span>
          <p>PERSONALIZE</p>
          <span>04</span>
          <p>STRENGTHEN</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="site-footer">
        <div className="footer-main">
          <div className="footer-quote">
            <p>
              The right direction can transform
              <br />
              the way you learn.
            </p>
          </div>

          <div className="footer-contact">
            <span>CONTACT US</span>
            <a href="mailto:contact@paperscope.in">
              contact@paperscope.in
            </a>
          </div>
        </div>

        <div className="sih-footer">
          PAPERSCOPE — AN AI-POWERED LEARNING INNOVATION · SMART INDIA HACKATHON 2026
        </div>
      </footer>
    </main>
  )
}

export default App
