import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import DeviceList from './pages/DeviceList'
import DeviceDetail from './pages/DeviceDetail'
import CLIModeling from './pages/CLIModeling'
import ImportWizard from './pages/ImportWizard'
import QueryExplorer from './pages/QueryExplorer'
import ScenarioList from './pages/ScenarioList'
import Settings from './pages/Settings'
import CustomFilters from './pages/CustomFilters'
import ConfigSources from './pages/ConfigSources'

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
          <Route path="/query-explorer" element={<QueryExplorer />} />
          <Route path="/scenarios" element={<ScenarioList />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/custom-filters" element={<CustomFilters />} />
          <Route path="/config-sources" element={<ConfigSources />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
