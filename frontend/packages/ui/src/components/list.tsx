import { ElementType, FC, ReactNode } from 'react';

import ListItemSkeleton from '@workspace/ui/components/skeletons/list';
import { Card, CardContent, CardHeader, CardTitle } from '@workspace/ui/components/ui/card';

export interface Props {
  title: string;
  icon: ElementType;
  items: ListItemProps[];
  isLoading?: boolean;
}

const List: FC<Props> = ({ title, icon: Icon, items, isLoading }) => (
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center space-x-2">
        <Icon className="h-5 w-5" />
        <span>{title}</span>
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-4">
        {isLoading && [...Array(3)].map((_, index) => <ListItemSkeleton key={index} />)}

        {!isLoading && items.length > 0 ? (
          items.slice(0, 5).map((item, index) => <ListItem key={index} {...item} />)
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No items found
          </p>
        )}
      </div>
    </CardContent>
  </Card>
);

export interface ListItemProps {
  icon: ReactNode;
  content: ReactNode;
  status: ReactNode;
  isLoading?: boolean;
}

export const ListItem: FC<ListItemProps> = ({ icon, content, status, isLoading }) =>
  isLoading ? (
    <ListItemSkeleton />
  ) : (
    <div className="flex items-center space-x-4">
      {icon}
      <div className="flex-1 min-w-0">{content}</div>
      {/* Todo: fix this, add wrapper div */}
      {status}
    </div>
  );

export default List;
