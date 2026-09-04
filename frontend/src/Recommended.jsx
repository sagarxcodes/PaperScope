import { useEffect, useState } from 'react'
import './Recommended.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function Recommended() {
  const [courses, setCourses] = useState([])

  useEffect(() => {
    const saved =
      localStorage.getItem('paperscope_analysis') ||
      localStorage.getItem('paperscopeAnalysis')

    if (saved) {
      try {
        const data = JSON.parse(saved)

        const training =
          data?.igot_training ||
          data?.training ||
          data?.recommendations ||
          data?.personalized_recommendations ||
          []

        setCourses(Array.isArray(training) ? training : [])
      } catch (error) {
        console.error('Failed to load PaperScope recommendations:', error)
      }
    }
  }, [])

  return (
    <main className="recommended-page">
      <nav className="recommended-nav">
        <button onClick={() => (window.location.href = '/dashboard')}>
          ← Back to Dashboard
        </button>

        <strong>PaperScope</strong>
      </nav>

      <section className="recommended-content">
        <p className="section-label">IGOT KARMAYOGI</p>

        <h1>Recommended for Your Weakness</h1>

        <p className="recommended-lead">
          PaperScope connects identified competency gaps with
          relevant learning opportunities so recommendations are
          based on evidence rather than generic course lists.
        </p>

        <div className="course-list">
          {courses.map((course, index) => (
            <article className="course-card" key={course.title}>
              <div className="course-score">
                <span>
                  {index === 0
                    ? 'HIGH-PRIORITY GAP'
                    : 'DEVELOPING AREA'}
                </span>

                <strong>
                  {index === 0 ? '48%' : '57%'}
                </strong>

                <small>CURRENT COMPETENCY</small>
              </div>

              <div className="course-info">
                <p className="course-label">
                  RECOMMENDED IGOT TRAINING
                </p>

                <h2>{course.title}</h2>

                <p>{course.reason}</p>

                <div className="course-actions">
                  <button
                    onClick={() => (window.location.href = '/analysis')}
                  >
                    View Complete Analysis →
                  </button>

                  <a
                    href="https://igotkarmayogi.gov.in/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open iGOT Karmayogi ↗
                  </a>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <footer className="recommended-footer">
        <span>PAPERSCOPE — SMART INDIA HACKATHON 2026</span>
        <span>CONTACT US · contact@paperscope.in</span>
      </footer>
    </main>
  )
}

export default Recommended
