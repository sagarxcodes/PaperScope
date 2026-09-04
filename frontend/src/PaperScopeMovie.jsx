import { useEffect, useState } from 'react'
import './PaperScopeMovie.css'

const scenes = [
  {
    id: 1,
    time: '0:00 — 0:08',
    title: 'THE LONE LEARNER',
    text: 'He studies every day. He works hard. He keeps moving forward.',
  },
  {
    id: 2,
    time: '0:08 — 0:18',
    title: 'THE UNCERTAINTY',
    text: 'Knowing what to study next can be.',
  },
  {
    id: 3,
    time: '0:18 — 0:27',
    title: 'THE GAP',
    text: 'What if learning could understand you?',
  },
  {
    id: 4,
    time: '0:27 — 0:36',
    title: 'PAPERSCOPE',
    text: 'An AI-powered learning intelligence designed to turn uncertainty into direction.',
  },
  {
    id: 5,
    time: '0:36 — 0:48',
    title: 'INTELLIGENCE',
    text: 'PaperScope identifies where you stand, recognizes what you missed, and builds what you need next.',
  },
  {
    id: 6,
    time: '0:48 — 0:59',
    title: 'THE TRANSFORMATION',
    text: 'Learning is not about consuming more content. It is about knowing what matters.',
  },
  {
    id: 7,
    time: '0:59 — 1:08',
    title: 'THE BIGGER VISION',
    text: 'Whether you learn in a classroom, at home, or entirely on your own...',
  },
  {
    id: 8,
    time: '1:08 — 1:15',
    title: 'YOUR DIRECTION',
    text: 'No learner should learn without direction.',
  },
]

function PaperScopeMovie() {
  const [scene, setScene] = useState(1)

  useEffect(() => {
    const timer = setInterval(() => {
      setScene((current) => (current >= scenes.length ? 1 : current + 1))
    }, 9000)

    return () => clearInterval(timer)
  }, [])

  return (
    <section className={`paperscope-movie movie-scene-${scene}`}>
      <div className="movie-header">
        <div>
          <span className="movie-eyebrow">PAPERSCOPE PRESENTS</span>
          <h2>
            THE DIRECTION
            <br />
            <span>TO LEARN.</span>
          </h2>
        </div>

        <div className="movie-counter">
          <span>SCENE</span>
          <strong>0{scene}</strong>
          <small>/ 08</small>
        </div>
      </div>

      <div className="movie-screen">

        {/* Ambient cinematic light */}
        <div className="movie-glow"></div>
        <div className="movie-grid"></div>

        {/* Scene 1 — learner */}
        <div className="learner-room">
          <div className="room-window">
            <div className="window-light"></div>
          </div>

          <div className="desk">
            <div className="laptop">
              <div className="laptop-screen">
                <span>PDF</span>
                <span>QUESTION PAPER</span>
                <span>NOTES</span>
              </div>
            </div>

            <div className="book-stack">
              <span></span>
              <span></span>
              <span></span>
            </div>

            <div className="paper paper-one">STATISTICS</div>
            <div className="paper paper-two">PROBABILITY</div>
          </div>

          <div className="learner">
            <div className="learner-head"></div>
            <div className="learner-body"></div>
            <div className="learner-arm"></div>
          </div>

          <div className="desk-clock">11:47 PM</div>
        </div>

        {/* Scene 2 — uncertainty */}
        <div className="uncertainty">
          <span>WHERE DO I STAND?</span>
          <span>WHAT DID I MISS?</span>
          <span>WHAT SHOULD I LEARN NEXT?</span>

          <div className="unknown-card">
            <small>PROGRESS</small>
            <strong>?</strong>
            <small>COMPETENCY — UNKNOWN</small>
            <small>LEARNING PATH — UNDEFINED</small>
          </div>
        </div>

        {/* Scene 3 — gaps */}
        <div className="gap-scene">
          <div className="data-fragments">
            <i></i><i></i><i></i><i></i><i></i><i></i>
            <i></i><i></i><i></i><i></i><i></i><i></i>
          </div>

          <div className="gap-marker gap-one">
            <b>01</b>
            KNOWLEDGE GAP
          </div>

          <div className="gap-marker gap-two">
            <b>02</b>
            COMPETENCY GAP
          </div>

          <div className="gap-marker gap-three">
            <b>03</b>
            UNASSESSED
          </div>

          <div className="question">
            WHAT IF LEARNING
            <br />
            COULD <span>UNDERSTAND YOU?</span>
          </div>
        </div>

        {/* Scene 4 — PaperScope */}
        <div className="arrival-scene">
          <div className="paperscope-core">
            <div className="core-ring ring-one"></div>
            <div className="core-ring ring-two"></div>
            <div className="core-p">P</div>
          </div>

          <div className="arrival-name">PAPERSCOPE</div>
          <div className="arrival-line">
            AI-POWERED LEARNING INTELLIGENCE
          </div>
        </div>

        {/* Scene 5 — intelligence pipeline */}
        <div className="intelligence-scene">
          <div className="pipeline">
            <div className="pipeline-node active">
              <span>01</span>
              Learning Material
            </div>
            <div className="pipeline-line"></div>
            <div className="pipeline-node">
              <span>02</span>
              AI Analysis
            </div>
            <div className="pipeline-line"></div>
            <div className="pipeline-node">
              <span>03</span>
              Competency Mapping
            </div>
            <div className="pipeline-line"></div>
            <div className="pipeline-node">
              <span>04</span>
              Gap Detection
            </div>
            <div className="pipeline-line"></div>
            <div className="pipeline-node">
              <span>05</span>
              Personalized Learning
            </div>
            <div className="pipeline-line"></div>
            <div className="pipeline-node">
              <span>06</span>
              AI Assessment
            </div>
          </div>

          <div className="profile-dashboard">
            <div className="dashboard-label">YOUR COMPETENCY PROFILE</div>

            <div className="profile-row">
              <span>Statistical Concepts</span>
              <strong>82%</strong>
            </div>
            <div className="profile-bar"><i style={{ width: '82%' }}></i></div>

            <div className="profile-row">
              <span>Data Interpretation</span>
              <strong>61%</strong>
            </div>
            <div className="profile-bar"><i style={{ width: '61%' }}></i></div>

            <div className="profile-row">
              <span>Research Methods</span>
              <strong>74%</strong>
            </div>
            <div className="profile-bar"><i style={{ width: '74%' }}></i></div>

            <div className="gap-result">3 COMPETENCY GAPS IDENTIFIED</div>

            <div className="study-plan">
              <div>YOUR PERSONALIZED PATH</div>
              <span>01 — Strengthen Data Interpretation</span>
              <span>02 — Practice Statistical Concepts</span>
              <span>03 — Take Adaptive Assessment</span>
            </div>
          </div>
        </div>

        {/* Scene 6 — progress */}
        <div className="progress-scene">
          <div className="progress-label">COMPETENCY PROGRESS</div>

          <div className="progress-number">
            <strong>91%</strong>
            <span>↑ CONSISTENT PROGRESS</span>
          </div>

          <div className="progress-graph">
            <i style={{ height: '35%' }}></i>
            <i style={{ height: '52%' }}></i>
            <i style={{ height: '68%' }}></i>
            <i style={{ height: '78%' }}></i>
            <i style={{ height: '91%' }}></i>
          </div>

          <div className="correct-answer">
            CORRECT <span>✓</span>
          </div>
        </div>

        {/* Scene 7 — network */}
        <div className="network-scene">
          <div className="network-core">P</div>

          <div className="network-person person-one">LEARNER</div>
          <div className="network-person person-two">NIOS</div>
          <div className="network-person person-three">HOME</div>
          <div className="network-person person-four">PROFESSIONAL</div>
          <div className="network-person person-five">SELF-LEARNER</div>

          <div className="network-line line-one"></div>
          <div className="network-line line-two"></div>
          <div className="network-line line-three"></div>
          <div className="network-line line-four"></div>
          <div className="network-line line-five"></div>
        </div>

        {/* Final scene */}
        <div className="final-scene">
          <div className="final-statement">
            <span>NO LEARNER</span>
            <span>SHOULD LEARN</span>
            <span>WITHOUT <b>DIRECTION.</b></span>
          </div>

          <div className="final-brand">
            <strong>PaperScope</strong>
            <span>AI-POWERED COMPETENCY INTELLIGENCE</span>
          </div>
        </div>

        <div className="movie-caption">
          {scenes[scene - 1].text}
        </div>
      </div>

      <div className="movie-controls">
        {scenes.map((item) => (
          <button
            key={item.id}
            className={scene === item.id ? 'active' : ''}
            onClick={() => setScene(item.id)}
            aria-label={`Scene ${item.id}`}
          >
            <span>{String(item.id).padStart(2, '0')}</span>
          </button>
        ))}
      </div>

      <div className="movie-footer-line">
        <span>CONFUSION</span>
        <i></i>
        <span>UNDERSTANDING</span>
        <i></i>
        <span>DIRECTION</span>
        <i></i>
        <span>PROGRESS</span>
      </div>
    </section>
  )
}

export default PaperScopeMovie
