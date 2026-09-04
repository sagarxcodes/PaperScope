import { useEffect, useMemo, useState } from 'react'
import './Quiz.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function Quiz() {
  const [questions, setQuestions] = useState([])
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState(null)
  const [answers, setAnswers] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [finished, setFinished] = useState(false)
  const [assessment, setAssessment] = useState(null)
  const [learnerProfile, setLearnerProfile] = useState(null)
  const [activeAnalysis, setActiveAnalysis] = useState(null)

  const loadQuiz = async (profileOverride = null) => {
    setLoading(true)
    setError('')
    setFinished(false)
    setAssessment(null)
    setCurrent(0)
    setSelected(null)
    setAnswers([])

    try {
      const savedAnalysis =
        localStorage.getItem('paperscope_active_analysis')

      const parsedAnalysis = savedAnalysis
        ? JSON.parse(savedAnalysis)
        : null

      setActiveAnalysis(parsedAnalysis)

      const stored = JSON.parse(
        localStorage.getItem('paperscopeAnalysis') || 'null'
      )

      const text =
        stored?.material?.text ||
        stored?.text ||
        localStorage.getItem('paperscopeMaterialText') ||
        ''

      if (!text.trim()) {
        throw new Error(
          'No analysed learning material found. Please upload a file from the Dashboard.'
        )
      }

      const savedProfile = JSON.parse(
        localStorage.getItem('paperscope_learner_profile') || 'null'
      )

      const profile =
        profileOverride ||
        savedProfile || {
          exam_target: 'Competitive Examination',
          mastery: {},
          difficulty: 'adaptive',
          recent_questions: [],
        }

      setLearnerProfile(profile)

      const response = await fetch(
        `${API}/api/questions/personalized`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            text,
            number: 5,
            learner_profile: profile,
            analysis: parsedAnalysis,
          }),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to generate personalized quiz')
      }

      const data = await response.json()

      if (!data.success || !data.questions?.length) {
        throw new Error(
          'PaperScope could not generate questions from this material.'
        )
      }

      const convertedQuestions = data.questions.map((q, index) => {
        const options =
          q.options ||
          [
            q.answer,
            ...(q.distractors || []),
          ]

        const answerIndex =
          typeof q.answer === 'number'
            ? q.answer
            : options.indexOf(q.answer)

        return {
          ...q,
          id: q.id || `personalized-${index + 1}`,
          options,
          answer:
            answerIndex >= 0
              ? answerIndex
              : 0,
          competency:
            q.target_competency ||
            q.competency ||
            q.concept ||
            q.topic ||
            'General',
        }
      })

      setQuestions(convertedQuestions)
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQuiz()
  }, [])

  const question = questions[current]

  const progress = useMemo(() => {
    if (!questions.length) return 0
    return Math.round(
      ((current + 1) / questions.length) * 100
    )
  }, [current, questions.length])

  const submitAnswer = () => {
    if (selected === null || submitting) return

    const nextAnswers = [...answers]
    nextAnswers[current] = selected

    setAnswers(nextAnswers)
    setSelected(null)

    if (current + 1 < questions.length) {
      setCurrent((previous) => previous + 1)
      return
    }

    submitQuiz(nextAnswers)
  }

  const submitQuiz = async (finalAnswers) => {
    setSubmitting(true)
    setError('')

    try {
      const response = await fetch(
        `${API}/api/questions/personalized/submit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            questions,
            answers: finalAnswers,
            learner_profile:
              learnerProfile || {
                exam_target: 'Competitive Examination',
                mastery: {},
                difficulty: 'adaptive',
                recent_questions: [],
              },
          }),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to evaluate personalized assessment')
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(
          data.message || 'Assessment evaluation failed'
        )
      }

      setAssessment(data)
      setFinished(true)

      localStorage.setItem(
        'paperscope_last_personalized_assessment',
        JSON.stringify(data)
      )

      /*
       * The backend returns the updated competency mastery.
       * Persist it locally so the next quiz starts from the
       * learner's new state.
       */
      const updatedProfile = {
        ...(learnerProfile || {}),
        mastery: data.updated_mastery || {},
        difficulty: 'adaptive',
        recent_questions: questions.map((item) => ({
          id: item.id,
          competency:
            item.target_competency ||
            item.competency ||
            item.concept,
        })),
      }

      setLearnerProfile(updatedProfile)

      localStorage.setItem(
        'paperscope_learner_profile',
        JSON.stringify(updatedProfile)
      )

      localStorage.setItem(
        'paperscope_mastery',
        JSON.stringify(data.updated_mastery || {})
      )
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const continueAdaptiveLearning = () => {
    const updatedProfile = {
      ...(learnerProfile || {}),
      mastery:
        assessment?.updated_mastery ||
        learnerProfile?.mastery ||
        {},
      difficulty: 'adaptive',
    }

    localStorage.setItem(
      'paperscope_learner_profile',
      JSON.stringify(updatedProfile)
    )

    loadQuiz(updatedProfile)
  }

  if (loading) {
    return (
      <main className="quiz-page">
        <section className="quiz-result">
          <p className="section-label">
            PAPERSCOPE INTELLIGENCE ENGINE
          </p>

          <h1>
            Generating your adaptive assessment...
          </h1>

          <p>
            PaperScope is analysing your competency profile
            and targeting the areas that need the most
            improvement.
          </p>
        </section>
      </main>
    )
  }

  if (error) {
    return (
      <main className="quiz-page">
        <section className="quiz-result">
          <p className="section-label">
            QUIZ GENERATION ERROR
          </p>

          <h1>
            Unable to generate assessment.
          </h1>

          <p>{error}</p>

          <button onClick={() => loadQuiz()}>
            Try Again →
          </button>
        </section>
      </main>
    )
  }

  if (finished && assessment) {
    const nextTarget =
      assessment.next_adaptive_target

    const updatedMastery =
      assessment.updated_mastery || {}

    return (
      <main className="quiz-page">
        <section className="quiz-result">
          <p className="section-label">
            PAPERSCOPE ADAPTIVE ASSESSMENT
          </p>

          <h1>
            Your competency profile has been updated.
          </h1>

          <div className="quiz-score">
            <strong>{assessment.accuracy}%</strong>
            <span>Assessment Accuracy</span>
          </div>

          <div className="quiz-summary-grid">
            <div className="quiz-summary-card">
              <span>Score</span>
              <strong>
                {assessment.score}/{questions.length}
              </strong>
            </div>

            <div className="quiz-summary-card">
              <span>Readiness</span>
              <strong>
                {assessment.readiness}
              </strong>
            </div>

            <div className="quiz-summary-card">
              <span>Competencies</span>
              <strong>
                {Object.keys(
                  assessment.competency_performance || {}
                ).length}
              </strong>
            </div>
          </div>

          {nextTarget && (
            <div className="adaptive-target-card">
              <p className="section-label">
                NEXT ADAPTIVE TARGET
              </p>

              <h2>
                {nextTarget.competency}
              </h2>

              <p>
                Current mastery:{' '}
                <strong>
                  {Number(nextTarget.mastery).toFixed(1)}%
                </strong>
              </p>

              <p>
                {nextTarget.reason}
              </p>
            </div>
          )}

          <div className="mastery-section">
            <p className="section-label">
              UPDATED COMPETENCY MASTERY
            </p>

            {Object.entries(updatedMastery).map(
              ([competency, mastery]) => (
                <div
                  className="mastery-row"
                  key={competency}
                >
                  <div>
                    <strong>{competency}</strong>
                    <span>
                      {Number(mastery).toFixed(1)}%
                    </span>
                  </div>

                  <div className="mastery-bar">
                    <div
                      className="mastery-fill"
                      style={{
                        width: `${Math.max(
                          0,
                          Math.min(100, mastery)
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              )
            )}
          </div>

          <div className="competency-results">
            <p className="section-label">
              COMPETENCY PERFORMANCE
            </p>

            {Object.entries(
              assessment.competency_performance || {}
            ).map(([competency, data]) => (
              <div
                className="competency-result-row"
                key={competency}
              >
                <div>
                  <strong>{competency}</strong>
                  <span>
                    {data.correct}/{data.questions} correct
                  </span>
                </div>

                <strong>{data.accuracy}%</strong>
              </div>
            ))}
          </div>


          {/* WHERE YOU STAND */}
          {assessment.where_you_stand && (
            <div className="adaptive-target-card">
              <p className="section-label">
                WHERE YOU STAND
              </p>

              <h2>
                {assessment.where_you_stand.standing ||
                  assessment.where_you_stand.level ||
                  'Current Position'}
              </h2>

              <p>
                Current score:{' '}
                <strong>
                  {assessment.where_you_stand.score ?? 0}
                </strong>
                {' '}
                ({Number(
                  assessment.where_you_stand.percentage ?? assessment.accuracy ?? 0
                ).toFixed(1)}%)
              </p>

              {assessment.where_you_stand.summary && (
                <p>
                  {assessment.where_you_stand.summary}
                </p>
              )}

              {assessment.where_you_stand.action_plan?.length > 0 && (
                <div>
                  {assessment.where_you_stand.action_plan
                    .slice(0, 3)
                    .map((action, index) => (
                      <p key={index}>
                        <strong>{index + 1}.</strong>{' '}
                        {typeof action === 'string'
                          ? action
                          : action.action ||
                            action.description ||
                            action.title ||
                            'Targeted improvement task'}
                      </p>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* ADAPTIVE LEARNING */}
          {assessment.adaptive_learning && (
            <div className="adaptive-target-card">
              <p className="section-label">
                ADAPTIVE LEARNING PLAN
              </p>

              <h2>
                {assessment.adaptive_learning.learning_mode ||
                  'Personalized Learning'}
              </h2>

              {assessment.adaptive_learning.focus_topic && (
                <p>
                  Focus competency:{' '}
                  <strong>
                    {assessment.adaptive_learning.focus_topic}
                  </strong>
                </p>
              )}

              {assessment.adaptive_learning.recommended_difficulty && (
                <p>
                  Next difficulty:{' '}
                  <strong>
                    {assessment.adaptive_learning.recommended_difficulty}
                  </strong>
                </p>
              )}

              {assessment.adaptive_learning.priorities?.length > 0 && (
                <div>
                  {assessment.adaptive_learning.priorities
                    .slice(0, 3)
                    .map((item, index) => (
                      <p key={index}>
                        <strong>
                          {item.topic || item.competency || 'Priority'}
                        </strong>
                        {' — '}
                        {item.action || 'Targeted practice'}
                      </p>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* SMART CALENDAR */}
          {assessment.smart_calendar && (
            <div className="adaptive-target-card">
              <p className="section-label">
                SMART CALENDAR
              </p>

              <h2>
                AI-generated next steps
              </h2>

              {assessment.smart_calendar.summary && (
                <p>
                  {assessment.smart_calendar.summary.total_tasks} tasks
                  {' · '}
                  {assessment.smart_calendar.summary.pending_tasks} pending
                </p>
              )}

              {assessment.smart_calendar.tasks?.length > 0 && (
                <div>
                  {assessment.smart_calendar.tasks
                    .slice(0, 5)
                    .map((task, index) => (
                      <p key={task.id || index}>
                        <strong>
                          {task.title || `Task ${index + 1}`}
                        </strong>
                        {task.description
                          ? ` — ${task.description}`
                          : ''}
                      </p>
                    ))}
                </div>
              )}
            </div>
          )}

          <button
            className="primary-button"
            onClick={continueAdaptiveLearning}
          >
            Continue Adaptive Learning →
          </button>
        </section>
      </main>
    )
  }

  if (!question) {
    return (
      <main className="quiz-page">
        <section className="quiz-result">
          <h1>No questions available.</h1>
          <button onClick={() => loadQuiz()}>
            Generate Again →
          </button>
        </section>
      </main>
    )
  }

  const competency =
    question.target_competency ||
    question.competency ||
    question.concept ||
    'General'

  const mastery =
    question.mastery_before ?? null

  return (
    <main className="quiz-page">
      <section className="quiz-container">
        <div className="quiz-header">
          <div>
            <p className="section-label">
              PAPERSCOPE ADAPTIVE QUIZ
            </p>

            <h1>
              Targeted competency assessment
            </h1>
          </div>

          <div className="quiz-progress-text">
            {current + 1}/{questions.length}
          </div>
        </div>

        <div className="quiz-progress">
          <div
            className="quiz-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="target-intelligence">
          <div>
            <span>TARGET COMPETENCY</span>
            <strong>{competency}</strong>
          </div>

          {mastery !== null && (
            <div>
              <span>CURRENT MASTERY</span>
              <strong>
                {Number(mastery).toFixed(0)}%
              </strong>
            </div>
          )}

          <div>
            <span>DIFFICULTY</span>
            <strong>
              {question.difficulty || 'adaptive'}
            </strong>
          </div>
        </div>

        <div className="quiz-question-card">
          <p className="question-number">
            QUESTION {current + 1}
          </p>

          <h2>{question.question}</h2>

          <div className="quiz-options">
            {question.options.map((option, index) => (
              <button
                key={`${question.id}-${index}`}
                className={
                  selected === index
                    ? 'quiz-option selected'
                    : 'quiz-option'
                }
                onClick={() => setSelected(index)}
                disabled={submitting}
              >
                <span>
                  {String.fromCharCode(65 + index)}
                </span>

                <strong>{option}</strong>
              </button>
            ))}
          </div>

          <div className="quiz-footer">
            <small>
              {question.adaptive_reason ===
              'LOW_MASTERY'
                ? '🎯 Targeted because this competency has low mastery.'
                : 'PaperScope selected this question from your competency profile.'}
            </small>

            <button
              className="primary-button"
              disabled={
                selected === null || submitting
              }
              onClick={submitAnswer}
            >
              {submitting
                ? 'Evaluating...'
                : current + 1 === questions.length
                  ? 'Submit Assessment →'
                  : 'Next Question →'}
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}

export default Quiz
