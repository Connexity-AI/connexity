import { ElementType, FC, ReactNode } from 'react';

import CardSmallSkeleton from '@workspace/ui/components/skeletons/card-small';
import { Card, CardContent, CardHeader, CardTitle } from '@workspace/ui/components/ui/card';

export interface Props {
  title: string;
  icon: ElementType;
  content: ReactNode;
  status: string;
  /** Must be optional for Suspense. */
  isLoading?: boolean;
}

const CardSmall: FC<Props> = ({ title, icon: Icon, content, status, isLoading }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
        {title}
      </CardTitle>
      <Icon className="h-4 w-4 text-gray-400" />
    </CardHeader>
    <CardContent>
      {isLoading ? <CardSmallSkeleton /> : content}
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{status}</p>
    </CardContent>
  </Card>
);

export default CardSmall;
