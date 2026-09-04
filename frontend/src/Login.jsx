import { useState } from 'react'
import './Login.css'

const API_URL = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/api`

function Login() {
  const [mode, setMode] = useState('register')

  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    background: '',
    learningGoal: '',
  })

  const [loginData, setLoginData] = useState({
    email: '',
    pin: '',
  })

  const [generatedPin, setGeneratedPin] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const updateForm = (field, value) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }))
  }

  const register = async (event) => {
    event.preventDefault()
    setMessage('')
    setGeneratedPin('')

    if (
      !form.name ||
      !form.email ||
      !form.phone ||
      !form.background ||
      !form.learningGoal
    ) {
      setMessage('Please complete all fields.')
      return
    }

    const phone = form.phone.replace(/\D/g, '')

    if (phone.length !== 10) {
      setMessage('Please enter a valid 10-digit phone number.')
      return
    }

    try {
      setLoading(true)

      const response = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...form, phone }),
      })

      const data = await response.json()

      if (!response.ok) {
        setMessage(data.detail || 'Registration failed.')
        return
      }

      localStorage.setItem(
        'paperscopeUser',
        JSON.stringify({
          ...data.user,
          pin: data.pin,
        }),
      )

      setGeneratedPin(data.pin)
      setMessage('')
    } catch (error) {
      setMessage(
        'Unable to connect to PaperScope server. Make sure the backend is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  const login = async (event) => {
    event.preventDefault()
    setMessage('')

    if (!loginData.email || !loginData.pin) {
      setMessage('Please enter your email and PIN.')
      return
    }

    try {
      setLoading(true)

      const response = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData),
      })

      const data = await response.json()

      if (!response.ok) {
        setMessage(data.detail || 'Login failed.')
        return
      }

      localStorage.setItem(
        'paperscopeUser',
        JSON.stringify(data.user),
      )

      localStorage.setItem('paperscopeLoggedIn', 'true')

      window.history.pushState({}, '', '/dashboard')
      window.dispatchEvent(new PopStateEvent('popstate'))
    } catch (error) {
      setMessage(
        'Unable to connect to PaperScope server. Make sure the backend is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <button
        className="back-button"
        onClick={() => (window.location.href = '/')}
      >
        ← Back to PaperScope
      </button>

      <section className="login-card">
        <div className="login-heading">
          <p className="login-eyebrow">
            {mode === 'register'
              ? 'START YOUR LEARNING JOURNEY'
              : 'WELCOME BACK'}
          </p>

          <h1>
            {mode === 'register'
              ? 'Build your learning identity.'
              : 'Continue your journey.'}
          </h1>

          <p>
            {mode === 'register'
              ? 'Tell PaperScope how you learn, so your intelligence can be personalized.'
              : 'Enter your registered details to continue.'}
          </p>
        </div>

        {mode === 'register' ? (
          <form onSubmit={register} className="login-form">
            <label>
              Full Name
              <input
                type="text"
                value={form.name}
                onChange={(e) => updateForm('name', e.target.value)}
                placeholder="Your full name"
              />
            </label>

            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={(e) => updateForm('email', e.target.value)}
                placeholder="you@example.com"
              />
            </label>

            <label>
              Phone Number
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => updateForm('phone', e.target.value)}
                placeholder="Your phone number"
              />
            </label>

            <label>
              Current Role / Background
              <input
                type="text"
                value={form.background}
                onChange={(e) =>
                  updateForm('background', e.target.value)
                }
                placeholder="e.g. Government Officer / Student / Analyst"
              />
            </label>

            <label>
              Primary Learning Goal
              <select
                value={form.learningGoal}
                onChange={(e) =>
                  updateForm('learningGoal', e.target.value)
                }
              >
                <option value="">Select your goal</option>
                <option value="Official Statistics & Data">
                  Official Statistics & Data
                </option>
                <option value="Government Capacity Building">
                  Government Capacity Building
                </option>
                <option value="Professional Skill Development">
                  Professional Skill Development
                </option>
                <option value="Academic Learning">
                  Academic Learning
                </option>
                <option value="Self-Paced Learning">
                  Self-Paced Learning
                </option>
                <option value="Other">Other</option>
              </select>
            </label>

            <button
              className="login-submit"
              type="submit"
              disabled={loading}
            >
              {loading ? 'Creating Profile...' : 'Create Learning Profile'}
              {!loading && <span> →</span>}
            </button>
          </form>
        ) : (
          <form onSubmit={login} className="login-form">
            <label>
              Registered Email
              <input
                type="email"
                value={loginData.email}
                onChange={(e) =>
                  setLoginData({
                    ...loginData,
                    email: e.target.value,
                  })
                }
                placeholder="you@example.com"
              />
            </label>

            <label>
              6-Digit PIN
              <input
                type="text"
                inputMode="numeric"
                maxLength="6"
                value={loginData.pin}
                onChange={(e) =>
                  setLoginData({
                    ...loginData,
                    pin: e.target.value.replace(/\D/g, ''),
                  })
                }
                placeholder="Enter your PIN"
              />
            </label>

            <button
              className="login-submit"
              type="submit"
              disabled={loading}
            >
              {loading ? 'Signing In...' : 'Continue to Dashboard'}
              {!loading && <span> →</span>}
            </button>
          </form>
        )}

        {generatedPin && (
          <div className="pin-box">
            <span>Your PaperScope Access PIN</span>
            <strong>{generatedPin}</strong>
            <small>
              Save this PIN to securely access your learning dashboard.
            </small>
          </div>
        )}

        {message && (
          <p className="login-message">
            {message}
          </p>
        )}

        <div className="login-divider">
          <span>OR</span>
        </div>

        <div className="registered-switch">
          {mode === 'register' ? (
            <>
              <span>Already have a learning profile?</span>
              <button
                type="button"
                onClick={() => {
                  setMode('login')
                  setMessage('')
                  setGeneratedPin('')
                }}
              >
                Sign In →
              </button>
            </>
          ) : (
            <>
              <span>New to PaperScope?</span>
              <button
                type="button"
                onClick={() => {
                  setMode('register')
                  setMessage('')
                }}
              >
                Create Profile →
              </button>
            </>
          )}
        </div>
      </section>
    </main>
  )
}

export default Login
