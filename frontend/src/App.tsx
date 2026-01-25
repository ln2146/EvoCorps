import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ServiceManagement from './pages/ServiceManagement'
import DataMonitoring from './pages/DataMonitoring'
import ExperimentManagement from './pages/ExperimentManagement'
import DataVisualization from './pages/DataVisualization'
import ConfigPage from './pages/ConfigPage'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/service" element={<ServiceManagement />} />
          <Route path="/monitoring" element={<DataMonitoring />} />
          <Route path="/experiment" element={<ExperimentManagement />} />
          <Route path="/visualization" element={<DataVisualization />} />
          <Route path="/config" element={<ConfigPage />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
