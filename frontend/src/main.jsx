import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'

import App from './App.jsx'
import Login from './Login.jsx'
import Dashboard from './Dashboard.jsx'
import About from './About.jsx'
import Analysis from './Analysis.jsx'
import Quiz from './Quiz.jsx'
import Plan from './Plan.jsx'
import Recommended from './Recommended.jsx'

import './index.css'

function Router() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const handleNavigation = () => {
      setPath(window.location.pathname)
    }

    window.addEventListener('popstate', handleNavigation)

    return () => {
      window.removeEventListener('popstate', handleNavigation)
    }
  }, [])

  if (path === '/about') return <About />
  if (path === '/login') return <Login />
  if (path === '/dashboard') return <Dashboard />
  if (path === '/analysis') return <Analysis />
  if (path === '/quiz') return <Quiz />
  if (path === '/plan') return <Plan />
  if (path === '/recommended') return <Recommended />

  return <App />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>,
)
