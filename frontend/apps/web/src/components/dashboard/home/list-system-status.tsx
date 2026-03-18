import { Settings } from 'lucide-react';

import List from '@workspace/ui/components/list';

import { UtilsService } from '@/client/sdk.gen';
import { throwIfApiError } from '@/utils/error';

import type { FC } from 'react';

const ListSystemStatus: FC = async () => {
  const systemResult = await UtilsService.healthCheck();

  throwIfApiError(systemResult);

  const systemHealth = systemResult.data ?? false;

  return (
    <List
      title="System Status"
      icon={Settings}
      items={[
        {
          icon: (
            <>
              {systemHealth ? (
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              ) : (
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              )}
            </>
          ),
          content: (
            <span className="text-sm font-medium text-gray-900 dark:text-white">API Server</span>
          ),
          status: (
            <div className="text-right">
              <div className={`text-sm ${systemHealth ? 'text-green-600' : 'text-red-600'}`}>
                {systemHealth ? 'Online' : 'Offline'}
              </div>
              <div className="text-xs text-gray-400">
                {systemHealth ? 'Responding' : 'Not responding'}
              </div>
            </div>
          ),
        },
        {
          icon: <div className="w-3 h-3 bg-green-500 rounded-full"></div>,
          content: (
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              Authentication
            </span>
          ),
          status: (
            <div className="text-right">
              <div className="text-sm text-green-600">Active</div>
              <div className="text-xs text-gray-400">Token valid</div>
            </div>
          ),
        },
      ]}
    />
  );
};

export default ListSystemStatus;
