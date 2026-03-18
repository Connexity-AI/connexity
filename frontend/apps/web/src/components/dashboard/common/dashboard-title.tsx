import type { FC, ReactNode } from 'react';

export interface Props {
  title: string;
  description: string;
  contentRight?: ReactNode;
  alert?: ReactNode;
}

const DashboardTitle: FC<Props> = ({ title, description, contentRight = <div />, alert }) => (
  <div className="space-y-6">
    <div className="flex justify-between items-center">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{title}</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">{description}</p>
      </div>
      {contentRight}
    </div>
    {alert}
  </div>
);

export default DashboardTitle;
