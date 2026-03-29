import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import DeviceList from './pages/DeviceList'
import DeviceDetail from './pages/DeviceDetail'
import CLIModeling from './pages/CLIModeling'
import ImportWizard from './pages/ImportWizard'
import ScenarioList from './pages/ScenarioList'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/devices" element={<DeviceList />} />
          <Route path="/devices/:id" element={<DeviceDetail />} />
          <Route path="/devices/:id/cli" element={<CLIModeling />} />
          <Route path="/cli-modeling" element={<CLIModeling />} />
          <Route path="/import" element={<ImportWizard />} />
          <Route path="/scenarios" element={<ScenarioList />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
