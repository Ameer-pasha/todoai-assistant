import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './components/Sidebar.css'
import './components/TaskCard.css'
import './components/TaskList.css'
import './components/AddTaskForm.css'
import './components/ChatPanel.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
