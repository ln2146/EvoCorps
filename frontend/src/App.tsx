import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import DashboardLayout from './components/DashboardLayout'
import WelcomePage from './pages/WelcomePage'
import HomePage from './pages/HomePage'
import ServiceManagement from './pages/ServiceManagement'
import DataMonitoring from './pages/DataMonitoring'
import ExperimentManagement from './pages/ExperimentManagement'
import DataVisualization from './pages/DataVisualization'
import ConfigPage from './pages/ConfigPage'
import DynamicDemo from './pages/DynamicDemo'

function App() {
  return (
    <Router>
      <Routes>
        {/* 欢迎页 */}
        <Route path="/" element={<WelcomePage />} />
        
        {/* 动态演示 */}
        <Route path="/dynamic" element={<DynamicDemo />} />
        
        {/* 静态演示 - Dashboard */}
        <Route path="/dashboard/*" element={
          <DashboardLayout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/service" element={<ServiceManagement />} />
              <Route path="/monitoring" element={<DataMonitoring />} />
              <Route path="/experiment" element={<ExperimentManagement />} />
              <Route path="/visualization" element={<DataVisualization />} />
              <Route path="/config" element={<ConfigPage />} />
            </Routes>
          </DashboardLayout>
        } />
      </Routes>
    </Router>
  )
}

export default App
