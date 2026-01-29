import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient()

const rootEl = document.getElementById('root')
if (!rootEl) {
  console.error('CT Property Search: missing #root element. Check index.html.')
  document.body.innerHTML = '<div style="padding:2rem;font-family:sans-serif;">CT Property Search: missing root element. Check that index.html contains &lt;div id="root"&gt;&lt;/div&gt;</div>'
} else {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>,
  )
}
