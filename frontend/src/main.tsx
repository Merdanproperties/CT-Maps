import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient()

// #region agent log
const rootEl = document.getElementById('root')
if (rootEl) {
  fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'main.tsx:root',message:'root element found',data:{hasRoot:!!rootEl},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
} else {
  fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'main.tsx:root',message:'root element MISSING',data:{hasRoot:false},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
}
// #endregion

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

// #region agent log
fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'main.tsx:render',message:'React render invoked',data:{},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
// #endregion
