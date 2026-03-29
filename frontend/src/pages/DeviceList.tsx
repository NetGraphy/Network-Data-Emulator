import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchDevices } from '../api/client'

export default function DeviceList() {
  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: fetchDevices,
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Devices</h2>
        <Link to="/import" className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm transition-colors">
          Import Devices
        </Link>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left p-3 font-medium">Hostname</th>
                <th className="text-left p-3 font-medium">Platform</th>
                <th className="text-left p-3 font-medium">Model</th>
                <th className="text-left p-3 font-medium">Management IP</th>
                <th className="text-left p-3 font-medium">State</th>
                <th className="text-left p-3 font-medium">Tags</th>
              </tr>
            </thead>
            <tbody>
              {devices?.map(device => (
                <tr key={device.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="p-3">
                    <Link to={`/devices/${device.id}`} className="text-cyan-400 hover:text-cyan-300 font-medium">
                      {device.hostname}
                    </Link>
                  </td>
                  <td className="p-3 text-gray-400">{device.platform_name || '-'}</td>
                  <td className="p-3 text-gray-400">{device.model_name || '-'}</td>
                  <td className="p-3 font-mono text-gray-300">{device.management_ip || '-'}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                      device.admin_state === 'active'
                        ? 'bg-green-500/10 text-green-400'
                        : device.admin_state === 'maintenance'
                        ? 'bg-yellow-500/10 text-yellow-400'
                        : 'bg-gray-500/10 text-gray-400'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        device.admin_state === 'active' ? 'bg-green-400' :
                        device.admin_state === 'maintenance' ? 'bg-yellow-400' : 'bg-gray-400'
                      }`} />
                      {device.admin_state}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500 text-xs">
                    {device.tags ? Object.entries(device.tags).map(([k, v]) => (
                      <span key={k} className="inline-block bg-gray-800 rounded px-1.5 py-0.5 mr-1">
                        {k}: {v}
                      </span>
                    )) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
