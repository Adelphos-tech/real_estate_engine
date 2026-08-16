import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Questionnaire from './pages/Questionnaire'
import Marketplace from './pages/Marketplace'
import PropertyDetail from './pages/PropertyDetail'
import Compare from './pages/Compare'
import Profile from './pages/Profile'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/questionnaire" element={<Questionnaire />} />
            <Route path="/marketplace" element={<Marketplace />} />
            <Route path="/property/:propertyId" element={<PropertyDetail />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  </React.StrictMode>,
)
