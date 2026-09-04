import { useEffect, useRef, useState } from 'react'
import './Dashboard.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function Dashboard() {
  const fileInputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [materialType, setMaterialType] = useState('auto')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState('')

  // PYQ Intelligence
  const pyqInputRef = useRef(null)
  const [pyqFiles, setPyqFiles] = useState([])
  const [pyqLoading, setPyqLoading] = useState(false)
  const [pyqAnalysis, setPyqAnalysis] = useState(null)
  const [pyqError, setPyqError] = useState('')

  // Smart Calendar
  const [calendarDate, setCalendarDate] = useState(new Date())
  const [calendarTasks, setCalendarTasks] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem('paperscope_calendar_tasks') || '[]'
      )
    } catch {
      return []
    }
  })
  const [calendarModal, setCalendarModal] = useState(false)
  const [calendarTask, setCalendarTask] = useState({
    title: '',
    date: new Date().toISOString().slice(0, 10),
    start_time: '09:00',
    duration_minutes: 60,
    priority: 'medium',
    category: 'study',
    description: '',
  })
  const [calendarLoading, setCalendarLoading] = useState(false)
  const [calendarMessage, setCalendarMessage] = useState('')

  // Where You Stand
  const [whereYouStand, setWhereYouStand] = useState(null)
  const [whereYouStandLoading, setWhereYouStandLoading] = useState(false)
  const [whereYouStandError, setWhereYouStandError] = useState('')

  const generateWhereYouStand = async () => {
    if (!analysis?.assessment) {
      setWhereYouStandError(
        'Complete a PaperScope assessment to calculate your current standing.'
      )
      return
    }

    setWhereYouStandLoading(true)
    setWhereYouStandError('')

    try {
      const response = await fetch(
        `${API}/api/where-you-stand/from-analysis`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            exam_name:
              analysis?.material?.title ||
              'PaperScope Assessment',
            assessment: analysis.assessment,
            competency:
              analysis?.competency || {},
          }),
        }
      )

      if (!response.ok) {
        throw new Error(
          'Unable to calculate your current standing.'
        )
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error(
          'Where You Stand analysis failed.'
        )
      }

      setWhereYouStand(result)

      localStorage.setItem(
        'paperscope_where_you_stand',
        JSON.stringify(result)
      )
    } catch (err) {
      setWhereYouStandError(
        err.message ||
        'Unable to connect to Where You Stand Intelligence.'
      )
    } finally {
      setWhereYouStandLoading(false)
    }
  }

  useEffect(() => {
    try {
      const saved = localStorage.getItem(
        'paperscope_where_you_stand'
      )

      if (saved) {
        setWhereYouStand(JSON.parse(saved))
      }
    } catch {
      // Ignore invalid saved analysis.
    }
  }, [])


  const saveCalendarTasks = (tasks) => {
    setCalendarTasks(tasks)
    localStorage.setItem(
      'paperscope_calendar_tasks',
      JSON.stringify(tasks)
    )
  }

  const addCalendarTask = async () => {
    if (!calendarTask.title.trim()) {
      setCalendarMessage('Enter a task title.')
      return
    }

    setCalendarLoading(true)
    setCalendarMessage('')

    try {
      const response = await fetch(`${API}/api/calendar/task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(calendarTask),
      })

      if (!response.ok) {
        throw new Error('Unable to create calendar task.')
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error(result.detail || 'Task creation failed.')
      }

      saveCalendarTasks([
        ...calendarTasks,
        result.task,
      ])

      setCalendarModal(false)

      setCalendarTask({
        title: '',
        date: new Date().toISOString().slice(0, 10),
        start_time: '09:00',
        duration_minutes: 60,
        priority: 'medium',
        category: 'study',
        description: '',
      })

      setCalendarMessage('Task added to your study calendar.')
    } catch (err) {
      setCalendarMessage(
        err.message || 'Unable to connect to PaperScope Calendar.'
      )
    } finally {
      setCalendarLoading(false)
    }
  }

  const toggleCalendarTask = (taskId) => {
    const updated = calendarTasks.map((task) =>
      task.id === taskId
        ? { ...task, completed: !task.completed }
        : task
    )

    saveCalendarTasks(updated)
  }

  const deleteCalendarTask = (taskId) => {
    saveCalendarTasks(
      calendarTasks.filter((task) => task.id !== taskId)
    )
  }

  const generateAICalendar = async () => {
    setCalendarLoading(true)
    setCalendarMessage('Generating personalized study plan...')

    try {
      const response = await fetch(`${API}/api/calendar/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          competency_gaps:
            analysis?.competency?.competency_gaps || {},
          pyq_analysis:
            pyqAnalysis || {},
          exam_date: null,
          where_you_stand:
            whereYouStand || {},
        }),
      })

      if (!response.ok) {
        throw new Error('AI calendar generation failed.')
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error('AI calendar generation failed.')
      }

      const existingKeys = new Set(
        calendarTasks.map(
          (task) => `${task.date}|${task.title}`
        )
      )

      const newTasks = (result.tasks || []).filter(
        (task) =>
          !existingKeys.has(`${task.date}|${task.title}`)
      )

      saveCalendarTasks([
        ...calendarTasks,
        ...newTasks,
      ])

      setCalendarMessage(
        `${newTasks.length} personalized study task(s) added.`
      )
    } catch (err) {
      setCalendarMessage(
        err.message || 'Unable to generate AI study plan.'
      )
    } finally {
      setCalendarLoading(false)
    }
  }

  const calendarYear = calendarDate.getFullYear()
  const calendarMonth = calendarDate.getMonth()

  const calendarMonthName = calendarDate.toLocaleString(
    'en-US',
    { month: 'long' }
  )

  const firstDay = new Date(
    calendarYear,
    calendarMonth,
    1
  ).getDay()

  const daysInMonth = new Date(
    calendarYear,
    calendarMonth + 1,
    0
  ).getDate()

  const calendarCells = []

  for (let i = 0; i < firstDay; i++) {
    calendarCells.push(null)
  }

  for (let day = 1; day <= daysInMonth; day++) {
    calendarCells.push(
      new Date(calendarYear, calendarMonth, day)
    )
  }

  const calendarToday = new Date().toISOString().slice(0, 10)

  const tasksForDate = (date) => {
    if (!date) return []

    const key =
      `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

    return calendarTasks.filter(
      (task) => task.date === key
    )
  }

  const calendarCompleted = calendarTasks.filter(
    (task) => task.completed
  ).length

  const calendarCompletion =
    calendarTasks.length
      ? Math.round(
          (calendarCompleted / calendarTasks.length) * 100
        )
      : 0


  // Restore the active PaperScope learning session.
  // This keeps the analysed material available while navigating.
  useEffect(() => {
    try {
      const saved = localStorage.getItem('paperscope_active_analysis')
      if (saved) {
        setAnalysis(JSON.parse(saved))
      }
    } catch {
      localStorage.removeItem('paperscope_active_analysis')
    }
  }, [])

  const user = JSON.parse(
    localStorage.getItem('paperscopeUser') || 'null'
  )

  const name = user?.name || 'Learner'

  const go = (path) => {
    window.location.href = path
  }

  const analyseMaterial = async () => {
    if (!selectedFile) {
      await loadDemoAnalysis()
      return
    }

    setLoading(true)
    setError('')

    try {
      // Send the actual file to PaperScope Material Intelligence.
      // The backend extracts PDF/DOCX/PPTX/TXT correctly.
      const formData = new FormData()
      formData.append('file', selectedFile)

      // Send the actual file to Material Intelligence first.
      const materialResponse = await fetch(`${API}/api/material/analyze`, {
        method: 'POST',
        body: formData,
      })

      if (!materialResponse.ok) {
        const message = await materialResponse.text()
        throw new Error(
          message || 'Material analysis unavailable'
        )
      }

      const material = await materialResponse.json()

      if (!material.success) {
        throw new Error(
          material.error || 'Unable to analyse material'
        )
      }

      // The pipeline operates on extracted learning-material text.
      const pipelineResponse = await fetch(`${API}/api/pipeline/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: material.text || '',
          questions: [],
          answers: [],
        }),
      })

      if (!pipelineResponse.ok) {
        const message = await pipelineResponse.text()
        throw new Error(
          message || 'PaperScope intelligence pipeline unavailable'
        )
      }

      const pipeline = await pipelineResponse.json()

      if (!pipeline.success) {
        throw new Error(
          pipeline.error || 'PaperScope intelligence pipeline failed'
        )
      }

      // Persist the analysed material for PaperScope Quiz.
      localStorage.setItem(
        'paperscopeMaterialText',
        material.text || ''
      )

      // Keep the complete intelligence result available to every
      // PaperScope learning surface.
      localStorage.setItem(
        'paperscopeAnalysis',
        JSON.stringify(pipeline)
      )

      // Dashboard source of truth:
      // Material → Questions → Assessment → Competency → Adaptive Learning.
      const nextAnalysis = {
        ...pipeline,
        material,
        classification:
          pipeline.material?.classification ||
          material.classification,
        topics:
          pipeline.material?.topics ||
          material.topics ||
          [],
        concept_analysis:
          pipeline.material?.concept_analysis ||
          material.concept_analysis ||
          {},
        key_concepts:
          pipeline.material?.key_concepts ||
          material.key_concepts ||
          [],
        learning_signals:
          pipeline.material?.learning_signals ||
          material.learning_signals ||
          {},
      }

      setAnalysis(nextAnalysis)

      // Keep the active analysis available across dashboard/quiz/
      // recommendation navigation.
      localStorage.setItem(
        'paperscope_active_analysis',
        JSON.stringify(nextAnalysis)
      )

      localStorage.setItem(
        'paperscope_active_material_name',
        selectedFile.name
      )
    } catch (err) {
      setError(
        err.message ||
        'Unable to connect to PaperScope Material Intelligence'
      )
    } finally {
      setLoading(false)
    }
  }

  // ------------------------------------------------------------
  // PYQ Intelligence
  // ------------------------------------------------------------
  const analysePYQs = async () => {
    if (!pyqFiles.length) {
      setPyqError('Select at least one previous-year question paper.')
      return
    }

    setPyqLoading(true)
    setPyqError('')

    try {
      const formData = new FormData()

      pyqFiles.forEach((file) => {
        formData.append('files', file)
      })

      const response = await fetch(`${API}/api/pyq/analyze`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const message = await response.text()
        throw new Error(
          message || 'PYQ Intelligence analysis unavailable'
        )
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error(
          result.error || 'PYQ Intelligence analysis failed'
        )
      }

      setPyqAnalysis(result)

      localStorage.setItem(
        'paperscope_pyq_analysis',
        JSON.stringify(result)
      )
    } catch (err) {
      setPyqError(
        err.message ||
        'Unable to connect to PaperScope PYQ Intelligence'
      )
    } finally {
      setPyqLoading(false)
    }
  }

  const pyqRepeatedQuestions =
    pyqAnalysis?.repeated_questions || []

  const pyqConceptStats =
    pyqAnalysis?.concept_analysis ||
    []

  const pyqPredictions =
    pyqAnalysis?.prediction?.predicted_questions ||
    []

  const materialData = analysis?.material || analysis || {}
  const topics = analysis?.topics || materialData?.topics || []
  const concepts =
    analysis?.concept_analysis?.concepts ||
    materialData?.concept_analysis?.concepts ||
    []
  const classification =
    analysis?.classification ||
    materialData?.classification ||
    {}

  const detectedMaterialType =
    classification?.material_type || 'general'

  const estimatedComplexity =
    materialData?.material?.estimated_complexity ||
    materialData?.estimated_complexity ||
    'unknown'

  const totalConceptWeightage = concepts.reduce(
    (sum, item) => sum + Number(item.weightage || 0),
    0
  )

  const topConcepts = [...concepts]
    .sort(
      (a, b) =>
        Number(b.weightage || b.importance || 0) -
        Number(a.weightage || a.importance || 0)
    )
    .slice(0, 4)

  const topicCount = topics.length
  const conceptCount =
    analysis?.key_concepts?.length ||
    materialData?.key_concepts?.length ||
    concepts.length

  // ------------------------------------------------------------
  // Dynamic competency distribution
  // ------------------------------------------------------------
  const competencyItems =
    analysis?.competencies ||
    analysis?.assessment?.competencies ||
    materialData?.competencies ||
    []

  const strongCount = competencyItems.filter(
    (item) =>
      String(item.level || '').toLowerCase() === 'strong' ||
      Number(item.accuracy || item.score || 0) >= 75
  ).length

  const developingCount = competencyItems.filter(
    (item) => {
      const score = Number(item.accuracy || item.score || 0)
      return (
        String(item.level || '').toLowerCase() === 'developing' ||
        (score >= 50 && score < 75)
      )
    }
  ).length

  const gapCount = competencyItems.filter(
    (item) => {
      const score = Number(item.accuracy || item.score || 0)
      return (
        String(item.level || '').toLowerCase() === 'weak' ||
        score < 50
      )
    }
  ).length

  const competencyTotal =
    strongCount + developingCount + gapCount

  const strongPct = competencyTotal
    ? Math.round((strongCount / competencyTotal) * 100)
    : 0

  const developingPct = competencyTotal
    ? Math.round((developingCount / competencyTotal) * 100)
    : 0

  const gapPct = competencyTotal
    ? Math.max(0, 100 - strongPct - developingPct)
    : 0

  const overallAccuracy =
    Number(
      analysis?.assessment?.accuracy ??
      analysis?.overall_accuracy ??
      materialData?.assessment?.accuracy ??
      0
    )

  const readiness =
    analysis?.assessment?.readiness || 'NOT ASSESSED'

  const assessmentAccuracy =
    analysis?.assessment?.accuracy

  const hasAssessment =
    typeof assessmentAccuracy === 'number'

  const competencyGapItems =
    analysis?.competency?.competency_gaps ||
    analysis?.competency?.competencies ||
    []

  const difficulty =
    analysis?.assessment?.difficulty_distribution || {}

  // ------------------------------------------------------------
  // Adaptive Intelligence
  // ------------------------------------------------------------
  const adaptive =
    analysis?.adaptive_learning || {}

  const adaptivePriorities =
    adaptive?.topic_priorities || []

  const adaptiveFocus =
    adaptive?.focus_topic || 'Complete assessment'

  const adaptiveDifficulty =
    adaptive?.recommended_difficulty || 'medium'

  const adaptiveMode =
    adaptive?.learning_mode || 'improvement'

  const difficultyEntries = [
    ['Easy', Number(difficulty.easy || 0)],
    ['Medium', Number(difficulty.medium || 0)],
    ['Hard', Number(difficulty.hard || 0)],
  ]

  return (
    <main className="dashboard-page">

      <nav className="dashboard-nav">
        <div className="dashboard-brand">
          <span className="brand-logo">P</span>
          <span>PaperScope</span>
        </div>

        <div className="dashboard-nav-right">
          <span className="dashboard-status">
            AI-POWERED COMPETENCY INTELLIGENCE
          </span>

          <button
            onClick={() => {
              localStorage.removeItem('paperscopeLoggedIn')
              localStorage.removeItem('paperscopeUser')
              window.location.href = '/'
            }}
          >
            Logout
          </button>
        </div>
      </nav>

      <section className="dashboard-content">

        <header className="dashboard-welcome">
          <p className="dashboard-eyebrow">
            PAPERSCOPE LEARNING INTELLIGENCE
          </p>

          <h1>Welcome, {name}.</h1>

          <div className="learning-profile">
            <span>LEARNING PROFILE</span>
            <strong>
              Official Statistics &amp; Data Analyst
            </strong>
          </div>
        </header>

        <section className="upload-section">

          <div className="section-heading">
            <div>
              <p className="section-label">LEARNING MATERIAL</p>
              <h2>Upload Learning Material</h2>
            </div>
          </div>

          <div className="upload-workspace">

            <div className="upload-box">

              <div className="upload-icon">+</div>

              <h3>Drop your learning material here</h3>

              <p>
                Upload notes, lectures, PDFs, presentations or question
                papers for PaperScope to understand.
              </p>

              <input
                ref={fileInputRef}
                type="file"
                className="hidden-file-input"
                accept=".pdf,.doc,.docx,.txt,.ppt,.pptx,.jpeg,.jpg,.png"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    setSelectedFile(file)
                    setAnalysis(null)
                    setError('')
                  }
                }}
              />

              <button
                className="upload-button"
                type="button"
                onClick={() => fileInputRef.current?.click()}
              >
                Choose Material
              </button>

              {selectedFile && (
                <div className="selected-file">
                  <strong>Selected:</strong> {selectedFile.name}
                </div>
              )}

              <button
                className="red-button analyse-button"
                type="button"
                onClick={analyseMaterial}
                disabled={loading}
              >
                {loading
                  ? 'PaperScope is analysing...'
                  : 'Analyse with PaperScope →'}
              </button>

              <small>
                Supported: PDF, DOC, DOCX, TXT, PPT, PPTX, JPEG, JPG, PNG
              </small>

            </div>

            <aside className="material-type-panel">

              <p className="material-type-label">
                MATERIAL CONTEXT
              </p>

              <h3>What are you uploading?</h3>

              <p className="material-type-description">
                Tell PaperScope what this material is so it can apply
                the most relevant intelligence.
              </p>

              <div className="material-type-options">

                {[
                  {
                    value: 'pyq',
                    title: 'PYQ',
                    description: 'Previous year questions & exam trends',
                  },
                  {
                    value: 'question_bank',
                    title: 'Question Bank',
                    description: 'Practice questions & difficulty',
                  },
                  {
                    value: 'notes',
                    title: 'Notes',
                    description: 'Concepts, gaps & MCQ generation',
                  },
                  {
                    value: 'lecture',
                    title: 'Lecture',
                    description: 'Learning objectives & revision',
                  },
                  {
                    value: 'other',
                    title: 'Other',
                    description: 'Let PaperScope determine the context',
                  },
                ].map((item) => (
                  <label
                    key={item.value}
                    className={
                      materialType === item.value ? 'active' : ''
                    }
                  >
                    <input
                      type="radio"
                      name="materialType"
                      value={item.value}
                      checked={materialType === item.value}
                      onChange={(e) => setMaterialType(e.target.value)}
                    />

                    <span>
                      <strong>{item.title}</strong>
                      <small>{item.description}</small>
                    </span>
                  </label>
                ))}

              </div>

            </aside>

          </div>

          {error && (
            <div className="analysis-statement error-box">
              {error}
            </div>
          )}

          {!analysis && !error && (
            <div className="analysis-statement">
              <strong>
                PaperScope analyses concepts, competencies, difficulty,
                importance, competency gaps and learning requirements.
              </strong>
            </div>
          )}

        </section>

        {/* ============================================================
            PYQ INTELLIGENCE
            ============================================================ */}
        <section className="pyq-intelligence-section">

          <div className="section-heading">
            <div>
              <p className="section-label">EXAM INTELLIGENCE</p>
              <h2>Multi-Year PYQ Intelligence</h2>
              <p>
                Upload previous-year papers and let PaperScope discover
                repeated questions, concept frequency, trends and
                high-priority topics.
              </p>
            </div>

            {pyqAnalysis && (
              <div className="pyq-engine-badge">
                PAPERSCOPE PYQ ENGINE
              </div>
            )}
          </div>

          <div className="pyq-upload-panel">

            <div className="pyq-upload-main">

              <input
                ref={pyqInputRef}
                type="file"
                className="hidden-file-input"
                multiple
                accept=".pdf,.doc,.docx,.txt,.ppt,.pptx"
                onChange={(e) => {
                  const files = Array.from(e.target.files || [])
                  setPyqFiles(files)
                  setPyqAnalysis(null)
                  setPyqError('')
                }}
              />

              <div className="pyq-upload-icon">↗</div>

              <h3>Upload Previous-Year Papers</h3>

              <p>
                Select multiple papers such as 2023, 2024 and 2025.
                PaperScope automatically detects the year from the
                filename or document.
              </p>

              <button
                className="outline-button"
                type="button"
                onClick={() => pyqInputRef.current?.click()}
              >
                Choose PYQ Papers
              </button>

              {pyqFiles.length > 0 && (
                <div className="pyq-file-list">
                  {pyqFiles.map((file) => (
                    <div key={`${file.name}-${file.size}`}>
                      <span>PDF</span>
                      <strong>{file.name}</strong>
                    </div>
                  ))}
                </div>
              )}

              <button
                className="red-button"
                type="button"
                onClick={analysePYQs}
                disabled={pyqLoading}
              >
                {pyqLoading
                  ? 'PaperScope is discovering exam trends...'
                  : 'Analyse PYQ Intelligence →'}
              </button>

              {pyqError && (
                <div className="analysis-statement error-box">
                  {pyqError}
                </div>
              )}

            </div>

            <div className="pyq-feature-list">

              <div>
                <span>01</span>
                <strong>Repeated Questions</strong>
                <p>Identify questions appearing across multiple years.</p>
              </div>

              <div>
                <span>02</span>
                <strong>Concept Frequency</strong>
                <p>Measure which concepts dominate the examination.</p>
              </div>

              <div>
                <span>03</span>
                <strong>Trend Intelligence</strong>
                <p>Detect increasing, stable and declining concepts.</p>
              </div>

              <div>
                <span>04</span>
                <strong>Predicted Priorities</strong>
                <p>Surface high-priority topics for focused preparation.</p>
              </div>

            </div>

          </div>

          {pyqAnalysis && (
            <div className="pyq-results">

              <div className="pyq-stat-grid">

                <article>
                  <span>PAPERS ANALYSED</span>
                  <strong>
                    {pyqAnalysis.documents_analyzed ?? 0}
                  </strong>
                </article>

                <article>
                  <span>TOTAL QUESTIONS</span>
                  <strong>
                    {pyqAnalysis.total_questions ?? 0}
                  </strong>
                </article>

                <article>
                  <span>YEARS DETECTED</span>
                  <strong>
                    {pyqAnalysis.years?.length ?? 0}
                  </strong>
                </article>

                <article>
                  <span>REPEATED QUESTIONS</span>
                  <strong>
                    {pyqRepeatedQuestions.length}
                  </strong>
                </article>

              </div>

              <div className="pyq-results-grid">

                <article className="pyq-result-card">

                  <p className="section-label">
                    YEAR-WISE COVERAGE
                  </p>

                  <h3>Question distribution</h3>

                  <div className="pyq-year-list">
                    {Object.entries(
                      pyqAnalysis.year_wise_question_count || {}
                    ).map(([year, count]) => (
                      <div key={year}>
                        <strong>{year}</strong>
                        <div>
                          <i
                            style={{
                              width: `${Math.min(
                                100,
                                Number(count) * 10
                              )}%`
                            }}
                          />
                        </div>
                        <span>{count} questions</span>
                      </div>
                    ))}
                  </div>

                </article>

                <article className="pyq-result-card">

                  <p className="section-label">
                    REPEATED QUESTIONS
                  </p>

                  <h3>What keeps appearing?</h3>

                  {pyqRepeatedQuestions.length > 0 ? (
                    <div className="pyq-repeat-list">
                      {pyqRepeatedQuestions
                        .slice(0, 6)
                        .map((item, index) => {
                          const question =
                            item.question ||
                            item.text ||
                            item.question_text ||
                            'Repeated question'

                          const count =
                            item.count ||
                            item.frequency ||
                            item.occurrences ||
                            item.years?.length ||
                            0

                          return (
                            <div key={`${question}-${index}`}>
                              <span>
                                {String(index + 1).padStart(2, '0')}
                              </span>

                              <strong>{question}</strong>

                              <small>
                                Appeared {count} time
                                {Number(count) === 1 ? '' : 's'}
                              </small>
                            </div>
                          )
                        })}
                    </div>
                  ) : (
                    <p className="pyq-empty">
                      No repeated questions were detected.
                    </p>
                  )}

                </article>

              </div>

              <div className="pyq-results-grid">

                <article className="pyq-result-card">

                  <p className="section-label">
                    CONCEPT INTELLIGENCE
                  </p>

                  <h3>High-frequency concepts</h3>

                  {pyqConceptStats.length > 0 ? (
                    <div className="pyq-concept-list">
                      {pyqConceptStats
                        .slice(0, 8)
                        .map((item, index) => {
                          const name =
                            item.concept ||
                            item.name ||
                            item.topic ||
                            `Concept ${index + 1}`

                          const importance = Number(
                            item.importance ??
                            item.importance_score ??
                            item.score ??
                            0
                          )

                          const frequency = Number(
                            item.total ??
                            item.frequency ??
                            item.count ??
                            item.appearances ??
                            0
                          )

                          return (
                            <div key={`${name}-${index}`}>
                              <div>
                                <strong>{name}</strong>
                                <span>
                                  {frequency} appearance
                                  {frequency === 1 ? '' : 's'}
                                </span>
                              </div>

                              <div className="pyq-bar">
                                <i
                                  style={{
                                    width: `${Math.min(
                                      100,
                                      Math.max(0, importance)
                                    )}%`
                                  }}
                                />
                              </div>

                              <small>
                                Importance {Math.round(importance)}%
                              </small>
                            </div>
                          )
                        })}
                    </div>
                  ) : (
                    <p className="pyq-empty">
                      Concept statistics will appear here after analysis.
                    </p>
                  )}

                </article>

                <article className="pyq-result-card">

                  <p className="section-label">
                    PREDICTIVE INTELLIGENCE
                  </p>

                  <h3>Predicted important areas</h3>

                  {pyqPredictions.length > 0 ? (
                    <div className="pyq-prediction-list">
                      {pyqPredictions
                        .slice(0, 6)
                        .map((item, index) => {
                          const topic =
                            item.topic ||
                            item.concept ||
                            item.name ||
                            `Priority ${index + 1}`

                          const confidence =
                            item.confidence ||
                            item.level ||
                            'MEDIUM'

                          const importance = Number(
                            item.importance ??
                            item.score ??
                            item.importance_score ??
                            0
                          )

                          return (
                            <div key={`${topic}-${index}`}>
                              <div className="prediction-heading">
                                <span>
                                  {String(index + 1).padStart(2, '0')}
                                </span>

                                <strong>{topic}</strong>

                                <em>
                                  {String(confidence).toUpperCase()}
                                </em>
                              </div>

                              <p>
                                Importance score: {Math.round(importance)}%
                              </p>
                            </div>
                          )
                        })}
                    </div>
                  ) : (
                    <p className="pyq-empty">
                      PaperScope needs multi-year question data to
                      generate predicted priorities.
                    </p>
                  )}

                </article>

              </div>

              <div className="pyq-insight-banner">

                <div>
                  <span>EXAM INTELLIGENCE</span>
                  <strong>
                    {pyqRepeatedQuestions.length > 0
                      ? `${pyqRepeatedQuestions.length} recurring question patterns detected`
                      : 'PaperScope has completed the PYQ scan'}
                  </strong>
                </div>

                <p>
                  Use repeated questions and high-frequency concepts
                  as evidence-based preparation priorities rather than
                  studying every topic equally.
                </p>

              </div>

            </div>
          )}

        </section>

        
{pyqAnalysis?.prediction?.predicted_questions?.length > 0 && (
  <section className="pyq-intelligence-section">
    <div className="pyq-section-heading">
      <div>
        <span className="pyq-engine-badge">PREDICTIVE INTELLIGENCE</span>
        <h2>AI Predicted Paper</h2>
        <p>
          Evidence-based questions ranked using recurrence, historical coverage,
          concept importance and trend signals.
        </p>
      </div>
    </div>

    <div className="pyq-prediction-list">
      {pyqAnalysis.prediction.predicted_questions.map((item, index) => (
        <div className="pyq-prediction-card" key={index}>
          <div className="prediction-topline">
            <span className="prediction-rank">#{index + 1}</span>
            <span className="prediction-confidence">
              {item.confidence || "Medium"} confidence
            </span>
            <span className="prediction-score">
              {item.prediction_score ?? 0}/100
            </span>
          </div>

          <h3>
            {item.predicted_question || item.question || "Predicted question"}
          </h3>

          <div className="prediction-meta">
            <span>Concept: {item.concept || "General"}</span>
            <span>Difficulty: {item.difficulty || "Moderate"}</span>
            <span>Type: {item.question_type || "Conceptual"}</span>
          </div>

          <div className="prediction-evidence">
            <strong>Evidence:</strong>{" "}
            {item.evidence_occurrences || 0} occurrence(s)
            {item.evidence_years?.length
              ? ` across ${item.evidence_years.join(", ")}`
              : ""}
          </div>

          {item.reason && (
            <p className="prediction-reason">
              {item.reason}
            </p>
          )}
        </div>
      ))}
    </div>
  </section>
)}

{pyqAnalysis?.revision_notes?.notes?.length > 0 && (
  <section className="pyq-intelligence-section">
    <div className="pyq-section-heading">
      <div>
        <span className="pyq-engine-badge">AI STUDY INTELLIGENCE</span>
        <h2>AI Revision Notes</h2>
        <p>
          Personalized revision priorities generated from historical
          question frequency, recurrence and trends.
        </p>
      </div>
    </div>

    <div className="pyq-concept-list">
      {pyqAnalysis.revision_notes.notes.map((note, index) => (
        <div className="pyq-revision-card" key={index}>
          <div className="revision-card-top">
            <div>
              <span className="revision-priority">
                {note.priority}
              </span>
              <h3>{note.concept}</h3>
            </div>

            <div className="revision-score">
              <strong>{note.importance_score}</strong>
              <span>importance</span>
            </div>
          </div>

          <div className="revision-stats">
            <span>
              <strong>{note.question_frequency}</strong> questions
            </span>
            <span>
              <strong>{note.years_appeared}</strong> years
            </span>
            <span>
              Trend: <strong>{note.trend}</strong>
            </span>
          </div>

          <p className="revision-focus">
            {note.study_focus}
          </p>

          <p className="revision-evidence">
            <strong>Evidence:</strong> {note.evidence}
          </p>

          <div className="revision-note-box">
            {note.revision_note}
          </div>
        </div>
      ))}
    </div>
  </section>
)}


<section className="smart-calendar-section">
  <div className="calendar-header">
    <div>
      <span className="pyq-engine-badge">PERSONALIZED PLANNING</span>
      <h2>Smart Study Calendar</h2>
      <p>
        Turn PaperScope intelligence into a structured daily learning plan.
      </p>
    </div>

    <div className="calendar-actions">
      <button
        className="calendar-secondary-btn"
        onClick={() => {
          const now = new Date()
          setCalendarDate(now)
        }}
      >
        Today
      </button>

      <button
        className="calendar-ai-btn"
        onClick={generateAICalendar}
        disabled={calendarLoading}
      >
        {calendarLoading ? 'Generating...' : 'Generate AI Plan'}
      </button>

      <button
        className="calendar-add-btn"
        onClick={() => setCalendarModal(true)}
      >
        + Add Task
      </button>
    </div>
  </div>

  <div className="calendar-dashboard-stats">
    <div>
      <strong>{calendarTasks.length}</strong>
      <span>Total Tasks</span>
    </div>

    <div>
      <strong>{calendarCompleted}</strong>
      <span>Completed</span>
    </div>

    <div>
      <strong>{calendarTasks.length - calendarCompleted}</strong>
      <span>Pending</span>
    </div>

    <div>
      <strong>{calendarCompletion}%</strong>
      <span>Progress</span>
    </div>
  </div>

  {calendarMessage && (
    <div className="calendar-message">
      {calendarMessage}
    </div>
  )}

  <div className="calendar-shell">

    <div className="calendar-navigation">
      <button
        onClick={() =>
          setCalendarDate(
            new Date(calendarYear, calendarMonth - 1, 1)
          )
        }
      >
        ‹
      </button>

      <h3>
        {calendarMonthName} {calendarYear}
      </h3>

      <button
        onClick={() =>
          setCalendarDate(
            new Date(calendarYear, calendarMonth + 1, 1)
          )
        }
      >
        ›
      </button>
    </div>

    <div className="calendar-weekdays">
      {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(
        (day) => (
          <div key={day}>{day}</div>
        )
      )}
    </div>

    <div className="calendar-grid">
      {calendarCells.map((date, index) => {
        if (!date) {
          return (
            <div
              className="calendar-day empty"
              key={`empty-${index}`}
            />
          )
        }

        const dateKey =
          `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

        const dayTasks = tasksForDate(date)

        return (
          <div
            className={`calendar-day ${
              dateKey === calendarToday ? 'calendar-today' : ''
            }`}
            key={dateKey}
          >
            <div className="calendar-day-number">
              {date.getDate()}
            </div>

            <div className="calendar-day-tasks">
              {dayTasks.slice(0, 3).map((task) => (
                <div
                  className={`calendar-task ${
                    task.completed ? 'completed' : ''
                  }`}
                  key={task.id}
                  title={task.description || task.title}
                >
                  <button
                    className="calendar-task-check"
                    onClick={() =>
                      toggleCalendarTask(task.id)
                    }
                  >
                    {task.completed ? '✓' : '○'}
                  </button>

                  <span>
                    {task.start_time
                      ? `${task.start_time} `
                      : ''}
                    {task.title}
                  </span>
                </div>
              ))}

              {dayTasks.length > 3 && (
                <div className="calendar-more">
                  +{dayTasks.length - 3} more
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  </div>

  {calendarTasks.length > 0 && (
    <div className="calendar-task-list">
      <div className="calendar-list-heading">
        <h3>Upcoming Study Tasks</h3>
        <span>{calendarTasks.length} scheduled</span>
      </div>

      {calendarTasks
        .slice()
        .sort((a, b) =>
          `${a.date}${a.start_time || ''}`.localeCompare(
            `${b.date}${b.start_time || ''}`
          )
        )
        .slice(0, 8)
        .map((task) => (
          <div
            className={`calendar-list-task ${
              task.completed ? 'completed' : ''
            }`}
            key={task.id}
          >
            <button
              className="calendar-task-check large"
              onClick={() =>
                toggleCalendarTask(task.id)
              }
            >
              {task.completed ? '✓' : '○'}
            </button>

            <div className="calendar-list-main">
              <strong>{task.title}</strong>

              <span>
                {task.date}
                {task.start_time
                  ? ` · ${task.start_time}`
                  : ''}
                {' · '}
                {task.duration_minutes} min
              </span>
            </div>

            <span className="calendar-priority">
              {task.priority.replace('_', ' ')}
            </span>

            <button
              className="calendar-delete"
              onClick={() =>
                deleteCalendarTask(task.id)
              }
              aria-label="Delete task"
            >
              ×
            </button>
          </div>
        ))}
    </div>
  )}

  {calendarModal && (
    <div
      className="calendar-modal-backdrop"
      onClick={() => setCalendarModal(false)}
    >
      <div
        className="calendar-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="calendar-modal-heading">
          <div>
            <span className="pyq-engine-badge">NEW TASK</span>
            <h3>Add Study Task</h3>
          </div>

          <button
            onClick={() => setCalendarModal(false)}
          >
            ×
          </button>
        </div>

        <label>
          Task
          <input
            value={calendarTask.title}
            onChange={(e) =>
              setCalendarTask({
                ...calendarTask,
                title: e.target.value,
              })
            }
            placeholder="e.g. Revise Probability"
          />
        </label>

        <div className="calendar-form-row">
          <label>
            Date
            <input
              type="date"
              value={calendarTask.date}
              onChange={(e) =>
                setCalendarTask({
                  ...calendarTask,
                  date: e.target.value,
                })
              }
            />
          </label>

          <label>
            Start time
            <input
              type="time"
              value={calendarTask.start_time}
              onChange={(e) =>
                setCalendarTask({
                  ...calendarTask,
                  start_time: e.target.value,
                })
              }
            />
          </label>
        </div>

        <div className="calendar-form-row">
          <label>
            Duration
            <select
              value={calendarTask.duration_minutes}
              onChange={(e) =>
                setCalendarTask({
                  ...calendarTask,
                  duration_minutes: Number(e.target.value),
                })
              }
            >
              <option value={30}>30 minutes</option>
              <option value={45}>45 minutes</option>
              <option value={60}>1 hour</option>
              <option value={90}>1.5 hours</option>
              <option value={120}>2 hours</option>
            </select>
          </label>

          <label>
            Priority
            <select
              value={calendarTask.priority}
              onChange={(e) =>
                setCalendarTask({
                  ...calendarTask,
                  priority: e.target.value,
                })
              }
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="must_study">Must Study</option>
            </select>
          </label>
        </div>

        <label>
          Category
          <select
            value={calendarTask.category}
            onChange={(e) =>
              setCalendarTask({
                ...calendarTask,
                category: e.target.value,
              })
            }
          >
            <option value="study">Study</option>
            <option value="pyq_revision">PYQ Revision</option>
            <option value="competency">Competency</option>
            <option value="quiz">Quiz</option>
            <option value="exam">Exam</option>
          </select>
        </label>

        <label>
          Notes
          <textarea
            value={calendarTask.description}
            onChange={(e) =>
              setCalendarTask({
                ...calendarTask,
                description: e.target.value,
              })
            }
            placeholder="What should you focus on?"
            rows="3"
          />
        </label>

        <button
          className="calendar-save-btn"
          onClick={addCalendarTask}
          disabled={calendarLoading}
        >
          {calendarLoading ? 'Saving...' : 'Add to Calendar'}
        </button>

        {calendarMessage && (
          <p className="calendar-modal-message">
            {calendarMessage}
          </p>
        )}
      </div>
    </div>
  )}
</section>


{analysis && (
  <section className="where-you-stand-section">
    <div className="where-you-stand-header">
      <div>
        <span className="pyq-engine-badge">EXAM INTELLIGENCE</span>
        <h2>Where You Stand</h2>
        <p>
          Understand your current position, identify your biggest gaps,
          and see how far you can progress.
        </p>
      </div>

      <button
        className="where-you-stand-btn"
        onClick={generateWhereYouStand}
        disabled={whereYouStandLoading}
      >
        {whereYouStandLoading
          ? 'Analysing...'
          : 'Analyse My Standing'}
      </button>
    </div>

    {whereYouStandError && (
      <div className="where-you-stand-error">
        {whereYouStandError}
      </div>
    )}

    {whereYouStand && (
      <>
        <div className="where-standing-hero-grid">

          <div className="where-standing-main-card">
            <span>YOUR CURRENT STANDING</span>

            <div className="where-standing-score">
              {whereYouStand.current_standing.percentage}%
            </div>

            <strong>
              {whereYouStand.current_standing.standing.replace('_', ' ')}
            </strong>

            <div className="where-standing-progress">
              <div
                style={{
                  width:
                    `${whereYouStand.current_standing.percentage}%`,
                }}
              />
            </div>

            <p>
              {whereYouStand.summary.message}
            </p>
          </div>

          <div className="where-standing-target-card">

            <div>
              <span>TARGET</span>
              <strong>
                {whereYouStand.target_analysis.target_percentage}%
              </strong>
            </div>

            <div className="where-standing-gap">
              <span>IMPROVEMENT NEEDED</span>
              <strong>
                +{whereYouStand.target_analysis.improvement_percentage_points}%
              </strong>
            </div>

            <div className="where-standing-target-status">
              {whereYouStand.target_analysis.target_status === 'achieved'
                ? 'Target achieved'
                : 'Target in progress'}
            </div>

          </div>
        </div>

        <div className="where-standing-stats">

          <div>
            <span>Current Score</span>
            <strong>
              {whereYouStand.current_standing.score}
            </strong>
          </div>

          <div>
            <span>Target Score</span>
            <strong>
              {whereYouStand.target_analysis.target_score}
            </strong>
          </div>

          <div>
            <span>Current Level</span>
            <strong>
              {whereYouStand.current_standing.level.replace('_', ' ')}
            </strong>
          </div>

          <div>
            <span>Historical Cutoff</span>
            <strong>
              {whereYouStand.cutoff_analysis
                ? whereYouStand.cutoff_analysis.historical_cutoff
                : 'Not available'}
            </strong>
          </div>

        </div>

        <div className="where-standing-columns">

          <div className="where-standing-panel">
            <div className="where-standing-panel-heading">
              <div>
                <span>INTELLIGENCE</span>
                <h3>What You Should Improve</h3>
              </div>
            </div>

            <div className="where-standing-topic-list">
              {whereYouStand.topic_analysis.priority_topics
                .filter((topic) => topic.gap > 0)
                .slice(0, 5)
                .map((topic) => (
                  <div
                    className="where-standing-topic"
                    key={topic.topic}
                  >
                    <div className="where-standing-topic-top">
                      <strong>{topic.topic}</strong>

                      <span
                        className={`where-priority ${topic.priority}`}
                      >
                        {topic.priority.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="where-standing-topic-bar">
                      <div
                        style={{
                          width: `${topic.accuracy}%`,
                        }}
                      />
                    </div>

                    <div className="where-standing-topic-meta">
                      <span>
                        Current {topic.accuracy}%
                      </span>

                      <span>
                        Gap {topic.gap}%
                      </span>
                    </div>
                  </div>
                ))}

              {whereYouStand.topic_analysis.priority_topics
                .filter((topic) => topic.gap > 0).length === 0 && (
                  <div className="where-standing-empty">
                    No major competency gaps detected.
                  </div>
                )}
            </div>
          </div>

          <div className="where-standing-panel">

            <div className="where-standing-panel-heading">
              <div>
                <span>STRENGTHS</span>
                <h3>Where You're Strong</h3>
              </div>
            </div>

            <div className="where-standing-strength-list">

              {whereYouStand.topic_analysis.strongest_topics
                .slice(0, 3)
                .map((topic) => (
                  <div
                    className="where-standing-strength"
                    key={topic.topic}
                  >
                    <div>
                      <strong>{topic.topic}</strong>
                      <span>{topic.level}</span>
                    </div>

                    <strong>{topic.accuracy}%</strong>
                  </div>
                ))}

            </div>
          </div>

        </div>

        <div className="where-standing-panel where-projection-panel">

          <div className="where-standing-panel-heading">
            <div>
              <span>PROGRESS PROJECTION</span>
              <h3>How Far Can You Reach?</h3>
            </div>
          </div>

          <div className="where-projection-grid">

            {whereYouStand.projections.map((projection) => (
              <div
                className="where-projection-card"
                key={projection.scenario}
              >
                <span>{projection.scenario}</span>

                <strong>
                  {projection.percentage}%
                </strong>
              </div>
            ))}

          </div>
        </div>

        <div className="where-standing-action">

          <div>
            <span>NEXT MOVE</span>

            <h3>
              Turn your gaps into a study plan.
            </h3>

            <p>
              PaperScope can convert your priority areas into
              structured tasks inside Smart Study Calendar.
            </p>
          </div>

          <button
            className="where-calendar-btn"
            onClick={generateAICalendar}
          >
            Build My Improvement Plan →
          </button>

        </div>
      </>
    )}
  </section>
)}

{analysis && (
          <>

            

            <section className="dashboard-actions">

              <button
                className="red-button"
                onClick={() => go('/analysis')}
              >
                View Complete Analysis →
              </button>

              <button
                className="outline-button"
                onClick={() => go('/quiz')}
              >
                Start Adaptive Learning →
              </button>

              <button
                className="outline-button"
                onClick={() => go('/recommended')}
              >
                View Learning Recommendations →
              </button>

            </section>

            <section className="intelligence-grid">

              <article className="intelligence-card">

                <p className="section-label">
                  COMPETENCY INTELLIGENCE
                </p>

                <h2>Competency distribution</h2>

                <div className="donut-wrap">
                  <div
                    className="donut"
                    style={{
                      background: `conic-gradient(
                        #151515 0 ${strongPct}%,
                        #77716a ${strongPct}% ${strongPct + developingPct}%,
                        #d52f27 ${strongPct + developingPct}% 100%
                      )`
                    }}
                  >
                    <div>
                      <strong>{overallAccuracy}%</strong>
                      <span>Overall</span>
                    </div>
                  </div>
                </div>

                <div className="legend">
                  {hasAssessment ? (
                    <>
                      <span>
                        <i className="legend-strong" />
                        Strong · {strongPct}%
                      </span>
                      <span>
                        <i className="legend-developing" />
                        Developing · {developingPct}%
                      </span>
                      <span>
                        <i className="legend-gap" />
                        Needs Improvement · {gapPct}%
                      </span>
                    </>
                  ) : (
                    <>
                      <span>
                        <i className="legend-strong" />
                        Assessment required
                      </span>
                      <span>
                        <i className="legend-developing" />
                        {topicCount} topics detected
                      </span>
                      <span>
                        <i className="legend-gap" />
                        {conceptCount} concepts detected
                      </span>
                    </>
                  )}
                </div>

              </article>

              <article className="intelligence-card">

                <p className="section-label">
                  CONCEPT WEIGHTAGE
                </p>

                <h2>What matters most?</h2>

                <div className="weightage-list">

                  {topConcepts.length > 0 ? (
                    topConcepts.map((item) => {
                      const value = Math.min(
                        100,
                        Math.max(
                          0,
                          Number(item.weightage || item.importance || 0)
                        )
                      )

                      return (
                        <div key={item.concept}>
                          <span>{item.concept}</span>
                          <strong>{value.toFixed(1)}%</strong>
                          <div>
                            <i style={{ width: `${value}%` }} />
                          </div>
                        </div>
                      )
                    })
                  ) : (
                    <div>
                      <span>No concepts detected yet</span>
                      <strong>—</strong>
                      <div><i style={{ width: '0%' }} /></div>
                    </div>
                  )}

                </div>

              </article>

              <article className="intelligence-card">

                <p className="section-label">
                  QUESTION INTELLIGENCE
                </p>

                <h2>Difficulty distribution</h2>

                <div className="difficulty-bars">

                  {difficultyEntries.map(([label, value]) => (
                    <div key={label}>
                      <span>{label}</span>
                      <i style={{ width: `${Math.min(value, 100)}%` }} />
                      <strong>{value ? `${value}%` : '—'}</strong>
                    </div>
                  ))}

                </div>

                <p className="intelligence-note">
                  {hasAssessment
                    ? 'Difficulty is based on the generated assessment.'
                    : `Detected material complexity: ${estimatedComplexity}. Question difficulty will appear after assessment generation.`}
                </p>

              </article>

            </section>

            <section className="competency-section">

              <div className="section-heading">
                <div>
                  <p className="section-label">
                    COMPETENCY INTELLIGENCE
                  </p>

                  <h2>Strengths &amp; competency gaps</h2>
                </div>
              </div>

              <div className="competency-grid">

                {competencyItems.length > 0 ? (
                  competencyItems.map((item, index) => {
                    const score = Number(
                      item.score ??
                      item.accuracy ??
                      item.competency_score ??
                      0
                    )

                    const safeScore = Math.min(
                      100,
                      Math.max(0, score)
                    )

                    const level =
                      safeScore >= 75
                        ? 'STRONG'
                        : safeScore >= 50
                          ? 'DEVELOPING'
                          : 'HIGH PRIORITY GAP'

                    return (
                      <article
                        className={`competency-card ${
                          safeScore >= 75 ? 'strength' : 'gap'
                        }`}
                        key={item.name || item.competency || index}
                      >
                        <span>{level}</span>

                        <h3>
                          {item.name ||
                            item.competency ||
                            item.topic ||
                            `Competency ${index + 1}`}
                        </h3>

                        <div className="progress">
                          <div
                            style={{
                              width: `${safeScore}%`
                            }}
                          />
                        </div>

                        <strong>{Math.round(safeScore)}%</strong>

                        <p>
                          {item.description ||
                            item.message ||
                            'Learner competency identified from assessment data.'}
                        </p>
                      </article>
                    )
                  })
                ) : (
                  <article className="competency-card">
                    <span>NOT ASSESSED</span>
                    <h3>Learner competency</h3>
                    <div className="progress">
                      <div style={{ width: '0%' }} />
                    </div>
                    <strong>—</strong>
                    <p>
                      Complete the generated assessment to let PaperScope
                      measure strengths and competency gaps.
                    </p>
                  </article>
                )}

              </div>

            </section>

            <section className="gap-section">

              <div>
                <p className="section-label">ACTIONABLE INTELLIGENCE</p>
                <h2>What should you improve next?</h2>
                <p>
                  PaperScope converts competency gaps into practical
                  learning actions instead of simply showing a score.
                </p>
              </div>

              <div className="gap-list">

                {adaptivePriorities.length > 0 ? (
                  adaptivePriorities.slice(0, 3).map((item, index) => (
                    <div key={item.topic || index}>
                      <span>{String(index + 1).padStart(2, '0')}</span>

                      <strong>
                        {item.topic || 'Learning competency'}
                      </strong>

                      <p>
                        {item.action || 'Targeted practice recommended.'}
                        {' · '}
                        Next difficulty: {item.next_difficulty || adaptiveDifficulty}
                      </p>
                    </div>
                  ))
                ) : (
                  <div>
                    <span>01</span>
                    <strong>{adaptiveFocus}</strong>
                    <p>
                      Complete the assessment to generate
                      personalized adaptive priorities.
                    </p>
                  </div>
                )}

              </div>

            </section>

            

            <section className="igot-section">

              <div>

                <p className="section-label">
                  IGOT KARMAYOGI INTEGRATION
                </p>

                <h2>
                  From competency gap
                  <br />
                  to the right training.
                </h2>

                <p>
                  PaperScope identifies the capability gap first and then
                  connects the learner with relevant training available
                  through the iGOT Karmayogi ecosystem.
                </p>

              </div>

              <div className="igot-courses">

                <article>
                  <span>HIGH PRIORITY</span>
                  <h3>Data Quality and Statistical Standards</h3>
                  <p>
                    Recommended because Data Quality Assessment is the
                    highest detected competency gap.
                  </p>

                  <a
                    href="https://igotkarmayogi.gov.in/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open iGOT Karmayogi →
                  </a>
                </article>

                <article>
                  <span>FOUNDATION</span>
                  <h3>Understanding Official Statistics</h3>
                  <p>
                    Strengthens foundational understanding and supports
                    professional capacity building.
                  </p>

                  <a
                    href="https://igotkarmayogi.gov.in/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Explore Training →
                  </a>
                </article>

              <div className="sathee-integration">
                <div className="sathee-integration-content">
                  <span className="section-label">
                    GOVERNMENT EXAM PREPARATION
                  </span>

                  <h3>SATHEE</h3>

                  <p>
                    Free exam preparation initiative by the Ministry of
                    Education and IIT Kanpur, supporting JEE, NEET, SSC,
                    CUET and other competitive examinations.
                  </p>

                  <div className="sathee-tags">
                    <span>JEE</span>
                    <span>NEET</span>
                    <span>SSC</span>
                    <span>CUET</span>
                  </div>
                </div>

                <a
                  href="https://sathee.iitk.ac.in/"
                  target="_blank"
                  rel="noreferrer"
                  className="sathee-link"
                >
                  Explore SATHEE →
                </a>
              </div>

            </div>

            </section>

          </>
        )}

      </section>

      <footer className="site-footer">

        <div className="footer-main">

          <div className="footer-brand">
            <div className="footer-logo">
              <span>P</span>
              <strong>PaperScope</strong>
            </div>

            <p>
              AI-powered competency intelligence for personalized
              learning and capacity building.
            </p>
          </div>

          <div className="footer-column">
            <span>EXPLORE</span>
            <button onClick={() => go('/dashboard')}>Dashboard</button>
            <button onClick={() => go('/analysis')}>Analysis</button>
            <button onClick={() => go('/quiz')}>Adaptive Learning</button>
            <button onClick={() => go('/recommended')}>Recommendations</button>
          </div>

          <div className="footer-column">
            <span>LEARNING</span>
            <button onClick={() => go('/plan')}>Personalized Plan</button>
            <a
              href="https://igotkarmayogi.gov.in/"
              target="_blank"
              rel="noreferrer"
            >
              iGOT Karmayogi ↗
            </a>
          </div>

          <div className="footer-column">
            <span>CONTACT</span>
            <a href="mailto:contact@paperscope.in">
              contact@paperscope.in
            </a>
            <small>Smart India Hackathon 2026</small>
          </div>

        </div>

        <div className="sih-footer">
          PAPERSCOPE — AI-POWERED COMPETENCY INTELLIGENCE ·
          SMART INDIA HACKATHON 2026
        </div>

      </footer>

    </main>
  )
}

export default Dashboard
